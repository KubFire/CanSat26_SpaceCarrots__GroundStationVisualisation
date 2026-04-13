#include <SPI.h>
#include <LoRa.h>

const int csPin = 15;    // D8
const int resetPin = 16; // D0
const int irqPin = 4;    // D2

void setup() {
  Serial.begin(115200);
  while (!Serial);

  LoRa.setPins(csPin, resetPin, irqPin);

  // Inicializace na 433 MHz
  if (!LoRa.begin(433E6)) {
    Serial.println("Starting LoRa failed!");
    while (1);
  }

  // Finální "Rocket Mode" nastavení
  LoRa.setSpreadingFactor(7);           // Rychlost a kadence
  LoRa.setSignalBandwidth(125E3);       // Citlivost
  LoRa.setCodingRate4(5);               // FEC
  LoRa.setSyncWord(0xBB);               // Soukromá síť
  LoRa.setGain(6);                      // Max zesílení přijímače
  LoRa.enableCrc();                     // Validace dat
  
  Serial.println("LoRa 433MHz Receiver Ready.");
}

void loop() {
  int packetSize = LoRa.parsePacket();
  if (packetSize) {
    String incoming = "";
    while (LoRa.available()) {
      incoming += (char)LoRa.read();
    }
    
    // Výpis do Serialu pro tvůj sensor_map
    Serial.print(incoming);
    Serial.print(";R"); Serial.print(LoRa.packetRssi());
    Serial.print(";S"); Serial.println(LoRa.packetSnr());
  }
}