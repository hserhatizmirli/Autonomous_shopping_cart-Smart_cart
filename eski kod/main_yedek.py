# main.py
import cv2
import time
import pandas as pd
import threading
import requests

# Modüllerimiz
from yolo import YoloAnalyzer
import barkod # Senin yazdığın barkod modülü
from tarti import ScaleReader

# --- DOSYA YOLLARI VE AYARLAR ---
DB_PATH = r"D:\AKILLI TARTI\mühendislik projesi\yolo_database.xlsx"
MODEL_PATH = r"D:\AKILLI TARTI\mühendislik projesi\runs\detect\yolo11\weights\best.pt"
COM_PORT = "COM6"
BAUDRATE = 115200

# Flask API Adresi (app.py açık olmalı)
API_URL = "http://127.0.0.1:5000/sepete_ekle"

class SmartScaleSystem:
    def __init__(self):
        self.state = "YOLO"  # "YOLO" veya "BARKOD"
        self.db = pd.DataFrame()
        
        # Anlık veriler
        self.current_detections = [] # YOLO'dan gelen top-3 listesi
        self.current_weight = None
        self.new_weight_flag = threading.Event()
        
        self.yolo_analyzer = YoloAnalyzer(MODEL_PATH)
        self.scale_reader = ScaleReader(COM_PORT, BAUDRATE, self.on_weight_stable)
        self.load_database()

    def load_database(self):
        try:
            self.db = pd.read_excel(DB_PATH)
            print(f"Veritabanı yüklendi. Toplam kayıt: {len(self.db)}")
        except Exception as e:
            print(f"Veritabanı yüklenemedi: {e}")

    def send_to_web_cart(self, product_name, price):
        """Ürünü app.py (Flask) sunucusuna gönderir."""
        try:
            payload = {"ad": product_name, "fiyat": float(price)}
            response = requests.post(API_URL, json=payload, timeout=2)
            if response.status_code == 200:
                print(f"[WEB BİLGİ] {product_name} sepete fırlatıldı!")
            else:
                print(f"[WEB HATA] Sunucu yanıtı: {response.status_code}")
        except Exception as e:
            print(f"[WEB HATA] Flask sunucusuna (app.py) ulaşılamadı! Sunucunun açık olduğundan emin ol.")

    def on_weight_stable(self, weight):
        if self.current_weight is None or abs(self.current_weight - weight) > 2.0:
            self.current_weight = weight
            print(f"\n[Sensör] Stabil Ağırlık Alındı: {weight} g")
            self.new_weight_flag.set()

    def check_weight_match(self, item_name, measured_weight):
        """Veritabanında ürün adı ve ağırlığı (±15g tolerans) eşleşiyor mu bakar."""
        matched = self.db[
            (self.db['product name'].str.lower() == str(item_name).lower()) & 
            (abs(self.db['weight'] - measured_weight) <= 15.0)
        ]
        if not matched.empty:
            return matched.iloc[0] # Eşleşen ürünün satırını döndür
        return None

    def logic_loop(self):
        while True:
            self.new_weight_flag.wait()
            self.new_weight_flag.clear() 
            
            if self.db.empty:
                continue

            # Senaryo 1: Teraziye yük bindi ama YOLO hiçbir şey görmüyor
            if not self.current_detections:
                print("[Hata] Teraziye yük kondu ancak kamera nesneyi tanıyamadı!")
                self.state = "BARKOD"
                continue

            en_iyi_tespit = self.current_detections[0]
            print(f"[Analiz] Tartı: {self.current_weight}g | En İyi Görsel: {en_iyi_tespit['name']} (%{en_iyi_tespit['conf']*100:.1f})")

            # Senaryo 2: YOLO çok emin (%70 ve üzeri)
            if en_iyi_tespit['conf'] >= 0.70:
                urun_satiri = self.check_weight_match(en_iyi_tespit['name'], self.current_weight)
                if urun_satiri is not None:
                    print(f"[%70 ÜZERİ KUSURSUZ EŞLEŞME] {urun_satiri['product name']} eklendi.")
                    self.send_to_web_cart(urun_satiri['product name'], urun_satiri['price'])
                else:
                    print("[Uyuşmazlık] YOLO %70 emin ama ağırlık tutmuyor!")
                    self.state = "BARKOD"
            
            # Senaryo 3: YOLO emin değil (%70 altı) veya karmaşa var. Top-3 Doğrulaması.
            else:
                print("[Karmaşa] %70 barajı aşılamadı, Top-3 gramaj doğrulaması yapılıyor...")
                eslesme_bulundu = False
                
                for tespit in self.current_detections:
                    urun_satiri = self.check_weight_match(tespit['name'], self.current_weight)
                    if urun_satiri is not None:
                        print(f"[TOP-3 DOĞRULAMA BAŞARILI] Tespit: {tespit['name']} ağırlığıyla doğrulandı!")
                        self.send_to_web_cart(urun_satiri['product name'], urun_satiri['price'])
                        eslesme_bulundu = True
                        break # Doğru ürünü bulduk, döngüden çık
                
                if not eslesme_bulundu:
                    print("[Uyuşmazlık] İlk 3 ürünün hiçbiri tartıdaki ağırlıkla uyuşmadı!")
                    self.state = "BARKOD"

    def run(self):
        self.scale_reader.start()
        threading.Thread(target=self.logic_loop, daemon=True).start()

        cap = cv2.VideoCapture(1, cv2.CAP_DSHOW)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

        print("\nSistem hazır! Çıkmak için 'q' tuşuna basın.\n" + "-"*50)

        try:
            while cap.isOpened():
                ret, frame = cap.read()
                if not ret: continue

                if self.state == "YOLO":
                    annotated_frame, detections = self.yolo_analyzer.process_frame(frame)
                    self.current_detections = detections 
                    
                    cv2.putText(annotated_frame, "MOD: YOLO", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                    cv2.imshow("Akilli Sistem", annotated_frame)

                elif self.state == "BARKOD":
                    cv2.rectangle(frame, (0, 0), (frame.shape[1], frame.shape[0]), (0, 0, 255), 10)
                    cv2.putText(frame, "LUTFEN BARKOD OKUTUN", (40, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
                    
                    # barkod.py içindeki pyzbar fonksiyonunu çağırıyoruz
                    import pyzbar.pyzbar as pyzbar
                    algilananlar = pyzbar.decode(frame)
                    
                    if algilananlar:
                        barkod_verisi = algilananlar[0].data.decode('utf-8')
                        print(f"\n[Barkod] Algılandı: {barkod_verisi}")
                        
                        if not self.db.empty:
                            matched = self.db[self.db['barcode'].astype(str) == str(barkod_verisi)]
                            if not matched.empty:
                                urun_satiri = matched.iloc[0]
                                print(f"[BARKOD EŞLEŞMESİ] {urun_satiri['product name']}")
                                self.send_to_web_cart(urun_satiri['product name'], urun_satiri['price'])
                            else:
                                print("[Hata] Okunan barkod veritabanında yok!")
                        
                        print("[Sistem] YOLO moduna geri dönülüyor...\n")
                        self.state = "YOLO"
                        time.sleep(1.5)
                        
                    cv2.imshow("Akilli Sistem", frame)

                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break

        except KeyboardInterrupt:
            pass
        finally:
            self.scale_reader.stop()
            cap.release()
            cv2.destroyAllWindows()

if __name__ == "__main__":
    system = SmartScaleSystem()
    system.run()