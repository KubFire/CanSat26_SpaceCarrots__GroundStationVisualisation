#Developement branch - visualising simulated data from test_lora_log.txt
#V1.1.32
#Stable - funguje mapa, funguje vizualizace, na KubFire LowPC to beha krasnych 63ms
"""
WHATS IMPLEMENTED?
    Offline mapy - prvni checkne jestli je ma offline, pokud ne, stahuje je z netu
    Optimalizace - beha rychle
    TSLP - time since last packet
    Windows resizing funguje
    Horni Bar je usporadany a zobrazuje vsechny values.
    vsechny hodnoty maji sve grafiky, color coded.
    Cteni Serialu misto example dat

----------------------------------

TO DO List
    Mapa aby byla 1:1
    Mapa vetsi zoom
    Zoom mapy aby kdyz cansat utece aby se prerendrovala a zmensila
    Drift prepsat na Packet T Drift
    Drift udelat aby kdyz je mensi nez 50ms tak aby ukazoval <50ms
"""
import queue
import sys
import threading
import time
import os
import serial
from PyQt6 import QtWidgets, QtCore, QtGui
import pyqtgraph as pg
import numpy as np
from haversine import haversine
import contextily as cx

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

# --- RELATIVNÍ CESTY ---
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(CURRENT_DIR)
MAP_DIR = os.path.join(BASE_DIR, "map_tiles")
TILES_PATH = os.path.join(MAP_DIR, "{z}", "{x}", "{y}.png")

# --- SERIAL CONFIG ---
SERIAL_PORT = "COM8"
BAUD_RATE = 115200

q = queue.Queue(maxsize=10) 
START_TIME = time.time()

# --- GPS & SCALE ---
ground_lat, ground_lon = 49.7950, 16.6800 
target_lat, target_lon = 49.7985833, 16.6877778
map_scale = 0.02# cim vetsi, tim mensi zoom

def data_reader_worker(data_queue, port, baud):
    sensor_map = {
        'M': 'MILLIS', 
        'A': 'ALT', 
        'B': 'TEMP', 
        'C': 'HUM', 
        'D': 'PRESS', 
        'E': 'LAT', 
        'F': 'LON', 
        'V': 'V_SPEED', 
        'R': 'RSSI', 
        'S': 'SNR'
    }
    
    try:
        ser = serial.Serial(port, baud, timeout=1)
        if not data_queue.full():
            data_queue.put({'type': 'msg', 'text': f"Connected to {port} at {baud} baud."})
            
        while True:
            try:
                raw_line = ser.readline()
                if not raw_line: continue
                
                try:
                    line = raw_line.decode('utf-8').strip()
                except Exception as e:
                    if not data_queue.full():
                        data_queue.put({'type': 'msg', 'text': f"Decode error: {e}"})
                    continue
                
                if not line: continue
                
                data = {'time': time.time()} 
                parts = line.split(';') 
                
                for item in parts:
                    item = item.strip()
                    if len(item) < 2: continue
                    v = item[0].upper()
                    
                    if v == 'X':
                        if not data_queue.full():
                            data_queue.put({'type': 'msg', 'text': f"MSG: {item[1:]}"})
                        continue
                        
                    try: 
                        data[sensor_map.get(v, v)] = float(item[1:])
                    except ValueError: 
                        continue
                        
                for key in ["TEMP", "RSSI", "SNR", "PRESS", "LON", "LAT", "ALT", "HUM", "MILLIS", "V_SPEED"]:
                    if key not in data: data[key] = 0.0
                    
                if data_queue.full():
                    try: data_queue.get_nowait()
                    except queue.Empty: pass
                data_queue.put(data)
                
            except Exception as e:
                if not data_queue.full():
                    data_queue.put({'type': 'msg', 'text': f"Read error: {e}"})
                time.sleep(0.1)
    except Exception as e:
        if not data_queue.full():
            data_queue.put({'type': 'msg', 'text': f"Connection failed: {e}"})

#---------------------------------------MAPA-----------------------
class MapWidget(FigureCanvas):
    def __init__(self, parent=None):
        self.fig = Figure(figsize=(5, 5), dpi=100)
        self.axes = self.fig.add_subplot(111)
        super().__init__(self.fig)
        self.path_lons, self.path_lats = [], []
        self.ground_pos = [ground_lon, ground_lat]
        self.current_scale = map_scale
        self.bg_cache = None
        self.setup_plot()
        
        self.resize_timer = QtCore.QTimer()
        self.resize_timer.setSingleShot(True)
        self.resize_timer.timeout.connect(self.on_resize_timeout)
        
    def setup_plot(self):
        self.fig.patch.set_facecolor('#121212')
        self.axes.set_facecolor('#121212')
        self.axes.set_axis_off() 
        self.axes.set_aspect('equal', adjustable='box')
        
        self.ground_dot, = self.axes.plot([self.ground_pos[0]], [self.ground_pos[1]], 'o', color='#000000', markersize=10, zorder=10, animated=True)
        self.cansat_dot, = self.axes.plot([], [], 'o', color='#EA5A0C', markersize=10, zorder=11, animated=True)
        self.path_line, = self.axes.plot([], [], color='#EA5A0C', alpha=0.6, linewidth=2, zorder=5, animated=True)
        
        self.mpl_connect('draw_event', self.on_draw)
        
        self.render_full_map()
        self.fig.subplots_adjust(left=0, right=1, top=1, bottom=0)

    def on_draw(self, event):
        self.bg_cache = self.copy_from_bbox(self.axes.bbox)
        self.axes.draw_artist(self.path_line)
        self.axes.draw_artist(self.ground_dot)
        self.axes.draw_artist(self.cansat_dot)

    def render_full_map(self):
        self.axes.set_xlim(self.ground_pos[0] - self.current_scale, self.ground_pos[0] + self.current_scale)
        self.axes.set_ylim(self.ground_pos[1] - self.current_scale, self.ground_pos[1] + self.current_scale)
        try:
            self.axes.images = [] 
            cx.add_basemap(self.axes, crs='EPSG:4326', source=TILES_PATH)
        except:
            try: cx.add_basemap(self.axes, crs='EPSG:4326', source=cx.providers.OpenStreetMap.Mapnik)
            except: pass
        self.draw()

    def check_watchdog(self, lat, lon):
        xmin, xmax = self.axes.get_xlim()
        ymin, ymax = self.axes.get_ylim()
        margin_x = (xmax - xmin) * 0.15
        margin_y = (ymax - ymin) * 0.15
        if (lon < xmin + margin_x or lon > xmax - margin_x or lat < ymin + margin_y or lat > ymax - margin_y):
            self.current_scale *= 1.5
            self.render_full_map()
            return True
        return False

    def update_position(self, lat, lon):
        if not self.check_watchdog(lat, lon):
            self.path_lons.append(lon)
            self.path_lats.append(lat)
            self.path_line.set_data(self.path_lons[-300:], self.path_lats[-300:])
            self.cansat_dot.set_data([lon], [lat])
            
            if self.bg_cache is not None:
                self.restore_region(self.bg_cache)
                self.axes.draw_artist(self.path_line)
                self.axes.draw_artist(self.ground_dot)
                self.axes.draw_artist(self.cansat_dot)
                self.blit(self.axes.bbox)
            
    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.resize_timer.start(400)

    def on_resize_timeout(self):
        self.render_full_map()

#------------------------------------UI-----------------------

class GroundStation(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("CanSat Ground Station V1.1.3")
        
        self.setStyleSheet("""
            QCheckBox::indicator {
                width: 14px;
                height: 14px;
                background-color: transparent;
                border: 1px solid #777;
                border-radius: 3px;
            }
            QCheckBox::indicator:checked {
                background-color: #EA5A0C;
                border: 1px solid #EA5A0C;
                image: url("data:image/svg+xml;utf8,<svg width='14' height='14' viewBox='0 0 24 24' fill='none' stroke='white' stroke-width='4' stroke-linecap='round' stroke-linejoin='round' xmlns='http://www.w3.org/2000/svg'><polyline points='20 6 9 17 4 12'/></svg>");
            }
        """)

        self.data = {k: [] for k in ['RSSI', 'SNR', 'TEMP', 'ALT', 'LAT', 'LON', 'D_LAT', 'U_LAT', 'HUM', 'PRESS', 'DIST', 'MILLIS', 'V_SPEED']}
        self.real_t_offset = time.time()
        self.last_millis = 0
        
        self.main_widget = QtWidgets.QWidget()
        self.setCentralWidget(self.main_widget)
        self.layout = QtWidgets.QVBoxLayout(self.main_widget)
        
        self.top_container = QtWidgets.QVBoxLayout()
        
        self.title_layout = QtWidgets.QHBoxLayout()
        self.title_lbl = QtWidgets.QLabel("SPACE CARROTS CANSAT TX")
        title_font = QtGui.QFont()
        title_font.setPointSize(24)
        title_font.setBold(True)
        self.title_lbl.setFont(title_font)
        self.title_lbl.setStyleSheet("color: #EA5A0C;")
        self.title_layout.addWidget(self.title_lbl, alignment=QtCore.Qt.AlignmentFlag.AlignCenter)
        
        self.row1_layout = QtWidgets.QHBoxLayout()
        self.row2_layout = QtWidgets.QHBoxLayout()
        
        font = QtGui.QFont()
        font.setPointSize(16)
        
        self.lbls = {}
        row1_keys = ['Packet T', 'TSLP', 'UI Frame', 'RSSI', 'SNR']
        row2_keys = ['Alt', 'V_Speed', 'Lng', 'Lat', 'Dist', 'Temp', 'Hum', 'Pressure']
        
        self.color_map = {
            'TSLP': '#FFD700',       
            'UI Frame': '#FF00FF',   
            'RSSI': '#00FFFF',       
            'SNR': '#FFFFFF',        
            'Dist': '#9370DB',
            'V_Speed': '#00FA9A',
            'Alt': '#1E90FF',        
            'Temp': '#FF6A6A',       
            'Hum': '#FFA500',        
            'Pressure': '#98FB98'    
        }

        self.lbls['World T'] = QtWidgets.QLabel("Time: 00:00:00")
        self.lbls['World T'].setFont(font)
        self.row1_layout.addWidget(self.lbls['World T'])

        self.lbls['Real T'] = QtWidgets.QLabel("Real T: 00000")
        self.lbls['Real T'].setFont(font)
        self.row1_layout.addWidget(self.lbls['Real T'])
        
        self.btn_sync = QtWidgets.QPushButton("Sync T")
        self.btn_sync.setStyleSheet("background-color: #333; color: #FFF; padding: 4px; border-radius: 4px;")
        self.btn_sync.clicked.connect(self.sync_real_t)
        self.row1_layout.addWidget(self.btn_sync)
        
        for k in row1_keys:
            lbl = QtWidgets.QLabel(f"{k}: <font color='red'>N/A</font>")
            lbl.setFont(font)
            if k in self.color_map: lbl.setStyleSheet(f"color: {self.color_map[k]};")
            self.lbls[k] = lbl
            self.row1_layout.addWidget(lbl)
            
        for k in row2_keys:
            lbl = QtWidgets.QLabel(f"{k}: <font color='red'>N/A</font>")
            lbl.setFont(font)
            if k in self.color_map: lbl.setStyleSheet(f"color: {self.color_map[k]};")
            self.lbls[k] = lbl
            self.row2_layout.addWidget(lbl)
            
        self.top_container.addLayout(self.title_layout)
        self.top_container.addLayout(self.row1_layout)
        self.top_container.addLayout(self.row2_layout)
        self.layout.addLayout(self.top_container)
        
        self.content = QtWidgets.QHBoxLayout()
        self.left_panel = QtWidgets.QVBoxLayout()
        
        self.toggle_layout = QtWidgets.QHBoxLayout()
        self.left_panel.addLayout(self.toggle_layout)
        
        self.graph_stack = QtWidgets.QVBoxLayout()
        self.left_panel.addLayout(self.graph_stack, stretch=1) 
        
        self.plots = {}
        self.graph_widgets = {}
        
        graph_configs = [
            ('TSLP', 'TSLP', self.color_map['TSLP']),
            ('UI Latency', 'UI', self.color_map['UI Frame']),
            ('RSSI', 'RSSI', self.color_map['RSSI']),
            ('SNR', 'SNR', self.color_map['SNR']),
            ('Distance', 'DIST', self.color_map['Dist']),
            ('V_Speed', 'V_SPEED', self.color_map['V_Speed']),
            ('Alt', 'ALT', self.color_map['Alt']),
            ('Temp', 'TEMP', self.color_map['Temp']),
            ('Humidity', 'HUM', self.color_map['Hum']),
            ('Pressure', 'PRESS', self.color_map['Pressure'])
        ]
        
        for i, (name, key, color) in enumerate(graph_configs):
            pw = pg.PlotWidget(title=name)
            pw.setMinimumHeight(80) 
            self.plots[key] = pw.plot(pen=color)
            self.graph_widgets[key] = pw
            
            pw.setVisible(i < 5)
            self.graph_stack.addWidget(pw)
            
            chk = QtWidgets.QCheckBox(name)
            chk.setChecked(i < 5)
            chk.toggled.connect(lambda checked, w=pw: w.setVisible(checked))
            self.toggle_layout.addWidget(chk)
            
        self.msg_log = QtWidgets.QTextEdit()
        self.msg_log.setReadOnly(True)
        self.msg_log.setMinimumHeight(80)
        self.msg_log.setStyleSheet("background-color: #121212; color: #EA5A0C; font-family: monospace;")
        self.msg_log.setVisible(False)
        self.graph_stack.addWidget(self.msg_log)
        
        chk_err = QtWidgets.QCheckBox("ERRORS & MESSAGES")
        chk_err.setChecked(False)
        chk_err.toggled.connect(self.msg_log.setVisible)
        self.toggle_layout.addWidget(chk_err)
        
        self.toggle_layout.addStretch() 
        
        self.map_widget = MapWidget()
        self.content.addLayout(self.left_panel, stretch=1)
        self.content.addWidget(self.map_widget, stretch=1)
        self.layout.addLayout(self.content)
        
        self.last_ui_time = time.time()
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.update_ui)
        self.timer.start(50) 
        
    def sync_real_t(self):
        self.real_t_offset = time.time()
        
    def update_ui(self):
        now = time.time()
        ui_ms = (now - self.last_ui_time) * 1000
        self.last_ui_time = now
        
        self.lbls['World T'].setText(time.strftime("Time: %H:%M:%S"))
        
        elapsed = int((now - self.real_t_offset) * 1000)
        self.lbls['Real T'].setText(f"Real T: {elapsed:05d}")
        self.lbls['UI Frame'].setText(f"UI Frame: {ui_ms:.0f} ms")

        if 0 <= ui_ms < 500:
            self.data['U_LAT'].append(ui_ms)

        updated = False
        while not q.empty():
            d = q.get()
            
            if d.get('type') == 'msg':
                self.msg_log.append(f"[{time.strftime('%H:%M:%S')}] {d['text']}")
                sb = self.msg_log.verticalScrollBar()
                sb.setValue(sb.maximum())
                continue
            
            for k in ['TEMP', 'ALT', 'LAT', 'LON', 'RSSI', 'SNR', 'PRESS', 'MILLIS', 'V_SPEED']: 
                self.data[k].append(d.get(k, 0.0))
            self.data['HUM'].append(d.get('HUM', 0.0))
            
            tslp_ms = (now - d['time']) * 1000
            if 0 <= tslp_ms < 1000:
                self.data['D_LAT'].append(tslp_ms)
            
            current_millis = d.get('MILLIS', 0)
            delta_millis = current_millis - self.last_millis
            self.last_millis = current_millis
            self.lbls['Packet T'].setText(f"Packet T: {int(current_millis)} (Δ {int(delta_millis)}ms)")
                
            if d.get('LAT', 0) != 0 and d.get('LON', 0) != 0:
                dist = round(haversine((d['LAT'], d['LON']), (target_lat, target_lon))*1000, 1)
            else:
                dist = self.data['DIST'][-1] if self.data['DIST'] else 0.0
            self.data['DIST'].append(dist)

            if d.get('LAT', 0) != 0:
                self.map_widget.update_position(d['LAT'], d['LON'])
                updated = True

        if not self.data['ALT']: return
        for k in self.data: self.data[k] = self.data[k][-300:]
        
        for key in ['TEMP', 'ALT', 'RSSI', 'SNR', 'HUM', 'PRESS', 'DIST', 'V_SPEED']:
            if self.data[key]:
                self.plots[key].setData(self.data[key])
        
        if self.data['D_LAT']:
            self.plots['TSLP'].setData(self.data['D_LAT'])
            self.lbls['TSLP'].setText(f"TSLP: {self.data['D_LAT'][-1]:.0f} ms")
        
        if self.data['U_LAT']:
            self.plots['UI'].setData(self.data['U_LAT'])
        
        self.lbls['Dist'].setText(f"Dist: {self.data['DIST'][-1]} m")
        self.lbls['V_Speed'].setText(f"V_Speed: {self.data['V_SPEED'][-1]} m/s")
        self.lbls['Alt'].setText(f"Alt: {self.data['ALT'][-1]} m")
        self.lbls['Lng'].setText(f"Lng: {self.data['LON'][-1]:.5f}")
        self.lbls['Lat'].setText(f"Lat: {self.data['LAT'][-1]:.5f}")
        self.lbls['Temp'].setText(f"Temp: {self.data['TEMP'][-1]} °C")
        self.lbls['Hum'].setText(f"Hum: {self.data['HUM'][-1]} %")
        self.lbls['Pressure'].setText(f"Pressure: {self.data['PRESS'][-1]} hPa")
        self.lbls['RSSI'].setText(f"RSSI: {self.data['RSSI'][-1]} dBm")
        self.lbls['SNR'].setText(f"SNR: {self.data['SNR'][-1]} dB")

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    threading.Thread(target=data_reader_worker, args=(q, SERIAL_PORT, BAUD_RATE), daemon=True).start()
    w = GroundStation(); w.show()
    sys.exit(app.exec())