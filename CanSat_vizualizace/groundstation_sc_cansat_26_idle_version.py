# OOP: https://realpython.com/python3-object-oriented-programming/
# Threading: https://realpython.com/intro-to-python-threading/
# PyQt6 tutorial: https://www.pythonguis.com/pyqt6-tutorial/

#TODO: branding     

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
import serial #knihovna se jmenuje pyserial

# Matplotlib v PyQt
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

#setup
q = queue.Queue(maxsize=0) #nekonečná fronta
export_file = "telemetry_export.csv" #sem se budou zapisovat data
data_file = 'test_lora_log.txt' #simulace čtení
# nastavit umístění terče
target_lat = 49.7985833
target_lon = 16.6877778

print("soubory načteny")

def data_reader_worker(data_queue, port):
    """
    the worker - reads the file (later serial port) 
    and pushes data onto the queue
    """
    try:
        serial_setup = serial.Serial(port, 115200, timeout=1)
    except Exception as e:
        print(f"Port {port} nelze otevřít: {e}")
        return
    
    with open(export_file, "w", newline="") as f:
        csv.writer(f).writerow(["timestamp", "temp", "rssi", "snr", "press", "lon", "lat", "alt"])
    print("header ready")
    
    while True:
        if serial_setup.in_waiting:
            line = serial_setup.readline().decode('utf-8').strip()
            if not line:
                continue
            
            data = {} #python dictionary
            
            try:
                    parts = line.split('|') #line.strip().split... by mazalo mezery na konci a na začátku řádku - nemáme
                    print(parts)
                    for values in parts[0].split(';'): #první z parts - naše data rozdělí po veličinách
                        velicina = values[0]
                        hodnota = float(values[1:])
                        data[velicina] = hodnota
                            
                    #for p in parts[1:]: #od [0]jedné dále - rssi, snr
                    for values in parts[1:]:
                        velicina = values[0]
                        #print(velicina)
                        hodnota = float(values[1:])
                        data[velicina] = hodnota
                        #print(data)
                            
            except:
                print("problém s parsováním")
                continue
                           
            data['time'] = time.time()
            
            if "A" in data:
                data["TEMP"] = data["A"]
                del data["A"]
                
            if "B" in data:
                data["HUM"] = data["B"]
                del data["B"]
                
            if "F" in data:
                data["LON"] = data["F"]
                del data["F"]
                
            if "E" in data:
                data["LAT"] = data["E"]
                del data["E"]
                
            if "D" in data:
                data["PRESS"] = data["D"]
                del data["D"]
                
            if "C" in data:
                data["ALT"] = data["C"]
                del data["C"]
                
            if "R" in data:
                data["RSSI"] = data["R"]
                del data["R"]
                
            if "S" in data:
                data["SNR"] = data["S"]
                del data["S"]
            ### takhle pro všechno co tam bude
            
            print(data)
            
            with open(export_file, "a", newline="") as f:
                writer = csv.writer(f)
                # zápis dat do .csv
                writer.writerow([data["time"], data["TEMP"], data["RSSI"], data["SNR"], data["PRESS"], data["LON"], data["LAT"], data["ALT"]])
            
            # Posílání dat do fronty
            data_queue.put(data)
            #to be removed when real time
            time.sleep(0.1)
                    
class MapWidget(FigureCanvas):
    def __init__(self, parent=None):
        self.fig = Figure(figsize=(5, 4), dpi=100, facecolor="#FF4400") 
        self.axes = self.fig.add_subplot(111)
        super().__init__(self.fig)
        
        # Rozsah mapy = okolí Moravské Třebové - ZMĚNIT!!!!!
        self.extent = [16.67, 16.72, 49.78, 49.82] # [min_lon, max_lon, min_lat, max_lat]
        self.path_lons = []
        self.path_lats = []
        self.map_loaded = False
        self.setup_plot()
        
    def setup_plot(self):

            self.fig.patch.set_facecolor('#121212')  # Pozadí plátna
            self.axes.set_facecolor('#121212')       # Pozadí pod mapou
            
            # vypnutí os
            self.axes.set_axis_off() 
            
            self.axes.set_aspect('equal', adjustable='box')
            
            self.line, = self.axes.plot([], [], color='#FF4400', linewidth=2, zorder=5)
            self.dot, = self.axes.plot([], [], 'ro', markersize=8, zorder=6)

            # Nastavení limitů bez zobrazení os
            self.axes.set_xlim(self.extent[0], self.extent[1])
            self.axes.set_ylim(self.extent[2], self.extent[3])
            
            if not self.map_loaded:
                self.refresh_map()
                self.map_loaded = True
            
            # 3. Odstraníme bílé okraje kolem grafu
            self.fig.subplots_adjust(left=0, right=1, top=1, bottom=0)

    def refresh_map(self):
        """Stáhne a vykreslí mapu jako backround grafu"""
        try:
            # crs='EPSG:4326'= používáme klasické GPS souřadnice (WGS84)
            # source určuje vzhled mapy
            cx.add_basemap(self.axes, crs='EPSG:4326', source=cx.providers.OpenStreetMap.Mapnik)
        except Exception as e:
            print(f"Chyba při načítání mapy (asi není připojení): {e}")

    def update_position(self, lat, lon):
        if lat is None or lon is None:
            return
            
        self.path_lons.append(lon)
        self.path_lats.append(lat)

        # Omezí počet bodů, aby se mapa nesekala
        display_lons = self.path_lons[-500:]
        display_lats = self.path_lats[-500:]
        n = len(display_lons)

        # Vytvoří gradient, staré body budou tmavé
        colors = np.zeros((n, 4))
        colors[:, 0] = 1.0  # Red složka
        colors[:, 1] = 0.26 # Green složka
        colors[:, 2] = 0.0  # Blue složka
        
        # Nastaví průhlednost (alpha chanell) od 0.1 (staré) po 1.0 (nové)
        alphas = np.linspace(0.1, 1.0, n)
        colors[:, 3] = alphas

        # Vykreslíme body s přechodem barev
        self.scatter = self.axes.scatter(display_lons, display_lats, 
                                         c=colors, s=20, zorder=5)
        
        # Samostatná tečka pro aktuální pozici (nejvýraznější)
        self.dot.set_data([lon], [lat])
        
        self.draw()

class GroundStation(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("CanSat Ground Station")
        #self.resize(1000, 800)
        
        #vlastní, nesdílené seznamy pro tento jeden objekt    
        self.data_rssi = []
        self.data_snr = []
        self.data_temp = []
        self.data_time = []
        self.data_alt = []
        self.data_pres = []
        self.data_lon = []
        self.data_lat = []
        
        
        # Central widget and layout
        self.main_widget = QtWidgets.QWidget()
        self.setCentralWidget(self.main_widget)
        
        # Vertical layout to hold the top bar and the content area
        self.main_v_layout = QtWidgets.QVBoxLayout(self.main_widget)
        self.top_row_layout = QtWidgets.QHBoxLayout()
        
        ########## Telemetrie ############
        self.top_row = QtWidgets.QHBoxLayout()
        
        self.rssi_label = QtWidgets.QLabel("RSSI: --")
        font = self.rssi_label.font()
        font.setPointSize(20)
        self.rssi_label.setFont(font)
        self.rssi_label.setAlignment(
            QtCore.Qt.AlignmentFlag.AlignLeft | QtCore.Qt.AlignmentFlag.AlignVCenter
        )
        self.top_row_layout.addWidget(self.rssi_label)
        
        self.snr_label = QtWidgets.QLabel("SNR: --")
        self.top_row.addWidget(self.snr_label)
        font = self.snr_label.font()
        font.setPointSize(20)
        self.snr_label.setFont(font)
        self.snr_label.setAlignment(
            QtCore.Qt.AlignmentFlag.AlignLeft| QtCore.Qt.AlignmentFlag.AlignVCenter
        )
        self.top_row_layout.addWidget(self.snr_label)
        
        self.alt_label = QtWidgets.QLabel("ALT: --")
        self.top_row.addWidget(self.alt_label)
        font = self.alt_label.font()
        font.setPointSize(20)
        self.alt_label.setFont(font)
        self.alt_label.setAlignment(
            QtCore.Qt.AlignmentFlag.AlignLeft | QtCore.Qt.AlignmentFlag.AlignVCenter
        )
        self.top_row_layout.addWidget(self.alt_label)
        
        self.lon_label = QtWidgets.QLabel("LON: --")
        self.top_row.addWidget(self.lon_label)
        font = self.lon_label.font()
        font.setPointSize(20)
        self.lon_label.setFont(font)
        self.lon_label.setAlignment(
            QtCore.Qt.AlignmentFlag.AlignLeft| QtCore.Qt.AlignmentFlag.AlignVCenter
        )
        self.top_row_layout.addWidget(self.lon_label)
        
        self.lat_label = QtWidgets.QLabel("LAT: --")
        self.top_row.addWidget(self.lat_label)
        font = self.lat_label.font()
        font.setPointSize(20)
        self.lat_label.setFont(font)
        self.lat_label.setAlignment(
            QtCore.Qt.AlignmentFlag.AlignLeft| QtCore.Qt.AlignmentFlag.AlignVCenter
        )
        self.top_row_layout.addWidget(self.lat_label)
        
        self.distance_label = QtWidgets.QLabel("Distance from target: --")
        self.top_row.addWidget(self.distance_label)
        font = self.distance_label.font()
        font.setPointSize(20)
        self.distance_label.setFont(font)
        self.distance_label.setAlignment(
            QtCore.Qt.AlignmentFlag.AlignLeft| QtCore.Qt.AlignmentFlag.AlignVCenter
        )
        self.top_row_layout.addWidget(self.distance_label)
        
        self.main_v_layout.addLayout(self.top_row_layout)
        
        self.content_layout = QtWidgets.QHBoxLayout()
        self.main_v_layout.addLayout(self.content_layout)
        
        # --- Střední část ---
        self.middle_layout = QtWidgets.QHBoxLayout()

        # Sloupec pro grafy
        self.graph_col = QtWidgets.QVBoxLayout()
        
        # Add graph column to content layout (stretch=x určuje šířku okna)
        self.content_layout.addLayout(self.graph_col, stretch=1)
        
        # Vytvoření mapy
        self.map_widget = MapWidget()
        self.content_layout.addWidget(self.map_widget, stretch=1)
        
        # Tlak (Pressure)
        self.pres_plot = pg.PlotWidget(title="Pressure")
        self.pres_curve = self.pres_plot.plot(pen='g') # green
        self.graph_col.addWidget(self.pres_plot)

        # Teplota (Temp)
        self.temp_plot = pg.PlotWidget(title="Temperature")
        self.temp_curve = self.temp_plot.plot(pen='r') # red
        self.graph_col.addWidget(self.temp_plot)

        # Výška (Altitude)
        self.alt_plot = pg.PlotWidget(title="Altitude")
        self.alt_curve = self.alt_plot.plot(pen='b') # blue
        self.graph_col.addWidget(self.alt_plot)
        
        # kontroluje frontu každých 100ms
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.update_ui)
        self.timer.start(1000)
        
    def hav(self, target_lat, target_lon, lat, lon):
        """
        Haversine formula counts distance between two points on the sphere
        """
        cansat = (lat,lon)
        target = (target_lat, target_lon)
        distance = haversine(cansat, target)*1000 #in meters
        distance = round(distance, 3)
        return distance
    
    def update_ui(self):
        while not q.empty():
            
            data = q.get()
            self.data_temp.append(data['TEMP'])
            self.data_time.append(data['time'])
            self.data_rssi.append(data['RSSI'])
            self.data_alt.append(data['ALT'])
            self.data_snr.append(data['SNR'])
            self.data_pres.append(data['PRESS'])
            self.data_lat.append(data['LAT'])
            self.data_lon.append(data['LON'])
            
            # Keep only last 500 points to save memory
            self.data_temp = self.data_temp[-500:]
            self.data_time = self.data_time[-500:]
            self.data_rssi = self.data_rssi[-500:]
            self.data_pres = self.data_pres[-500:]
            self.data_lat = self.data_lat[-500:]
            self.data_lon = self.data_lon[-500:]
            self.data_alt = self.data_alt[-500:]
            self.data_rssi = self.data_rssi[-500:]
            self.data_snr = self.data_snr[-500:]
            
            # Update graph
            self.temp_curve.setData(self.data_temp)
            self.alt_curve.setData(self.data_alt)
            self.pres_curve.setData(self.data_pres)
            
            # Update horního panelu
            latest_rssi = self.data_rssi[-1]
            self.rssi_label.setText(f"RSSI: {latest_rssi} dBm")
            if latest_rssi > -90:
                self.rssi_label.setStyleSheet("color: green;")
            elif latest_rssi > -110:
                self.rssi_label.setStyleSheet("color: orange;")
            else:
                self.rssi_label.setStyleSheet("color: red;")
            
            latest_snr = self.data_snr[-1]
            self.snr_label.setText(f"SNR: {latest_snr} dB ")
            if latest_snr > 5:
                self.snr_label.setStyleSheet("color: green;")
            elif latest_snr > 0:
                self.snr_label.setStyleSheet("color: orange;")
            elif latest_snr > -20:
                self.snr_label.setStyleSheet("color: red;")
            else:
                self.snr_label.setStyleSheet("color: black;")
                
            if len(self.data_alt) >= 2:
                latest_alt = self.data_alt[-1]
                latest_alt_2 = self.data_alt[-2]
                self.alt_label.setText(f"ALT: {latest_alt} m")
                if latest_alt < latest_alt_2:
                    self.alt_label.setStyleSheet("color: green;")
                else:
                    self.alt_label.setStyleSheet("color: blue;")
            else:
                latest_alt = self.data_alt[-1]
                self.alt_label.setText(f"ALT: {latest_alt} m")
            
            
            latest_lat = self.data_lat[-1]
            latest_lat_display = round(latest_lat, 2)
            self.lat_label.setText(f"LAT: {latest_lat_display}°")
            
            latest_lon = self.data_lon[-1]
            latest_lon_display = round(latest_lon, 2)
            self.lon_label.setText(f"LON: {latest_lon_display}°")
            
            latest_distance = self.hav(target_lat, target_lon, latest_lat, latest_lon)
            self.distance_label.setText(f"Distance from target: {latest_distance} m")
            if latest_distance < 20:
                self.distance_label.setStyleSheet("color: green;")
            elif latest_distance < 50:
                self.distance_label.setStyleSheet("color: orange;")
            elif latest_distance < 100:
                self.distance_label.setStyleSheet("color: red;")
            else:
                self.distance_label.setStyleSheet("color: black;")
            
            # Update pozice na mapě
            lat = data.get('LAT')
            lon = data.get('LON')
            self.map_widget.update_position(lat, lon)
           
if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    
    app.setStyle("Fusion")

    # daemon=True zajišťuje, že se vlákno vypne, když zavřu okno
    thread = threading.Thread(target=data_reader_worker, args=(q, "COM3"), daemon=True)
    thread.start()

    # Spuštění okna
    window = GroundStation()
    window.show()
    
    sys.exit(app.exec())
