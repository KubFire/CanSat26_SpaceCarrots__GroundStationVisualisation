/*
LEGENDA SENSOR_MAP:
M: MILLIS (čas od startu v ms)
B: TEMP (teplota)
C: HUM (vlhkost)
D: ALT (výška)
E: PRESS (tlak)
F: LAT (šířka)
G: LON (délka)
S: RSSI (síla signálu)
T: SNR (odstup signál-šum)
*/

float ground_lat = 49.7950;
float ground_lon = 16.6800;

float current_lat = 49.7950;
float current_lon = 16.6786; 

float altitude = 0;
float phase = 0; 
unsigned long startTime;

void setup() {
  Serial.begin(115200);
  startTime = millis();
}

void loop() {
  unsigned long currentTime = millis() - startTime;
  float t = currentTime / 1000.0;

  if (phase == 0) {
    altitude = 400 * t - 20 * t * t; 
    if (altitude > 1000 || t > 10) {
      altitude = 1000;
      phase = 1;
      startTime = millis();
    }
    current_lon += 0.000002; 
  } else {
    altitude -= 5.0;
    if (altitude < 0) altitude = 0;
    
    if (altitude > 0) {
      current_lon += 0.00001; 
      current_lat += 0.000002;
    }
  }

  float temp = 25.0 - (altitude / 100.0);
  float hum = 45.0 + (altitude / 50.0);
  float press = 1013.25 * pow((1 - 0.0000225577 * altitude), 5.25588);
  int rssi = random(-110, -30);
  float snr = random(5, 120) / 10.0;

  // Formát: M[ms];B[temp];C[hum];D[alt];E[press];F[lat];G[lon];S[rssi];T[snr]
  Serial.print("M"); Serial.print(millis());
  Serial.print(";B"); Serial.print(temp, 2);
  Serial.print(";C"); Serial.print(hum, 1);
  Serial.print(";D"); Serial.print(altitude, 2);
  Serial.print(";E"); Serial.print(press, 2);
  Serial.print(";F"); Serial.print(current_lat, 6);
  Serial.print(";G"); Serial.print(current_lon, 6);
  Serial.print(";S"); Serial.print(rssi);
  Serial.print(";T"); Serial.println(snr, 1);

  delay(50);
}