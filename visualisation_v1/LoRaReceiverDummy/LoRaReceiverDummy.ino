float ground_lat = 49.7950;
float ground_lon = 16.6800;

// Startovní pozice (100m západně)
// 100m na západ v těchto zeměpisných šířkách je cca -0.0014 stupně v longitude
float current_lat = 49.7950;
float current_lon = 16.6786; 

float altitude = 0;
float velocity = 0;
float phase = 0; // 0: Vzestup, 1: Sestup
unsigned long startTime;

void setup() {
  Serial.begin(115200);
  startTime = millis();
}

void loop() {
  unsigned long currentTime = millis() - startTime;
  float t = currentTime / 1000.0; // čas v sekundách

  // Simulace trajektorie
  if (phase == 0) {
    // Vzestup do 1km (zjednodušená parabola pro simulaci)
    altitude = 400 * t - 20 * t * t; 
    if (altitude > 1000 || t > 10) {
      altitude = 1000;
      phase = 1;
      startTime = millis(); // Reset pro fázi sestupu
    }
    // Horizontální posun při vzestupu (200m)
    current_lon += 0.000002; 
  } else {
    // Sestup z 1km na 0 (pomalý pád na padáku)
    altitude -= 5.0; // 5 m/s klesání
    if (altitude < 0) altitude = 0;
    
    // Horizontální posun při sestupu (1km)
    if (altitude > 0) {
      current_lon += 0.00001; 
      current_lat += 0.000002;
    }
  }

  // Generování believable dat
  float temp = 25.0 - (altitude / 100.0); // Teplota klesá s výškou
  float hum = 45.0 + (altitude / 50.0);
  float press = 1013.25 * pow((1 - 0.0000225577 * altitude), 5.25588);
  int rssi = random(-110, -30);
  float snr = random(5, 120) / 10.0;

  // Formátování výstupu dle sensor_map
  // A:TEMP, B:HUM, C:ALT, D:PRESS, E:LAT, F:LON, R:RSSI, S:SNR
  Serial.print("A:"); Serial.print(temp, 2);
  Serial.print(",B:"); Serial.print(hum, 1);
  Serial.print(",C:"); Serial.print(altitude, 2);
  Serial.print(",D:"); Serial.print(press, 2);
  Serial.print(",E:"); Serial.print(current_lat, 6);
  Serial.print(",F:"); Serial.print(current_lon, 6);
  Serial.print(",R:"); Serial.print(rssi);
  Serial.print(",S:"); Serial.println(snr, 1);

  delay(500); // Simulace intervalu LoRa zpráv
}