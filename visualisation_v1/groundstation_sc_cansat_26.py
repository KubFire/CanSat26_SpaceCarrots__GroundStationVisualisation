#Developement branch - visualising simulated data from test_lora_log.txt
#V1.1.2
#Stable - funguje mapa, funguje vizualizace, na KubFire LowPC to beha krasnych 63ms
"""
WHATS IMPLEMENTED?
    Offline mapy - prvni checkne jestli je ma offline, pokud ne, stahuje je z netu
    Optimalizace - beha rychle
    TSLP - time since last packet
    Windows resizing funguje
    Horni Bar je usporadany a zobrazuje vsechny values.
    vsechny hodnoty maji sve grafiky, color coded.

----------------------------------

TO DO List
    Cteni Serialu misto example dat

"""
import queue
import sys
import threading
import time
import csv
import os
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
DATA_DIR = os.path.join(BASE_DIR, "data")
MAP_DIR = os.path.join(BASE_DIR, "map_tiles")
TILES_PATH = os.path.join(MAP_DIR, "{z}", "{x}", "{y}.png")

export_file = os.path.join(DATA_DIR, "telemetry_export.csv")
data_file = os.path.join(DATA_DIR, "test_lora_log.txt")

q = queue.Queue(maxsize=10) 
START_TIME = time.time()

# --- GPS & SCALE ---
ground_lat, ground_lon = 49.7950, 16.6800 
target_lat, target_lon = 49.7985833, 16.6877778
map_scale = 0.04 

def data_reader_worker(data_queue, file_path):
    sensor_map = {'A': 'TEMP', 'B': 'HUM', 'C': 'ALT', 'D': 'PRESS', 'E': 'LAT', 'F': 'LON', 'R': 'RSSI', 'S': 'SNR'}
    try:
        with open(file_path, 'r', encoding='utf-8') as log_file:
            for line in log_file:
                line = line.strip()
                if not line: continue
                data = {'time': time.time()} 
                parts = line.split('|') 
                for part in parts:
                    for item in part.split(';'):
                        item = item.strip()
                        if len(item) < 2: continue
                        v = item[0].upper()
                        try: data[sensor_map.get(v, v)] = float(item[1:])
                        except: continue
                for key in ["TEMP", "RSSI", "SNR", "PRESS", "LON", "LAT", "ALT"]:
                    if key not in data: data[key] = 0.0
                if data_queue.full():
                    try: data_queue.get_nowait()
                    except: pass
                data_queue.put(data)
                time.sleep(0.1)
    except FileNotFoundError: print("Data file not found.")

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
        
        self.ground_dot, = self.axes.plot([self.ground_pos[0]], [self.ground_pos[1]], 'o', color='#FF69B4', markersize=10, zorder=10, animated=True)
        self.cansat_dot, = self.axes.plot([], [], 'o', color='#FFA500', markersize=10, zorder=11, animated=True)
        self.path_line, = self.axes.plot([], [], color='#FFA500', alpha=0.6, linewidth=2, zorder=5, animated=True)
        
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
        self.setWindowTitle("CanSat Ground Station V1.1.2")
        
        self.setStyleSheet("""
            QCheckBox::indicator {
                width: 14px;
                height: 14px;
                background-color: transparent;
                border: 1px solid #777;
                border-radius: 3px;
            }
            QCheckBox::indicator:checked {
                background-color: #FFA500;
                border: 1px solid #FFA500;
            }
        """)

        self.data = {k: [] for k in ['RSSI', 'SNR', 'TEMP', 'ALT', 'LAT', 'LON', 'D_LAT', 'U_LAT', 'HUM', 'PRESS', 'DIST']}
        
        self.main_widget = QtWidgets.QWidget()
        self.setCentralWidget(self.main_widget)
        self.layout = QtWidgets.QVBoxLayout(self.main_widget)
        
        # --- TOP DATA BARS ---
        self.top_container = QtWidgets.QVBoxLayout()
        
        # Title Row
        self.title_layout = QtWidgets.QHBoxLayout()
        self.title_lbl = QtWidgets.QLabel("Space Carrots CanSat TX Visualisation")
        title_font = QtGui.QFont("Eras Bold ITC", 32)
        self.title_lbl.setFont(title_font)
        self.title_lbl.setStyleSheet("color: #FFA500;")
        self.title_layout.addWidget(self.title_lbl, alignment=QtCore.Qt.AlignmentFlag.AlignCenter)
        
        self.row1_layout = QtWidgets.QHBoxLayout()
        self.row2_layout = QtWidgets.QHBoxLayout()
        
        font = QtGui.QFont()
        font.setPointSize(16)
        
        self.lbls = {}
        row1_keys = ['Real T', 'Packet T', 'TSLP', 'UI Frame', 'RSSI', 'SNR']
        row2_keys = ['Alt', 'Lng', 'Lat', 'Dist', 'Temp', 'Hum', 'Pressure']
        
        # Nová paleta s plným spektrem a pastelovějšími tóny pro červenou a zelenou
        self.color_map = {
            'TSLP': '#FFD700',       # Gold / Jemnější žlutá
            'UI Frame': '#FF00FF',   # Magenta
            'RSSI': '#00FFFF',       # Cyan
            'SNR': '#FFFFFF',        # Bílá
            'Dist': '#9370DB',       # Medium Purple
            'Alt': '#1E90FF',        # Dodger Blue
            'Temp': '#FF6A6A',       # Indian Red 1 / Soft Red
            'Hum': '#FFA500',        # Oranžová
            'Pressure': '#98FB98'    # Pale Green / Pastelová zelená
        }
        
        for k in row1_keys:
            lbl = QtWidgets.QLabel(f"{k}: --")
            lbl.setFont(font)
            if k in self.color_map: lbl.setStyleSheet(f"color: {self.color_map[k]};")
            self.lbls[k] = lbl
            self.row1_layout.addWidget(lbl)
            
        for k in row2_keys:
            lbl = QtWidgets.QLabel(f"{k}: --")
            lbl.setFont(font)
            if k in self.color_map: lbl.setStyleSheet(f"color: {self.color_map[k]};")
            self.lbls[k] = lbl
            self.row2_layout.addWidget(lbl)
            
        self.lbls['Packet T'].setText("Packet T: <font color='red'>N/A</font>")
        
        self.top_container.addLayout(self.title_layout)
        self.top_container.addLayout(self.row1_layout)
        self.top_container.addLayout(self.row2_layout)
        self.layout.addLayout(self.top_container)
        
        # --- CONTENT LAYOUT ---
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
            ('Alt', 'ALT', self.color_map['Alt']),
            ('Temp', 'TEMP', self.color_map['Temp']),
            ('Humidity', 'HUM', self.color_map['Hum']),
            ('Pressure', 'PRESS', self.color_map['Pressure'])
        ]
        
        for name, key, color in graph_configs:
            pw = pg.PlotWidget(title=name)
            pw.setMinimumHeight(100) 
            self.plots[key] = pw.plot(pen=color)
            self.graph_widgets[key] = pw
            self.graph_stack.addWidget(pw)
            
            chk = QtWidgets.QCheckBox(name)
            chk.setChecked(True)
            chk.toggled.connect(lambda checked, w=pw: w.setVisible(checked))
            self.toggle_layout.addWidget(chk)
        
        self.toggle_layout.addStretch() 
        
        self.map_widget = MapWidget()
        self.content.addLayout(self.left_panel, stretch=1)
        self.content.addWidget(self.map_widget, stretch=1)
        self.layout.addLayout(self.content)
        
        self.last_ui_time = time.time()
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.update_ui)
        self.timer.start(50) 
        
    def update_ui(self):
        now = time.time()
        ui_ms = (now - self.last_ui_time) * 1000
        self.last_ui_time = now
        self.lbls['Real T'].setText(f"Real T: {int(now*1000)%100000:05d}")
        self.lbls['UI Frame'].setText(f"UI Frame: {ui_ms:.0f} ms")

        if 0 <= ui_ms < 500:
            self.data['U_LAT'].append(ui_ms)

        updated = False
        while not q.empty():
            d = q.get()
            for k in ['TEMP', 'ALT', 'LAT', 'LON', 'RSSI', 'SNR', 'PRESS']: 
                self.data[k].append(d[k])
            self.data['HUM'].append(d.get('HUM', 0.0))
            
            tslp_ms = (now - d['time']) * 1000
            if 0 <= tslp_ms < 1000:
                self.data['D_LAT'].append(tslp_ms)
                
            if d['LAT'] != 0 and d['LON'] != 0:
                dist = round(haversine((d['LAT'], d['LON']), (target_lat, target_lon))*1000, 1)
            else:
                dist = self.data['DIST'][-1] if self.data['DIST'] else 0.0
            self.data['DIST'].append(dist)

            if d['LAT'] != 0:
                self.map_widget.update_position(d['LAT'], d['LON'])
                updated = True

        if not self.data['ALT']: return
        for k in self.data: self.data[k] = self.data[k][-300:]
        
        for key in ['TEMP', 'ALT', 'RSSI', 'SNR', 'HUM', 'PRESS', 'DIST']:
            if self.data[key]:
                self.plots[key].setData(self.data[key])
        
        if self.data['D_LAT']:
            self.plots['TSLP'].setData(self.data['D_LAT'])
            self.lbls['TSLP'].setText(f"TSLP: {self.data['D_LAT'][-1]:.0f} ms")
        
        if self.data['U_LAT']:
            self.plots['UI'].setData(self.data['U_LAT'])
        
        self.lbls['Dist'].setText(f"Dist: {self.data['DIST'][-1]}m")
        self.lbls['Alt'].setText(f"Alt: {self.data['ALT'][-1]} m")
        self.lbls['Lng'].setText(f"Lng: {self.data['LON'][-1]:.5f}")
        self.lbls['Lat'].setText(f"Lat: {self.data['LAT'][-1]:.5f}")
        self.lbls['Temp'].setText(f"Temp: {self.data['TEMP'][-1]} °C")
        self.lbls['Hum'].setText(f"Hum: {self.data['HUM'][-1]} %")
        self.lbls['Pressure'].setText(f"Pressure: {self.data['PRESS'][-1]} hPa")
        self.lbls['RSSI'].setText(f"RSSI: {self.data['RSSI'][-1]}")
        self.lbls['SNR'].setText(f"SNR: {self.data['SNR'][-1]}")

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    threading.Thread(target=data_reader_worker, args=(q, data_file), daemon=True).start()
    w = GroundStation(); w.show()
    sys.exit(app.exec())