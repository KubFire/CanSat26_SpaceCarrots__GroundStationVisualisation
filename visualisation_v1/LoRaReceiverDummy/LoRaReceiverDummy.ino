/*
LEGENDA SENSOR_MAP:
M: MILLIS (čas od startu v ms)
A: ALT (výška v m)
B: TEMP (teplota v °C)
C: HUM (vlhkost v %)
D: PRESS (tlak v hPa)
E: LAT (šířka)
F: LON (délka)
V: V_SPEED (rychlost klesání/stoupání v m/s)
R: RSSI (síla signálu v dBm)
S: SNR (odstup signál-šum v dB)
*/

float ground_lat = 49.7950;
float ground_lon = 16.6800;

float current_lat = 49.7950;
float current_lon = 16.6786; 

float altitude = 0;
float vertical_speed = 0;
float phase = 0; 
unsigned long startTime;
unsigned long lastUpdate;

void setup() {
  Serial.begin(115200);
  startTime = millis();
  lastUpdate = millis();
}

void loop() {
  unsigned long now = millis();
  float dt = (now - lastUpdate) / 1000.0;
  if (dt <= 0.001) dt = 0.001; 
  lastUpdate = now;

  unsigned long currentTime = now - startTime;
  float t = currentTime / 1000.0;

  if (phase == 0) {
    // Vzestup
    float next_alt = 400 * t - 20 * t * t;
    vertical_speed = (next_alt - altitude) / dt;
    altitude = next_alt;

    if (altitude > 1000 || vertical_speed <= 0) {
      altitude = 1000;
      phase = 1;
      startTime = now;
    }
    current_lon += 0.0000005;
  } else {
    // Sestup 4m/s
    vertical_speed = -4.0;
    altitude += vertical_speed * dt;
    
    if (altitude < 0) {
      altitude = 0;
      vertical_speed = 0;
    }
    
    if (altitude > 0) {
      current_lon += 0.000002; 
      current_lat += 0.0000005;
    }
  }

  float temp = 25.0 - (altitude / 100.0);
  float hum = 45.0 + (altitude / 50.0);
  float press = 1013.25 * pow((1 - 0.0000225577 * altitude), 5.25588);
  int rssi = random(-110, -30);
  float snr = random(5, 120) / 10.0;

  // Formát: M;A;B;C;D;E;F;V;R;S
  Serial.print("M"); Serial.print(now);
  Serial.print(";A"); Serial.print(altitude, 2);
  Serial.print(";B"); Serial.print(temp, 2);
  Serial.print(";C"); Serial.print(hum, 1);
  Serial.print(";D"); Serial.print(press, 2);
  Serial.print(";E"); Serial.print(current_lat, 6);
  Serial.print(";F"); Serial.print(current_lon, 6);
  Serial.print(";V"); Serial.print(vertical_speed, 2);
  Serial.print(";R"); Serial.print(rssi);
  Serial.print(";S"); Serial.println(snr, 1);

  delay(50); 
}