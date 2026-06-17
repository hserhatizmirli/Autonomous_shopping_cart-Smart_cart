#include "HX711.h"

// --- PİN TANIMLAMALARI ---
const int LOADCELL_DOUT_PIN = 26; // HX711 Veri hattı 
const int LOADCELL_SCK_PIN = 33;  // HX711 Saat hattı 
const int TARE_BUTTON_PIN = 14;   // Buton: Bir ucu GPIO 14, diğer ucu GND 

HX711 scale;

// İteratif testler sonucu optimize edilen kalibrasyon faktörü 
float calibration_factor = 412.5; 

void setup() {
  Serial.begin(115200);
  
  // HX711 Başlatma
  scale.begin(LOADCELL_DOUT_PIN, LOADCELL_SCK_PIN);
  
  // Dahili Pull-up direnci ile buton yapılandırması
  pinMode(TARE_BUTTON_PIN, INPUT_PULLUP);
  
  Serial.println("=======================================");
  Serial.println("    ESP32 AKILLI TARTI SİSTEMİ HAZIR    ");
  Serial.println("=======================================");
  
  scale.set_scale();
  scale.tare(); // Açılışta platformun boş ağırlığını sıfırla 
  Serial.println("Sistem sıfırlandı. Ölçüme başlayabilirsiniz.");
}

void loop() {
  // 1. FİZİKSEL DARA KONTROLÜ
  if (digitalRead(TARE_BUTTON_PIN) == LOW) {
    Serial.println(">> Buton Algılandı: Dara Alınıyor...");
    scale.tare(); 
    delay(500); // Mekanik sıçrama (Debounce) önleyici 
  }

  // 2. KALİBRASYON FAKTÖRÜNÜ UYGULA
  scale.set_scale(calibration_factor);

  // 3. SİNYAL İŞLEME VE FİLTRELEME
  // 5 ölçüm ortalaması alınarak gürültü bastırılır 
  float agirlik = scale.get_units(5);
  
  Serial.print("Ağırlık: ");
  Serial.print(agirlik, 2); 
  Serial.print(" g | CF: ");
  Serial.println(calibration_factor);

  // 4. DİNAMİK KALİBRASYON AYARI (Seri Port Terminali) 
  if(Serial.available()) {
    char temp = Serial.read();
    if(temp == '+' || temp == 'a') calibration_factor += 1.0;
    else if(temp == '-' || temp == 'z') calibration_factor -= 1.0;
  }
}
