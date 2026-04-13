#include <SPI.h>
#include <LoRa.h>

// --- KONFIGURACE PINŮ PRO TVOJE PCB (RP2350) ---
// Uprav podle svého schématu:
const int SCK_PIN   = 18; 
const int MOSI_PIN  = 19;
const int MISO_PIN  = 16;
const int CS_PIN    = 17; // NSS
const int RESET_PIN = 20; // RST
const int IRQ_PIN   = 21; // DIO0

// Globální konstanty
float altitude = 120.50;
float temperature = 22.35;
float humidity = 40.2;
float pressure = 1011.15;
float latitude = 49.795000;
float longitude = 16.680000;
float vertical_speed = 0.00;

void setup() {
  Serial.begin(115200);
  // U RP2350 může Serial chvíli trvat, než se probere
  unsigned long startWait = millis();
  while (!Serial && millis() - startWait < 3000);

  Serial.println("--- RP2350 LoRa Satellite Transmitter ---");

  // Inicializace SPI na RP2350
  SPI.setRX(MISO_PIN);
  SPI.setTX(MOSI_PIN);
  SPI.setSCK(SCK_PIN);
  SPI.begin();

  // Nastavení pinů pro LoRa knihovnu
  LoRa.setPins(CS_PIN, RESET_PIN, IRQ_PIN);

  // Inicializace na 433 MHz
  if (!LoRa.begin(433E6)) {
    Serial.println("Starting LoRa failed! Check RP2350 SPI pins.");
    while (1);
  }

  // Pimpnutý setup (shodný s receiverem)
  LoRa.setSpreadingFactor(7);
  LoRa.setSignalBandwidth(125E3);
  LoRa.setCodingRate4(5);
  LoRa.setSyncWord(0xBB);
  LoRa.setTxPower(20); 
  LoRa.enableCrc();

  Serial.println("LoRa TX Ready on RP2350.");
}

void loop() {
  unsigned long now = millis();

  // Odeslání balíčku ve tvém kódování
  LoRa.beginPacket();
  
  LoRa.print("M"); LoRa.print(now);
  LoRa.print(";A"); LoRa.print(altitude, 2);
  LoRa.print(";B"); LoRa.print(temperature, 2);
  LoRa.print(";C"); LoRa.print(humidity, 1);
  LoRa.print(";D"); LoRa.print(pressure, 2);
  LoRa.print(";E"); LoRa.print(latitude, 6);
  LoRa.print(";F"); LoRa.print(longitude, 6);
  LoRa.print(";V"); LoRa.print(vertical_speed, 2);
  
  LoRa.endPacket();

  Serial.print("Data sent: M");
  Serial.println(now);

  delay(50);
}