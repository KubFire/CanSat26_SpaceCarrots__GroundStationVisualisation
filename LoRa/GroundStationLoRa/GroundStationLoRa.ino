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

void setup() {
  Serial.begin(115200);
  
  // Čekání na inicializaci USB Serialu u RP2350
  unsigned long startWait = millis();
  while (!Serial && millis() - startWait < 3000);

  Serial.println("--- RP2350 LoRa Ground Station Receiver ---");

  // Inicializace SPI na RP2350
  SPI.setRX(MISO_PIN);
  SPI.setTX(MOSI_PIN);
  SPI.setSCK(SCK_PIN);
  SPI.begin();

  // Nastavení pinů pro LoRa knihovnu
  LoRa.setPins(CS_PIN, RESET_PIN, IRQ_PIN);

  // Inicializace na 433 MHz
  if (!LoRa.begin(433E6)) {
    Serial.println("Starting LoRa failed! Check wiring/pins.");
    while (1);
  }

  // --- Identický setup jako u satelitu ---
  LoRa.setSpreadingFactor(7);           
  LoRa.setSignalBandwidth(125E3);       
  LoRa.setCodingRate4(5);               
  LoRa.setSyncWord(0xBB);               
  LoRa.setGain(6);                      // Max citlivost pro pozemní stanici
  LoRa.enableCrc();                     
  
  Serial.println("RP2350 GS Ready. Listening on 433MHz...");
}

void loop() {
  // Kontrola příchozích balíčků
  int packetSize = LoRa.parsePacket();
  
  if (packetSize) {
    String incoming = "";
    
    // Čtení dat z LoRa bufferu
    while (LoRa.available()) {
      incoming += (char)LoRa.read();
    }

    // Výpis do sériového portu ve tvém formátu
    // Příklad: M12345;A100.00;B22.50;C40.0;D1011.00;E49.795000;F16.680000;V0.00;R-85;S10.5
    Serial.print(incoming);
    
    // Přidání RSSI (R) a SNR (S) měřených přijímačem
    Serial.print(";R"); 
    Serial.print(LoRa.packetRssi());
    Serial.print(";S"); 
    Serial.println(LoRa.packetSnr());
    
    // Na RP2350 není potřeba delay, chceme co nejrychlejší odezvu
  }
}