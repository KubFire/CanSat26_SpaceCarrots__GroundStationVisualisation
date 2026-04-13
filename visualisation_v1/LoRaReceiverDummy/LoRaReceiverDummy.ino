/*
LEGENDA SENSOR_MAP:
M: MILLIS (čas od zapnutí v ms)
A: ALT (výška v m)
B: TEMP (teplota v °C)
C: HUM (vlhkost v %)
D: PRESS (tlak v hPa)
E: LAT (šířka)
F: LON (délka)
V: V_SPEED (vertikální rychlost v m/s)
R: RSSI (síla signálu v dBm)
S: SNR (odstup signál-šum v dB)
X: STATUS (textová zpráva o stavu)
*/

float ground_lat = 49.7950;
float ground_lon = 16.6800;

float current_lat = 49.7950;
float current_lon = 16.6786; 

float altitude = 0;
float vertical_speed = 0;
int phase = 0; // 0: Idle, 1: Ascent, 2: Descent

unsigned long programStart;
unsigned long phaseStart;
unsigned long lastUpdate;
unsigned long lastXMessage = 0;

void setup() {
  Serial.begin(115200);
  programStart = millis();
  phaseStart = programStart;
  lastUpdate = programStart;
  lastXMessage = programStart;
}

void loop() {
  unsigned long now = millis();
  float dt = (now - lastUpdate) / 1000.0;
  if (dt <= 0.001) dt = 0.001; 
  lastUpdate = now;

  float timeInPhase = (now - phaseStart) / 1000.0;

  // Logika fází (beze změny)
  if (phase == 0) {
    altitude = 0;
    vertical_speed = 0;
    if (timeInPhase > 20.0) {
      phase = 1;
      phaseStart = now;
    }
  } 
  else if (phase == 1) {
    float next_alt = 400 * timeInPhase - 20 * timeInPhase * timeInPhase;
    vertical_speed = (next_alt - altitude) / dt;
    altitude = next_alt;

    if (altitude > 1000 || vertical_speed <= 0) {
      altitude = 1000;
      phase = 2;
      phaseStart = now;
    }
    current_lon += 0.0000005;
  } 
  else if (phase == 2) {
    float turbulence = (random(-50, 50) / 100.0);
    vertical_speed = -4.0 + turbulence;
    altitude += vertical_speed * dt;
    
    if (altitude < 0) {
      altitude = 0;
      vertical_speed = 0;
    } else {
      current_lon += 0.000002; 
      current_lat += 0.0000005;
    }
  }

  // Atmosférické výpočty
  float temp = 25.0 - (altitude / 100.0) + (random(-10, 10) / 100.0);
  float hum = 45.0 + (altitude / 50.0) + (random(-20, 20) / 100.0);
  float press = 1013.25 * pow((1 - 0.0000225577 * altitude), 5.25588);
  int rssi = random(-110, -30);
  float snr = random(50, 120) / 10.0;

  // Základní proud dat
  Serial.print("M"); Serial.print(now);
  Serial.print(";A"); Serial.print(altitude, 2);
  Serial.print(";B"); Serial.print(temp, 2);
  Serial.print(";C"); Serial.print(hum, 1);
  Serial.print(";D"); Serial.print(press, 2);
  Serial.print(";E"); Serial.print(current_lat, 6);
  Serial.print(";F"); Serial.print(current_lon, 6);
  Serial.print(";V"); Serial.print(vertical_speed, 2);
  Serial.print(";R"); Serial.print(rssi);
  Serial.print(";S"); Serial.print(snr, 1);

  // Vložení zprávy X každých 50 sekund
  if (now - lastXMessage >= 50000) {
    Serial.print(";Xall things normal, time elapsed:");
    Serial.print(now);
    lastXMessage = now;
  }

  // Ukončení řádku
  Serial.println();

  delay(50); 
}