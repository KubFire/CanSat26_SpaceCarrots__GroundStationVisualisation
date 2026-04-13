#Developement branch - visualising simulated data from test_lora_log.txt
#V1.0

"""
TO DO List


"""
import queue
import sys
import threading
import time
import csv
from PyQt6 import QtWidgets, QtCore, QtGui
import pyqtgraph as pg
import numpy as np
from haversine import haversine
import contextily as cx

# Matplotlib v PyQt
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

# setup
q = queue.Queue(maxsize=10) 
export_file = "telemetry_export.csv"
data_file = 'test_lora_log.txt'

# --- TVOJE GPS POZICE (Ground Station) ---
ground_lat = 49.7950 
ground_lon = 16.6800 

# Cíl/Terč (pro výpočet Dist)
target_lat = 49.7985833
target_lon = 16.6877778

def data_reader_worker(data_queue, file_path):
    with open(export_file, "w", newline="") as f:
        csv.writer(f).writerow(["timestamp", "temp", "rssi", "snr", "press", "lon", "lat", "alt"])
    
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
                        velicina = item[0].upper()
                        try:
                            val = float(item[1:])
                            data[sensor_map.get(velicina, velicina)] = val
                        except: continue
                
                for key in ["TEMP", "RSSI", "SNR", "PRESS", "LON", "LAT", "ALT"]:
                    if key not in data: data[key] = 0.0
                
                with open(export_file, "a", newline="") as f:
                    csv.writer(f).writerow([data["time"], data["TEMP"], data["RSSI"], data["SNR"], data["PRESS"], data["LON"], data["LAT"], data["ALT"]])
                
                if data_queue.full():
                    try: data_queue.get_nowait()
                    except: pass
                
                data_queue.put(data)
                time.sleep(0.1)
    except FileNotFoundError:
        print("Soubor nenalezen.")

#---------------------------------------MAPA-----------------------
class MapWidget(FigureCanvas):
    def __init__(self, parent=None):
        self.fig = Figure(figsize=(5, 5), dpi=100)
        self.axes = self.fig.add_subplot(111)
        super().__init__(self.fig)
        
        self.path_lons, self.path_lats = [], []
        self.cansat_pos = [0, 0]
        self.ground_pos = [ground_lon, ground_lat]
        
        self.setup_plot()
        
    def setup_plot(self):
        self.fig.patch.set_facecolor('#121212')
        self.axes.set_facecolor('#121212')
        self.axes.set_axis_off() 
        self.axes.set_aspect('equal', adjustable='datalim')
        
        # Pozemní stanice (Pink)
        self.ground_dot, = self.axes.plot([self.ground_pos[0]], [self.ground_pos[1]], 
                                          'o', color='#FF69B4', markersize=12, label='Ground', zorder=10)
        # CanSat (Orange)
        self.cansat_dot, = self.axes.plot([], [], 'o', color='#FFA500', markersize=12, label='CanSat', zorder=11)
        
        self.fig.subplots_adjust(left=0, right=1, top=1, bottom=0)

    def update_view(self):
        """Inteligentní centrování a zoomování"""
        # Střed mezi námi a CanSatem
        center_lon = (self.ground_pos[0] + self.cansat_pos[0]) / 2
        center_lat = (self.ground_pos[1] + self.cansat_pos[1]) / 2
        
        # Výpočet potřebného rozpětí (s 30% marginem)
        diff_lon = abs(self.ground_pos[0] - self.cansat_pos[0]) * 1.3
        diff_lat = abs(self.ground_pos[1] - self.cansat_pos[1]) * 1.3
        
        # Minimální zoom, aby mapa nebyla moc "nalepená"
        margin = max(diff_lon, diff_lat, 0.005)
        
        self.axes.set_xlim(center_lon - margin, center_lon + margin)
        self.axes.set_ylim(center_lat - margin, center_lat + margin)
        
        try:
            # Vyčištění staré mapy před novým stažením dlaždic (řeší zasekávání na černé)
            self.axes.images = [] 
            cx.add_basemap(self.axes, crs='EPSG:4326', source=cx.providers.OpenStreetMap.Mapnik)
        except: pass

    def update_position(self, lat, lon):
        self.cansat_pos = [lon, lat]
        self.path_lons.append(lon)
        self.path_lats.append(lat)
        
        lons, lats = self.path_lons[-500:], self.path_lats[-500:]
        n = len(lons)
        colors = np.zeros((n, 4))
        colors[:, 0] = 1.0; colors[:, 1] = 0.5; colors[:, 3] = np.linspace(0.1, 0.8, n)
        
        if hasattr(self, 'scatter'): self.scatter.remove()
        self.scatter = self.axes.scatter(lons, lats, c=colors, s=15, zorder=5)
        self.cansat_dot.set_data([lon], [lat])

#------------------------------------Samotna-vizualizace-----------------------

class GroundStation(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("CanSat Ground Station - Present Mode")
        self.data = {k: [] for k in ['RSSI', 'SNR', 'TEMP', 'ALT', 'LAT', 'LON', 'D_LAT', 'U_LAT']}
        
        self.main_widget = QtWidgets.QWidget()
        self.setCentralWidget(self.main_widget)
        self.layout = QtWidgets.QVBoxLayout(self.main_widget)
        
        self.top_panel = QtWidgets.QHBoxLayout()
        font = QtGui.QFont(); font.setPointSize(16)
        self.lbls = {}
        for k in ['Real T', 'Packet T', 'ALT', 'Dist', 'TSLP', 'UI Frame']:
            self.lbls[k] = QtWidgets.QLabel(f"{k}: --")
            self.lbls[k].setFont(font)
            self.top_panel.addWidget(self.lbls[k])
        
        self.lbls['Packet T'].setText("Packet T: N/A")
        self.lbls['Packet T'].setStyleSheet("color: red;")
        self.layout.addLayout(self.top_panel)

        self.content = QtWidgets.QHBoxLayout()
        self.graph_stack = QtWidgets.QVBoxLayout()
        
        self.plots = {}
        configs = [('TEMP', 'r'), ('ALT', 'b'), ('Data Latency', 'y'), ('UI Frame Latency', 'm')]
        for name, color in configs:
            pw = pg.PlotWidget(title=name)
            self.plots[name] = pw.plot(pen=color)
            self.graph_stack.addWidget(pw)
            
        self.map_widget = MapWidget()
        self.content.addLayout(self.graph_stack, stretch=1)
        self.content.addWidget(self.map_widget, stretch=1)
        self.layout.addLayout(self.content)
        
        self.last_ui_time = time.time()
        self.last_map_time = 0
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.update_ui)
        self.timer.start(50)
        
    def update_ui(self):
        now = time.time()
        ui_ms = (now - self.last_ui_time) * 1000
        self.last_ui_time = now
        
        self.lbls['Real T'].setText(f"Real T: {int(now*1000)%100000:05d}")
        self.lbls['UI Frame'].setText(f"UI Frame: {ui_ms:.0f} ms")
        self.data['U_LAT'].append(ui_ms)

        updated = False
        while not q.empty():
            d = q.get()
            self.data['TEMP'].append(d['TEMP']); self.data['ALT'].append(d['ALT'])
            self.data['LAT'].append(d['LAT']); self.data['LON'].append(d['LON'])
            self.data['D_LAT'].append((now - d['time']) * 1000)
            
            if d['LAT'] != 0:
                self.map_widget.update_position(d['LAT'], d['LON'])
                updated = True

        if not self.data['ALT']: return
        for k in self.data: self.data[k] = self.data[k][-500:]
        
        self.plots['TEMP'].setData(self.data['TEMP'])
        self.plots['ALT'].setData(self.data['ALT'])
        self.plots['Data Latency'].setData(self.data['D_LAT'])
        self.plots['UI Frame Latency'].setData(self.data['U_LAT'])
        
        self.lbls['ALT'].setText(f"ALT: {self.data['ALT'][-1]} m")
        tslp = self.data['D_LAT'][-1]
        self.lbls['TSLP'].setText(f"TSLP: {tslp:.0f} ms")
        self.lbls['TSLP'].setStyleSheet(f"color: {'green' if tslp < 100 else 'red'};")
        
        dist = round(haversine((self.data['LAT'][-1], self.data['LON'][-1]), (target_lat, target_lon))*1000, 1)
        self.lbls['Dist'].setText(f"Dist: {dist}m")

        # Easing/Throttling mapy: Aktualizace 1x za 2 sekundy, aby se mapa nezasekávala
        if updated and (now - self.last_map_time) > 2.0:
            self.map_widget.update_view()
            self.map_widget.draw()
            self.last_map_time = now

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    app.setStyle("Fusion")
    threading.Thread(target=data_reader_worker, args=(q, data_file), daemon=True).start()
    w = GroundStation(); w.show()
    sys.exit(app.exec())