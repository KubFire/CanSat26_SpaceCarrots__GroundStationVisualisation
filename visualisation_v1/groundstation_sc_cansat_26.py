#Developement branch - visualising simulated data from test_lora_log.txt
#V1.1.9
#Stable - funguje mapa, funguje vizualizace, na KubFire LowPC to beha krasnych 63ms
#Smaller screen support
# test - vidis tenhle comment? Lucka

"""
WHATS IMPLEMENTED?
    Optimalizace - Fast-Forward (Zero Latency Priority)
    Drift - rozdil casu Arduino vs PC (Topmost priority)
    Upkeep - surový čas Arduina (millis) + Graf (Topmost graph)
    Ground Cycle Δ - ground time since last packet
    CanSat Cycle Δ - interval mezi pakety z pohledu Arduina
    MSPF - UI Frame latency (millisecperframe)
    Sync Drift - tlacitko pro manualni synchronizaci casu
    Map 1:1 adaptive aspect ratio - Fixed 50/50 screen split
    Two-row layout pro checkboxy na mensich displejich
    AUTO COM PORT - Automatic detection and hot-plugging - UnTEsted
    Ukladani na csv soubor.
"""
import queue
import sys
import threading
import time
import os
import serial
import serial.tools.list_ports
import numpy as np
from PyQt6 import QtWidgets, QtCore, QtGui
import pyqtgraph as pg
from haversine import haversine
import contextily as cx

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

# --- CONFIG ---
SERIAL_PORT = "AUTO" # Set to "AUTO" for auto-detection, or specify a port like "COM8"
BAUD_RATE = 115200
ground_lat, ground_lon = 49.7950, 16.6800 
target_lat, target_lon = 49.7985833, 16.6877778
map_scale = 0.02 

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(CURRENT_DIR)
MAP_DIR = os.path.join(BASE_DIR, "map_tiles")
TILES_PATH = os.path.join(MAP_DIR, "{z}", "{x}", "{y}.png")

q = queue.Queue(maxsize=50) 

def data_reader_worker(data_queue, target_port, baud):
    sensor_map = {'M': 'MILLIS', 'A': 'ALT', 'B': 'TEMP', 'C': 'HUM', 'D': 'PRESS', 'E': 'LAT', 'F': 'LON', 'V': 'V_SPEED', 'R': 'RSSI', 'S': 'SNR'}
    last_status = ""
    log_filename = f"cansat_log_{int(time.time())}.csv"
    csv_keys = ['time', 'MILLIS', 'ALT', 'TEMP', 'HUM', 'PRESS', 'LAT', 'LON', 'V_SPEED', 'RSSI', 'SNR']
    log_file = None
    
    while True:
        port_to_open = target_port
        
        # --- AUTO DETECT LOGIC ---
        if target_port == "AUTO":
            port_to_open = None
            ports = serial.tools.list_ports.comports()
            # Look for common Arduino / LoRa receiver serial chips
            for p in ports:
                desc = p.description.lower()
                if any(k in desc for k in ['arduino', 'ch340', 'cp210', 'cp210x', 'ftdi', 'usb serial', 'usb-serial']):
                    port_to_open = p.device
                    break
            # Fallback: Just grab the first USB device if specific chips aren't named
            if not port_to_open:
                for p in ports:
                    if 'usb' in p.description.lower() or 'usb' in p.hwid.lower():
                        port_to_open = p.device
                        break
        
        if not port_to_open:
            if last_status != "WAITING":
                if not data_queue.full(): data_queue.put({'type': 'msg', 'text': "AUTO: Waiting for USB receiver..."})
                last_status = "WAITING"
            time.sleep(2)
            continue
            
        try:
            ser = serial.Serial(port_to_open, baud, timeout=0.1)
            if not data_queue.full():
                data_queue.put({'type': 'msg', 'text': f"Connected to {port_to_open}"})
            last_status = "CONNECTED"
            
            log_file = open(log_filename, "a", encoding="utf-8")
            if os.path.getsize(log_filename) == 0:
                log_file.write(",".join(csv_keys) + "\n")
            
            while True:
                raw_line = ser.readline()
                if not raw_line: continue
                try:
                    line = raw_line.decode('utf-8').strip()
                    if not line: continue
                    data = {'time': time.time()} 
                    parts = line.split(';') 
                    for item in parts:
                        item = item.strip()
                        if len(item) < 2: continue
                        v = item[0].upper()
                        if v == 'X':
                            data_queue.put({'type': 'msg', 'text': f"MSG: {item[1:]}"})
                            continue
                        try: data[sensor_map.get(v, v)] = float(item[1:])
                        except: continue
                    
                    data_queue.put(data)
                    
                    # Write to CSV
                    row = [str(data.get(k, "")) for k in csv_keys]
                    log_file.write(",".join(row) + "\n")
                    log_file.flush()
                    
                except Exception as parse_err: 
                    continue # Ignore decode errors
                    
        except serial.SerialException:
            # This triggers if the device is physically unplugged while running
            if log_file: log_file.close()
            if last_status != "DISCONNECTED":
                if not data_queue.full(): data_queue.put({'type': 'msg', 'text': f"Connection to {port_to_open} lost. Reconnecting..."})
                last_status = "DISCONNECTED"
            time.sleep(1)
        except Exception as e:
            if log_file: log_file.close()
            time.sleep(1)

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
        self.resize_timer.timeout.connect(self.render_full_map)
        
    def setup_plot(self):
        self.fig.patch.set_facecolor('#121212')
        self.axes.set_facecolor('#121212')
        self.axes.set_axis_off() 
        aspect = 1 / np.cos(np.radians(self.ground_pos[1]))
        self.axes.set_aspect(aspect, adjustable='datalim')
        
        self.ground_dot, = self.axes.plot([self.ground_pos[0]], [self.ground_pos[1]], 'o', color='#000000', markersize=10, zorder=10, animated=True)
        self.cansat_dot, = self.axes.plot([], [], 'o', color='#EA5A0C', markersize=10, zorder=11, animated=True)
        self.path_line, = self.axes.plot([], [], '-', color='#EA5A0C', alpha=0.6, linewidth=2, zorder=5, animated=True)
        
        self.mpl_connect('draw_event', self.on_draw)
        self.render_full_map()
        self.fig.subplots_adjust(left=0, right=1, top=1, bottom=0)

    def on_draw(self, event):
        self.bg_cache = self.copy_from_bbox(self.axes.bbox)
        self.axes.draw_artist(self.path_line)
        self.axes.draw_artist(self.ground_dot)
        self.axes.draw_artist(self.cansat_dot)

    def render_full_map(self):
        w, h = self.width(), self.height()
        aspect = 1 / np.cos(np.radians(self.ground_pos[1]))
        if w > h:
            new_scale_lon = self.current_scale * (w / h)
            new_scale_lat = self.current_scale / aspect
        else:
            new_scale_lon = self.current_scale
            new_scale_lat = (self.current_scale / aspect) * (h / w)

        self.axes.set_xlim(self.ground_pos[0] - new_scale_lon, self.ground_pos[0] + new_scale_lon)
        self.axes.set_ylim(self.ground_pos[1] - new_scale_lat, self.ground_pos[1] + new_scale_lat)
        
        self.path_line.set_visible(False)
        self.cansat_dot.set_visible(False)

        try:
            self.axes.images = []
            cx.add_basemap(self.axes, crs='EPSG:4326', source=TILES_PATH)
        except:
            try: cx.add_basemap(self.axes, crs='EPSG:4326', source=cx.providers.OpenStreetMap.Mapnik)
            except: pass
            
        self.draw()
        QtWidgets.QApplication.processEvents()
        self.path_line.set_visible(True)
        self.cansat_dot.set_visible(True)
        self.bg_cache = self.copy_from_bbox(self.axes.bbox)

    def update_position(self, lat, lon):
        if lat == 0 or lon == 0: return 
        self.path_lons.append(lon); self.path_lats.append(lat)
        self.path_line.set_data(self.path_lons[-300:], self.path_lats[-300:])
        self.cansat_dot.set_data([lon], [lat])
        
        if self.bg_cache is not None:
            self.restore_region(self.bg_cache)
            self.axes.draw_artist(self.path_line)
            self.axes.draw_artist(self.ground_dot)
            self.axes.draw_artist(self.cansat_dot)
            self.blit(self.axes.bbox)
        else:
            self.draw_idle()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.resize_timer.start(400)

class GroundStation(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("CanSat Ground Station V1.1.9")
        self.setStyleSheet("""
            QCheckBox::indicator { width: 14px; height: 14px; background-color: transparent; border: 1px solid #777; border-radius: 3px; } 
            QCheckBox::indicator:checked { background-color: #EA5A0C; border: 1px solid #EA5A0C; image: url("data:image/svg+xml;utf8,<svg width='14' height='14' viewBox='0 0 24 24' fill='none' stroke='white' stroke-width='4' stroke-linecap='round' stroke-linejoin='round' xmlns='http://www.w3.org/2000/svg'><polyline points='20 6 9 17 4 12'/></svg>"); }
        """)
        
        self.data = {k: [] for k in ['RSSI', 'SNR', 'TEMP', 'ALT', 'LAT', 'LON', 'GTSLP', 'U_LAT', 'HUM', 'PRESS', 'DIST', 'MILLIS', 'V_SPEED', 'DRIFT', 'CAN_DELTA', 'UPKEEP']}
        self.sync_offset = 0 
        self.last_millis = 0
        self.start_time_pc = time.time()

        self.main_widget = QtWidgets.QWidget()
        self.setCentralWidget(self.main_widget)
        self.layout = QtWidgets.QVBoxLayout(self.main_widget)
        
        title_lbl = QtWidgets.QLabel("SPACE CARROTS CANSAT TX")
        title_lbl.setFont(QtGui.QFont("Arial", 24, QtGui.QFont.Weight.Bold))
        title_lbl.setStyleSheet("color: #EA5A0C;")
        self.layout.addWidget(title_lbl, alignment=QtCore.Qt.AlignmentFlag.AlignCenter)

        self.row1, self.row2 = QtWidgets.QHBoxLayout(), QtWidgets.QHBoxLayout()
        font = QtGui.QFont("Arial", 16)
        
        self.lbl_keys = ['Drift', 'World T', 'Upkeep', 'CanSat Cycle Δ', 'Ground Cycle Δ', 'MSPF', 'RSSI', 'SNR', 'Alt', 'V_Speed', 'Lng', 'Lat', 'Dist', 'Temp', 'Hum', 'Pressure']
        self.lbls = {k: QtWidgets.QLabel() for k in self.lbl_keys}
        
        colors = {'Drift': '#FF4500', 'Upkeep': '#FFFFFF', 'Ground Cycle Δ': '#FFD700', 'MSPF': '#FF00FF', 'RSSI': '#00FFFF', 'SNR': '#FFFFFF', 'Dist': '#9370DB', 'V_Speed': '#00FA9A', 'Alt': '#1E90FF', 'Temp': '#FF6A6A', 'Hum': '#FFA500', 'Pressure': '#98FB98', 'CanSat Cycle Δ': '#FF6347'}
        data_labels = ['Drift', 'Upkeep', 'CanSat Cycle Δ', 'Ground Cycle Δ', 'RSSI', 'SNR', 'Alt', 'V_Speed', 'Lng', 'Lat', 'Dist', 'Temp', 'Hum', 'Pressure']
        
        for k in self.lbl_keys:
            lbl = self.lbls[k]
            lbl.setFont(font)
            if k in colors: lbl.setStyleSheet(f"color: {colors[k]};")
            
            # Apply initial N/A state using inline HTML so the label color is kept for the variable name
            if k in data_labels:
                lbl.setText(f"{k}: <b><font color='#FF0000'>N/A</font></b>")
            else:
                lbl.setText(f"{k}: --")
                
            (self.row1 if k in ['Drift', 'World T', 'Upkeep', 'CanSat Cycle Δ', 'Ground Cycle Δ', 'MSPF', 'RSSI', 'SNR'] else self.row2).addWidget(lbl)
        
        self.layout.addLayout(self.row1); self.layout.addLayout(self.row2)

        self.content = QtWidgets.QHBoxLayout()
        self.left_panel = QtWidgets.QVBoxLayout()
        
        self.toggle_container = QtWidgets.QHBoxLayout()
        self.toggle_rows_layout = QtWidgets.QVBoxLayout()
        self.t_row1 = QtWidgets.QHBoxLayout()
        self.t_row2 = QtWidgets.QHBoxLayout()
        
        self.graph_stack = QtWidgets.QVBoxLayout()
        
        self.plots = {}
        graph_configs = [
            ('Upkeep', 'UPKEEP', colors['Upkeep']),
            ('Drift', 'DRIFT', colors['Drift']), 
            ('CanSat Cycle Δ', 'CAN_DELTA', colors['CanSat Cycle Δ']), 
            ('Ground Cycle Δ', 'GTSLP', colors['Ground Cycle Δ']), 
            ('Distance', 'DIST', colors['Dist']),
            ('MSPF', 'U_LAT', colors['MSPF']), 
            ('RSSI', 'RSSI', colors['RSSI']), 
            ('SNR', 'SNR', colors['SNR']), 
            ('V_Speed', 'V_SPEED', colors['V_Speed']), 
            ('Alt', 'ALT', colors['Alt']), 
            ('Temp', 'TEMP', colors['Temp']), 
            ('Humidity', 'HUM', colors['Hum']), 
            ('Pressure', 'PRESS', colors['Pressure'])
        ]
        
        start_visible_keys = {'U_LAT', 'DIST', 'V_SPEED', 'ALT', 'DRIFT', 'CAN_DELTA', 'UPKEEP'}
        
        checkboxes = []
        for i, (name, key, col) in enumerate(graph_configs):
            pw = pg.PlotWidget(title=name)
            pw.setMinimumHeight(60)
            pw.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Expanding)
            self.plots[key] = pw.plot(pen=col)
            pw.setVisible(key in start_visible_keys)
            self.graph_stack.addWidget(pw, stretch=1)
            chk = QtWidgets.QCheckBox(name)
            chk.setChecked(key in start_visible_keys)
            chk.toggled.connect(lambda checked, w=pw: w.setVisible(checked))
            checkboxes.append(chk)

        self.msg_log = QtWidgets.QTextEdit()
        self.msg_log.setReadOnly(True)
        self.msg_log.setMaximumHeight(160) 
        self.msg_log.setStyleSheet("background:#121212; color:#EA5A0C; font-family:monospace;")
        self.msg_log.setVisible(True)
        self.graph_stack.addWidget(self.msg_log)
        
        chk_err = QtWidgets.QCheckBox("Error+Msg")
        chk_err.setChecked(True)
        chk_err.toggled.connect(self.msg_log.setVisible)
        checkboxes.append(chk_err)
        
        mid_point = (len(checkboxes) + 1) // 2
        for i, chk in enumerate(checkboxes):
            if i < mid_point:
                self.t_row1.addWidget(chk)
            else:
                self.t_row2.addWidget(chk)
                
        self.t_row1.addStretch()
        self.t_row2.addStretch()
        
        self.toggle_rows_layout.addLayout(self.t_row1)
        self.toggle_rows_layout.addLayout(self.t_row2)
        
        self.toggle_container.addLayout(self.toggle_rows_layout)
        
        self.btn_sync = QtWidgets.QPushButton("Sync Drift")
        self.btn_sync.setFixedSize(80, 50) 
        self.btn_sync.setStyleSheet("background:#FF2222; color:#FFF; font-weight:bold; border-radius:4px;")
        self.btn_sync.clicked.connect(self.do_sync)
        self.toggle_container.addWidget(self.btn_sync)

        self.left_panel.addLayout(self.toggle_container)
        self.left_panel.addLayout(self.graph_stack, stretch=1)
        
        self.left_widget = QtWidgets.QWidget()
        self.left_widget.setLayout(self.left_panel)
        self.left_widget.setMinimumWidth(100) 
        
        self.map_w = MapWidget()
        self.map_w.setMinimumWidth(100)
        self.map_w.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Expanding)
        
        self.content.addWidget(self.left_widget, stretch=1)
        self.content.addWidget(self.map_w, stretch=1)
        
        self.layout.addLayout(self.content)

        self.last_ui_t = time.time()
        self.timer = QtCore.QTimer(); self.timer.timeout.connect(self.update_ui); self.timer.start(33)

    def do_sync(self):
        if self.data['MILLIS']:
            self.sync_offset = (time.time() - self.start_time_pc) * 1000 - self.data['MILLIS'][-1]
            self.msg_log.append("Drift Synced.")

    def update_ui(self):
        now = time.time()
        ui_ms = (now - self.last_ui_t) * 1000
        self.last_ui_t = now
        self.lbls['World T'].setText(time.strftime("Time: %H:%M:%S"))
        real_ms = int((now - self.start_time_pc) * 1000)
        self.lbls['MSPF'].setText(f"MSPF: {ui_ms:.0f} ms")
        if 0 <= ui_ms < 500: self.data['U_LAT'].append(ui_ms)

        last_packet = None
        while not q.empty():
            d = q.get()
            if d.get('type') == 'msg':
                self.msg_log.append(f"[{time.strftime('%H:%M:%S')}] {d['text']}"); continue
            
            curr_m = d.get('MILLIS', 0)
            
            for k in ['TEMP', 'ALT', 'LAT', 'LON', 'RSSI', 'SNR', 'PRESS', 'MILLIS', 'V_SPEED']:
                self.data[k].append(d.get(k, 0.0))
            self.data['HUM'].append(d.get('HUM', 0.0))
            self.data['UPKEEP'].append(curr_m)
            
            can_delta = int(curr_m - self.last_millis) if self.last_millis != 0 else 0
            self.data['CAN_DELTA'].append(can_delta)
            
            gtslp = (now - d['time']) * 1000
            if 0 <= gtslp < 1000: self.data['GTSLP'].append(gtslp)
            
            drift = int((real_ms - self.sync_offset) - curr_m)
            self.data['DRIFT'].append(drift)
            
            dist = round(haversine((d.get('LAT', 0), d.get('LON', 0)), (target_lat, target_lon))*1000, 1) if d.get('LAT') else 0.0
            self.data['DIST'].append(dist)
            
            self.last_millis = curr_m
            last_packet = d 

        if last_packet:
            curr_m = last_packet.get('MILLIS', 0)
            self.lbls['Upkeep'].setText(f"Upkeep: {int(curr_m)//1000} {int(curr_m)%1000:03d}")
            self.lbls['CanSat Cycle Δ'].setText(f"CanSat Cycle Δ: {self.data['CAN_DELTA'][-1] if self.data['CAN_DELTA'] else 0} ms")
            self.lbls['Ground Cycle Δ'].setText(f"Ground Cycle Δ: {self.data['GTSLP'][-1]:.0f} ms")
            
            drift = self.data['DRIFT'][-1] if self.data['DRIFT'] else 0
            drift_txt = "<55ms" if abs(drift) < 55 else f"{drift} ms"
            self.lbls['Drift'].setText(f"Drift: {drift_txt}")
            
            if last_packet.get('LAT'):
                self.map_w.update_position(last_packet['LAT'], last_packet['LON'])

        if not self.data['ALT']: return
        for k in self.data: self.data[k] = self.data[k][-300:]
        for k in ['TEMP', 'ALT', 'RSSI', 'SNR', 'HUM', 'PRESS', 'DIST', 'V_SPEED', 'GTSLP', 'U_LAT', 'DRIFT', 'CAN_DELTA', 'UPKEEP']:
            if self.data[k]: self.plots[k].setData(self.data[k])
        
        vals = {'Dist': f"{self.data['DIST'][-1]} m", 'V_Speed': f"{self.data['V_SPEED'][-1]} m/s", 'Alt': f"{self.data['ALT'][-1]} m", 'Lng': f"{self.data['LON'][-1]:.5f}", 'Lat': f"{self.data['LAT'][-1]:.5f}", 'Temp': f"{self.data['TEMP'][-1]} °C", 'Hum': f"{self.data['HUM'][-1]} %", 'Pressure': f"{self.data['PRESS'][-1]} hPa", 'RSSI': f"{self.data['RSSI'][-1]} dBm", 'SNR': f"{self.data['SNR'][-1]} dB"}
        for k, v in vals.items(): self.lbls[k].setText(f"{k}: {v}")

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    threading.Thread(target=data_reader_worker, args=(q, SERIAL_PORT, BAUD_RATE), daemon=True).start()
    w = GroundStation(); w.show(); sys.exit(app.exec())