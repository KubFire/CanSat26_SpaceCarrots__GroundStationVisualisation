#Developement branch - visualising simulated data from test_lora_log.txt
#V1.1.14 - Forced CSV to Downloads, Forced Esri Zoom 16
#Stable - funguje mapa, funguje vizualizace, na KubFire LowPC to beha krasnych 63ms

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
import math

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure



# --- CONFIG ---
SERIAL_PORT = "AUTO" 
BAUD_RATE = 115200
ground_lat, ground_lon = 49.7950, 16.6800 
map_scale = 0.02 

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(CURRENT_DIR)
MAP_DIR = os.path.join(BASE_DIR, "map_tiles")
TILES_PATH = os.path.join(MAP_DIR, "{z}", "{x}", "{y}.png")

q = queue.Queue(maxsize=50)

def calculate_bearing(lat1, lon1, lat2, lon2):
<<<<<<< HEAD
=======
    """Vypočítá azimut mezi dvěma body v stupních (0-360)."""
>>>>>>> 5d3bb12931ea5ce3f14dc7820ed5b24694ca5cfa
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    delta_lambda = math.radians(lon2 - lon1)
    y = math.sin(delta_lambda) * math.cos(phi2)
    x = math.cos(phi1) * math.sin(phi2) - \
        math.sin(phi1) * math.cos(phi2) * math.cos(delta_lambda)
    return (math.degrees(math.atan2(y, x)) + 360) % 360

def calculate_h_speed(lat1, lon1, lat2, lon2, millis1, millis2):
<<<<<<< HEAD
    d_time = (millis2 - millis1) / 1000.0
    if d_time <= 0: return 0.0
    dist = haversine((lat1, lon1), (lat2, lon2)) * 1000 
    return dist / d_time

def data_reader_worker(data_queue, target_port, baud):
    sensor_map = {'M': 'MILLIS', 'A': 'ALT', 'B': 'TEMP', 'C': 'PRESS', 'D': 'LAT', 'E': 'LON', 'F': 'VOLTAGE', 'V': 'V_SPEED', 'R': 'RSSI', 'S': 'SNR', 'T':'STATE','G': 'TARGET_DIST', 'H': 'TARGET_AZIM', 'I': 'W_SPD', 'J': 'W_AZIM', 'K': 'V_WIN', 'L': 'A_WIN'}
    last_status = ""
    
    # FORCE TO DOWNLOADS FOLDER
    downloads_path = os.path.join(os.path.expanduser("~"), "Downloads")
    log_filename = os.path.join(downloads_path, f"cansat_log_{int(time.time())}.csv")
    
    csv_keys = ['time', 'MILLIS', 'ALT', 'TEMP', 'PRESS', 'LAT', 'LON', 'V_SPEED', 'RSSI', 'SNR', 'VOLTAGE', 'H_SPEED', 'T_SPEED', 'AZIM_F', 'TARGET_DIST', 'TARGET_AZIM', 'STATE', 'W_SPD', 'W_AZIM', 'V_WIN', 'A_WIN'] 
    
    log_file = None 
=======
    """Vypočítá horizontální rychlost v m/s pomocí Haversine a MILLIS."""
    d_time = (millis2 - millis1) / 1000.0
    if d_time <= 0: return 0.0
    # haversine vrací km, násobíme 1000 pro metry
    dist = haversine((lat1, lon1), (lat2, lon2)) * 1000 
    return dist / d_time


def data_reader_worker(data_queue, target_port, baud):
    # Upravte tento řádek (přidána G a H)
    sensor_map = {'M': 'MILLIS', 'A': 'ALT', 'B': 'TEMP', 'C': 'PRESS', 'D': 'LAT', 'E': 'LON', 'F': 'VOLTAGE', 'V': 'V_SPEED', 'R': 'RSSI', 'S': 'SNR', 'T':'STATE','G': 'TARGET_DIST', 'H': 'TARGET_AZIM', 'I': 'W_SPD', 'J': 'W_AZIM', 'K': 'V_WIN', 'L': 'A_WIN'}
    last_status = ""
    log_filename = f"cansat_log_{int(time.time())}.csv"
    # Uprav tento řádek v data_reader_worker:
    csv_keys = ['time', 'MILLIS', 'ALT', 'TEMP', 'PRESS', 'LAT', 'LON', 'V_SPEED', 'RSSI', 'SNR', 'VOLTAGE', 'H_SPEED', 'T_SPEED', 'AZIM_F', 'TARGET_DIST', 'TARGET_AZIM'] # Tyto dvě hodnoty posílá CanSat
>>>>>>> 5d3bb12931ea5ce3f14dc7820ed5b24694ca5cfa
    
    while True:
        port_to_open = target_port
        if target_port == "AUTO":
            port_to_open = None
            ports = serial.tools.list_ports.comports()
            for p in ports:
                desc = p.description.lower()
                if any(k in desc for k in ['arduino', 'ch340', 'cp210', 'cp210x', 'ftdi', 'usb serial', 'usb-serial']):
                    port_to_open = p.device
                    break
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
                data_queue.put({'type': 'msg', 'text': f"Connected to {port_to_open}. Logging to {log_filename}"})
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
                    
                    data['H_SPEED'] = data.get('H_SPEED', 0.0)
                    data['T_SPEED'] = data.get('T_SPEED', 0.0)
                    data['AZIM_F'] = data.get('AZIM_F', 0.0)
                    data['TARGET_DIST'] = data.get('TARGET_DIST', 0.0)
                    data['TARGET_AZIM'] = data.get('TARGET_AZIM', 0.0)

                    data_queue.put(data)
<<<<<<< HEAD
=======

                    # Write to CSV
>>>>>>> 5d3bb12931ea5ce3f14dc7820ed5b24694ca5cfa
                    row = [str(data.get(k, "")) for k in csv_keys]
                    log_file.write(",".join(row) + "\n")
                    log_file.flush()
                except: continue
        except serial.SerialException:
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

    def update_navigation(self, flight_azim, target_azim, wind_azim):
<<<<<<< HEAD
        f_rad = math.radians(flight_azim)
        t_rad = math.radians(target_azim)
        w_rad = math.radians(wind_azim)
        self.arrow_flight.set_data([f_rad, f_rad], [0, 1])
        self.arrow_target.set_data([t_rad, t_rad], [0, 0.9])
        self.arrow_wind.set_data([w_rad, w_rad], [0, 0.8])
=======
        # Převod na radiány pro polar plot
        f_rad = math.radians(flight_azim)
        t_rad = math.radians(target_azim)
        w_rad = math.radians(wind_azim)
    
        # Nastavení dat (od středu 0 k okraji 1)
        self.arrow_flight.set_data([f_rad, f_rad], [0, 1])
        self.arrow_target.set_data([t_rad, t_rad], [0, 0.9])
        self.arrow_wind.set_data([w_rad, w_rad], [0, 0.8])
        
        # Blit/Draw (v závislosti na tvém nastavení)
        self.draw_idle()
>>>>>>> 5d3bb12931ea5ce3f14dc7820ed5b24694ca5cfa
        
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

        self.nav_group = self.axes.inset_axes([0.02, 0.02, 0.2, 0.2], projection='polar')
        self.nav_group.set_facecolor('none')
<<<<<<< HEAD
        self.nav_group.set_theta_zero_location('N') 
        self.nav_group.set_theta_direction(-1)      
        self.nav_group.grid(False)
        self.nav_group.set_xticklabels([]); self.nav_group.set_yticklabels([])
        self.arrow_flight, = self.nav_group.plot([], [], color='#EA5A0C', linewidth=3)
        self.arrow_target, = self.nav_group.plot([], [], color='#00FF00', linewidth=3, linestyle='--')
        self.arrow_wind,   = self.nav_group.plot([], [], color='#00FFFF', linewidth=2)
=======
        self.nav_group.set_theta_zero_location('N') # Sever nahoře
        self.nav_group.set_theta_direction(-1)      # Po směru hodinových ručiček
        self.nav_group.grid(False)
        self.nav_group.set_xticklabels([])
        self.nav_group.set_yticklabels([])

        # Vytvoření šipek (rysek)
        self.arrow_flight, = self.nav_group.plot([], [], color='#EA5A0C', linewidth=3, label='Let')
        self.arrow_target, = self.nav_group.plot([], [], color='#00FF00', linewidth=3, linestyle='--', label='Cíl')
        self.arrow_wind,   = self.nav_group.plot([], [], color='#00FFFF', linewidth=2, label='Vítr')
>>>>>>> 5d3bb12931ea5ce3f14dc7820ed5b24694ca5cfa

    def on_draw(self, event):
        self.bg_cache = self.copy_from_bbox(self.axes.bbox)
        self.axes.draw_artist(self.path_line)
        self.axes.draw_artist(self.ground_dot)
        self.axes.draw_artist(self.cansat_dot)

    def render_full_map(self):
        w, h = self.width(), self.height()
        if w == 0 or h == 0: return
        aspect = 1 / np.cos(np.radians(self.ground_pos[1]))
        new_scale_lon = self.current_scale * (w / h) if w > h else self.current_scale
        new_scale_lat = (self.current_scale / aspect) if w > h else (self.current_scale / aspect) * (h / w)
        self.axes.set_xlim(self.ground_pos[0] - new_scale_lon, self.ground_pos[0] + new_scale_lon)
        self.axes.set_ylim(self.ground_pos[1] - new_scale_lat, self.ground_pos[1] + new_scale_lat)
        self.path_line.set_visible(False); self.cansat_dot.set_visible(False)
        
        try:
            self.axes.images = []
            cx.add_basemap(self.axes, crs='EPSG:4326', source=cx.providers.Esri.WorldImagery, zoom=16)
        except:
            try: cx.add_basemap(self.axes, crs='EPSG:4326', source=cx.providers.OpenStreetMap.Mapnik)
            except: pass
            
        self.draw()
        QtWidgets.QApplication.processEvents()
        self.path_line.set_visible(True); self.cansat_dot.set_visible(True)
        self.bg_cache = self.copy_from_bbox(self.axes.bbox)

    def update_position(self, lat, lon):
        if lat == 0 or lon == 0: return 
        self.path_lons.append(lon); self.path_lats.append(lat)
        self.path_line.set_data(self.path_lons[-300:], self.path_lats[-300:])
        self.cansat_dot.set_data([lon], [lat])
        if self.bg_cache is not None:
            self.restore_region(self.bg_cache)
            self.axes.draw_artist(self.path_line); self.axes.draw_artist(self.ground_dot); self.axes.draw_artist(self.cansat_dot)
            self.nav_group.draw_artist(self.arrow_flight); self.nav_group.draw_artist(self.arrow_target); self.nav_group.draw_artist(self.arrow_wind)
            self.blit(self.axes.bbox)
        else: self.draw_idle()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.resize_timer.start(400)

class GroundStation(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("CanSat Ground Station V1.1.14")
        self.setStyleSheet("""
            QMainWindow { background-color: #121212; color: #EEE; }
            QCheckBox::indicator { width: 14px; height: 14px; background-color: transparent; border: 1px solid #777; border-radius: 3px; } 
            QCheckBox::indicator:checked { background-color: #EA5A0C; border: 1px solid #EA5A0C; image: url("data:image/svg+xml;utf8,<svg width='14' height='14' viewBox='0 0 24 24' fill='none' stroke='white' stroke-width='4' stroke-linecap='round' stroke-linejoin='round' xmlns='http://www.w3.org/2000/svg'><polyline points='20 6 9 17 4 12'/></svg>"); }
        """)
        
<<<<<<< HEAD
=======
        # Najdi self.data a přidej tam tyto klíče 
>>>>>>> 5d3bb12931ea5ce3f14dc7820ed5b24694ca5cfa
        self.data = {k: [] for k in ['RSSI', 'SNR', 'TEMP', 'ALT', 'LAT', 'LON', 'GTSLP', 'U_LAT', 'PRESS', 'DIST', 'MILLIS', 'V_SPEED', 'DRIFT', 'CAN_DELTA', 'UPKEEP', "VOLTAGE", "STATE",'H_SPEED', 'T_SPEED', 'AZIM_F', "V_WIN", "A_WIN", "W_AZIM", "W_SPD",'TARGET_DIST', 'TARGET_AZIM']}
        self.sync_offset = 0 
        self.last_millis = 0
        self.start_time_pc = time.time() 
<<<<<<< HEAD
        self.last_map_update_t = time.time()
=======
>>>>>>> 5d3bb12931ea5ce3f14dc7820ed5b24694ca5cfa

        self.main_widget = QtWidgets.QWidget()
        self.setCentralWidget(self.main_widget)
        self.layout = QtWidgets.QVBoxLayout(self.main_widget)
        
        title_lbl = QtWidgets.QLabel("SPACE CARROTS CANSAT TX")
        title_lbl.setFont(QtGui.QFont("Arial", 20, QtGui.QFont.Weight.Bold))
        title_lbl.setStyleSheet("color: #EA5A0C;")
        self.layout.addWidget(title_lbl, alignment=QtCore.Qt.AlignmentFlag.AlignCenter)

<<<<<<< HEAD
        self.labels_layout = QtWidgets.QGridLayout()
        font = QtGui.QFont("Arial", 12) 
=======
        self.row1, self.row2, self.row3 = QtWidgets.QHBoxLayout(), QtWidgets.QHBoxLayout(), QtWidgets.QHBoxLayout()
        font = QtGui.QFont("Arial", 16)
>>>>>>> 5d3bb12931ea5ce3f14dc7820ed5b24694ca5cfa
        
        self.lbl_keys = ['Drift', 'World T', 'Upkeep', 'CanSat Cycle Δ', 'Ground Cycle Δ', 
                 'MSPF', 'RSSI', 'SNR', 'Alt', 'V_Speed', 'H_Speed', 'Total_Speed', 
                 'Lng', 'Lat', 'Dist', 'Azim_Target', 'Azim_Flight', 'Temp', 
                 'Pressure', "Battery voltage", "State", 'Wind_Spd', 'Wind_Azim', 'V_Win', 'A_Win']
        self.lbls = {k: QtWidgets.QLabel() for k in self.lbl_keys}

        self.lbls['State'].setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.lbls['State'].setMinimumWidth(100)
        
        colors = {'Drift': '#FF4500', 'Upkeep': '#FFFFFF', 'Ground Cycle Δ': '#FFD700', 'MSPF': '#FF00FF', 'RSSI': '#00FFFF', 'SNR': '#FFA500', 'Dist': '#9370DB', 'V_Speed': '#00FA9A', 'Alt': '#1E90FF', 'Temp': '#FF6A6A', 'Pressure': '#98FB98', 'CanSat Cycle Δ': '#FF6347', 'Voltage': "#6B1042"}
        data_labels = ['Drift', 'Upkeep', 'CanSat Cycle Δ', 'Ground Cycle Δ', 'RSSI', 'SNR', 'Alt', 'V_Speed', 'Lng', 'Lat', 'Dist', 'Temp', 'Pressure', "Battery voltage"]
        
        for i, k in enumerate(self.lbl_keys):
            lbl = self.lbls[k]
            lbl.setFont(font)
            if k in colors: lbl.setStyleSheet(f"color: {colors[k]};")
            
            if k == 'State':
<<<<<<< HEAD
                lbl.setText("IDLE") 
                lbl.setStyleSheet("background-color: #1E90FF; color: white; font-weight: bold; border-radius: 4px; padding: 2px;")
                lbl.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
=======
                lbl.setText("IDLE") # Výchozí text
                lbl.setStyleSheet("background-color: #1E90FF; color: white; font-weight: bold; border-radius: 8px;")
            # Apply initial N/A state using inline HTML so the label color is kept for the variable name
>>>>>>> 5d3bb12931ea5ce3f14dc7820ed5b24694ca5cfa
            elif k in data_labels:
                lbl.setText(f"{k}: <b><font color='#FF0000'>N/A</font></b>")
            else:
                lbl.setText(f"{k}: --")
                
<<<<<<< HEAD
            self.labels_layout.addWidget(lbl, i // 6, i % 6)
            
        self.layout.addLayout(self.labels_layout)
=======
            # 1. ŘÁDEK: Systémové věci a čas
            if k in ['Drift', 'World T', 'Upkeep', 'CanSat Cycle Δ', 'Ground Cycle Δ', 'MSPF', 'RSSI', 'SNR', "State"]:
                self.row1.addWidget(lbl)
            # 2. ŘÁDEK: Základní telemetrie letu
            elif k in ['Alt', 'V_Speed', 'H_Speed', 'Total_Speed', 'Temp', 'Pressure', 'Battery voltage']:
                self.row2.addWidget(lbl)
            # 3. ŘÁDEK: GPS, Cíl a Vítr
            else:
                self.row3.addWidget(lbl)
        
        self.layout.addLayout(self.row1); self.layout.addLayout(self.row2); self.layout.addLayout(self.row3)
>>>>>>> 5d3bb12931ea5ce3f14dc7820ed5b24694ca5cfa

        self.content = QtWidgets.QHBoxLayout()
        self.left_panel = QtWidgets.QVBoxLayout()
        
        self.toggle_container = QtWidgets.QHBoxLayout()
        
        self.toggle_grid = QtWidgets.QGridLayout()
        self.toggle_grid.setHorizontalSpacing(15) 
        
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
            ('Pressure', 'PRESS', colors['Pressure']),
            ('Battery voltage', 'VOLTAGE', colors['Voltage']),
<<<<<<< HEAD
            ('H-Speed', 'H_SPEED', '#FFD700'),     
            ('Total Speed', 'T_SPEED', '#FFFFFF'), 
            ('Flight Azimuth', 'AZIM_F', '#00FF00'), 
=======
            ('H-Speed', 'H_SPEED', '#FFD700'),     # Zlatá
            ('Total Speed', 'T_SPEED', '#FFFFFF'), # Bílá
            ('Flight Azimuth', 'AZIM_F', '#00FF00'), # Zelená
>>>>>>> 5d3bb12931ea5ce3f14dc7820ed5b24694ca5cfa
            ('Wind Speed', 'W_SPD', '#00FFFF'),
            ('Wind Azimuth', 'W_AZIM', '#FFA500'),
            ('Target Distance', 'TARGET_DIST', '#9370DB'),
            ('V-Win', 'V_WIN', '#FF00FF'),
            ('A-Win', 'A_WIN', '#FFFFFF')
        ]
        
        start_visible_keys = {'U_LAT', 'DIST', 'V_SPEED', 'ALT', 'DRIFT', 'CAN_DELTA', 'UPKEEP'}
        
        self.state_map = {
            0: ("IDLE", "#1E90FF"),
            1: ("LAUNCH", "#FF0000"),
            2: ("DEPLOYMENT", "#00AA00")
<<<<<<< HEAD
        }
=======
}
>>>>>>> 5d3bb12931ea5ce3f14dc7820ed5b24694ca5cfa

        checkboxes = []
        for i, (name, key, col) in enumerate(graph_configs):
            pw = pg.PlotWidget(title=name)
            pw.setMinimumHeight(60)
            pw.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Expanding)
            self.plots[key] = pw.plot(pen=col)
            pw.setVisible(key in start_visible_keys)
            self.graph_stack.addWidget(pw, stretch=1)
<<<<<<< HEAD
            
=======
            self.msg_log = QtWidgets.QTextEdit()
>>>>>>> 5d3bb12931ea5ce3f14dc7820ed5b24694ca5cfa
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
        
        for i, chk in enumerate(checkboxes):
            self.toggle_grid.addWidget(chk, i // 4, i % 4)
            
        self.toggle_container.addLayout(self.toggle_grid)
        
        self.btn_sync = QtWidgets.QPushButton("Sync Drift")
        self.btn_sync.setFixedSize(80, 50) 
        self.btn_sync.setStyleSheet("background:#FF2222; color:#FFF; font-weight:bold; border-radius:4px;")
        self.btn_sync.clicked.connect(self.do_sync)
        self.toggle_container.addWidget(self.btn_sync)

        self.left_panel.addLayout(self.toggle_container)
        self.left_panel.addLayout(self.graph_stack, stretch=1)
        
        self.left_widget = QtWidgets.QWidget()
        self.left_widget.setLayout(self.left_panel)
        self.left_widget.setMinimumWidth(500) 
        
        self.map_w = MapWidget()
        self.map_w.setSizePolicy(QtWidgets.QSizePolicy.Policy.Ignored, QtWidgets.QSizePolicy.Policy.Ignored)
        
        self.content.addWidget(self.left_widget, stretch=1)
        self.content.addWidget(self.map_w, stretch=1)
        
        self.layout.addLayout(self.content)

        self.last_ui_t = time.time()
        self.timer = QtCore.QTimer(); self.timer.timeout.connect(self.update_ui); self.timer.start(33)

    def do_sync(self):
        if self.data['MILLIS']:
            self.sync_offset = (time.time() - self.start_time_pc) * 1000 - self.data['MILLIS'][-1]
            self.msg_log.append("Drift Synced.")

    def update_state_label(self, state_num):
        text, color = self.state_map.get(state_num, ("", "#555555"))
<<<<<<< HEAD
        self.lbls['State'].setText(text)
        self.lbls['State'].setStyleSheet(f"background-color: {color}; color: white; font-weight: bold; padding: 2px; border-radius: 4px;")
=======

        self.lbls['State'].setText(text)
        self.lbls['State'].setStyleSheet(f"background-color: {color}; color: white; font-weight: bold; padding: 5px; border-radius: 8px;")
>>>>>>> 5d3bb12931ea5ce3f14dc7820ed5b24694ca5cfa

    def update_ui(self):
        now = time.time()
        ui_ms = (now - self.last_ui_t) * 1000
        self.last_ui_t = now
        self.lbls['World T'].setText(time.strftime("Time: %H:%M:%S"))
        real_ms = int((now - self.start_time_pc) * 1000)
        self.lbls['MSPF'].setText(f"MSPF: {ui_ms:.0f} ms")
        if 0 <= ui_ms < 500: self.data['U_LAT'].append(ui_ms)

        azim_flight = self.data['AZIM_F'][-1] if self.data['AZIM_F'] else 0.0

        last_packet = None
        while not q.empty():
            d = q.get()
            if d.get('type') == 'msg':
                self.msg_log.append(f"[{time.strftime('%H:%M:%S')}] {d['text']}"); continue
            
            curr_m = d.get('MILLIS', 0)
            
            for k in ['TEMP', 'ALT', 'LAT', 'LON', 'RSSI', 'SNR', 'PRESS', 'MILLIS', 'V_SPEED', "VOLTAGE", 'TARGET_DIST', 'TARGET_AZIM', 'W_SPD', 'W_AZIM', 'V_WIN']:
                self.data[k].append(d.get(k, 0.0))
            self.data['UPKEEP'].append(curr_m)
            
            can_delta = int(curr_m - self.last_millis) if self.last_millis != 0 else 0
            self.data['CAN_DELTA'].append(can_delta)
            
            gtslp = (now - d['time']) * 1000
            if 0 <= gtslp < 1000: self.data['GTSLP'].append(gtslp)
            
            drift = int((real_ms - self.sync_offset) - curr_m)
            self.data['DRIFT'].append(drift)

            self.data['STATE'].append(d.get('STATE', self.data['STATE'][-1] if self.data['STATE'] else 0))
            self.update_state_label(d.get('STATE', 0))
            
            self.last_millis = curr_m
            last_packet = d

            new_vals = {'Wind_Spd': f"{self.data.get('W_SPD', [0])[-1]:.1f} m/s", 'Wind_Azim': f"{self.data.get('W_AZIM', [0])[-1]:.0f}°", 'V_Win': f"{self.data.get('V_WIN', [0])[-1]:.1f} m/s"}
            for k, v in new_vals.items():
                if k in self.lbls:
                    self.lbls[k].setText(f"{k}: {v}")
<<<<<<< HEAD
=======

            if self.data['LAT']:
                # Získání posledních hodnot (pokud neexistují, použij 0)
                f_az = azim_flight if 'azim_flight' in locals() else 0
                t_az = self.data['TARGET_AZIM'][-1] if self.data['TARGET_AZIM'] else 0
                w_az = self.data['W_AZIM'][-1] if self.data['W_AZIM'] else 0
                
                # Aktualizace widgetu
                self.map_w.update_navigation(f_az, t_az, w_az)


    
>>>>>>> 5d3bb12931ea5ce3f14dc7820ed5b24694ca5cfa

        if last_packet:
            curr_m = last_packet.get('MILLIS', 0)
            self.lbls['Upkeep'].setText(f"Upkeep: {int(curr_m)//1000} {int(curr_m)%1000:03d}")
            self.lbls['CanSat Cycle Δ'].setText(f"CanSat Cycle Δ: {self.data['CAN_DELTA'][-1] if self.data['CAN_DELTA'] else 0} ms")
            self.lbls['Ground Cycle Δ'].setText(f"Ground Cycle Δ: {self.data['GTSLP'][-1]:.0f} ms")
            
            drift = self.data['DRIFT'][-1] if self.data['DRIFT'] else 0
            drift_txt = "<55ms" if abs(drift) < 55 else f"{drift} ms"
            self.lbls['Drift'].setText(f"Drift: {drift_txt}")

            if len(self.data['LAT']) >= 2:
                curr_lat, curr_lon = self.data['LAT'][-1], self.data['LON'][-1]
                prev_lat, prev_lon = self.data['LAT'][-2], self.data['LON'][-2]
                curr_m = self.data['MILLIS'][-1]
                prev_m = self.data['MILLIS'][-2]

                azim_flight = calculate_bearing(prev_lat, prev_lon, curr_lat, curr_lon)
                v_h = calculate_h_speed(prev_lat, prev_lon, curr_lat, curr_lon, prev_m, curr_m)
                v_v = self.data['V_SPEED'][-1]
                v_total = math.sqrt(v_h**2 + v_v**2)

                dist_from_cansat = last_packet.get('TARGET_DIST', 0.0)
                azim_target_from_cansat = last_packet.get('TARGET_AZIM', 0.0)

                self.lbls['Azim_Target'].setText(f"Target Brg (CS): {azim_target_from_cansat:.1f}°")
                self.lbls['Azim_Flight'].setText(f"Flight Dir: {azim_flight:.1f}°")
                self.lbls['H_Speed'].setText(f"H-Speed: {v_h:.2f} m/s")
                self.lbls['Total_Speed'].setText(f"Total Speed: {v_total:.2f} m/s")
                self.lbls['Dist'].setText(f"Dist (CS): {dist_from_cansat} m")

                self.data['H_SPEED'].append(v_h)
                self.data['T_SPEED'].append(v_total)
                self.data['AZIM_F'].append(azim_flight)
                self.data['DIST'].append(dist_from_cansat) 

            if now - self.last_map_update_t >= 1.0:
                if last_packet.get('LAT'):
                    self.map_w.update_position(last_packet['LAT'], last_packet['LON'])

                t_az = self.data['TARGET_AZIM'][-1] if self.data['TARGET_AZIM'] else 0
                w_az = self.data['W_AZIM'][-1] if self.data['W_AZIM'] else 0
                
                self.map_w.update_navigation(azim_flight, t_az, w_az)
                self.last_map_update_t = now

            if len(self.data['LAT']) >= 2:
                # Načtení dat pro výpočet směru LETU a horizontální RYCHLOSTI
                curr_lat, curr_lon = self.data['LAT'][-1], self.data['LON'][-1]
                prev_lat, prev_lon = self.data['LAT'][-2], self.data['LON'][-2]
                curr_m = self.data['MILLIS'][-1]
                prev_m = self.data['MILLIS'][-2]

                # 1. Směr LETU (stále počítáme v GTS, protože to CanSat obvykle neposílá)
                azim_flight = calculate_bearing(prev_lat, prev_lon, curr_lat, curr_lon)
                
                # 2. Rychlosti (stále počítáme v GTS)
                v_h = calculate_h_speed(prev_lat, prev_lon, curr_lat, curr_lon, prev_m, curr_m)
                v_v = self.data['V_SPEED'][-1]
                v_total = math.sqrt(v_h**2 + v_v**2)

                # 3. Získání hodnot, které POSLAL CANSAT
                # Pokud v paketu nejsou, použijeme 0
                dist_from_cansat = last_packet.get('TARGET_DIST', 0.0)
                azim_target_from_cansat = last_packet.get('TARGET_AZIM', 0.0)

                # 4. Aktualizace UI (labels)
                self.lbls['Azim_Target'].setText(f"Target Brg (CS): {azim_target_from_cansat:.1f}°")
                self.lbls['Azim_Flight'].setText(f"Flight Dir: {azim_flight:.1f}°")
                self.lbls['H_Speed'].setText(f"H-Speed: {v_h:.2f} m/s")
                self.lbls['Total_Speed'].setText(f"Total Speed: {v_total:.2f} m/s")
                self.lbls['Dist'].setText(f"Dist (CS): {dist_from_cansat} m")

                # Uložení do historie pro grafy
                self.data['H_SPEED'].append(v_h)
                self.data['T_SPEED'].append(v_total)
                self.data['AZIM_F'].append(azim_flight)
                self.data['DIST'].append(dist_from_cansat) # Přepisujeme vypočtenou hodnotu tou z CanSatu

        if not self.data['ALT']: return
        for k in self.data: self.data[k] = self.data[k][-300:]
        for k in ['TEMP', 'ALT', 'RSSI', 'SNR', 'PRESS', 'DIST', 'V_SPEED', 'H_SPEED', 'T_SPEED', 'AZIM_F', 'GTSLP', 'U_LAT', 'DRIFT', 'CAN_DELTA', 'UPKEEP', "VOLTAGE"]:
            if self.data[k]: 
                self.plots[k].setData(self.data[k])
        
        vals = {'Dist': f"{self.data['DIST'][-1]} m", 'V_Speed': f"{self.data['V_SPEED'][-1]} m/s", 'Alt': f"{self.data['ALT'][-1]} m", 'Lng': f"{self.data['LON'][-1]:.5f}", 'Lat': f"{self.data['LAT'][-1]:.5f}", 'Temp': f"{self.data['TEMP'][-1]} °C", 'Pressure': f"{self.data['PRESS'][-1]} hPa", 'RSSI': f"{self.data['RSSI'][-1]} dBm", 'SNR': f"{self.data['SNR'][-1]} dB", 'Battery voltage': f"{self.data['VOLTAGE'][-1]} V"}
        for k, v in vals.items(): self.lbls[k].setText(f"{k}: {v}")

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    threading.Thread(target=data_reader_worker, args=(q, SERIAL_PORT, BAUD_RATE), daemon=True).start()
    w = GroundStation(); w.show(); sys.exit(app.exec())