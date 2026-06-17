# main.py
import cv2
import time
import pandas as pd
import threading

# Geliştirdiğimiz modülleri içe aktarıyoruz
from yolo import YoloAnalyzer
from barkod import BarcodeScanner
from tarti import ScaleReader

# --- DOSYA YOLLARI VE AYARLAR ---
DB_PATH = r"D:\AKILLI TARTI\mühendislik projesi\yolo_database.xlsx"
MODEL_PATH = r"D:\AKILLI TARTI\mühendislik projesi\runs\detect\yolo11\weights\best.pt"
COM_PORT = "COM6"
BAUDRATE = 115200

class SmartScaleSystem:
    def __init__(self):
        # Durum Değişkenleri (State Machine)
        self.state = "YOLO"  # "YOLO" veya "BARKOD"
        self.cart = []
        self.db = pd.DataFrame()
        
        # Anlık veriler
        self.current_visual_detection = None
        self.current_weight = None
        self.new_weight_flag = threading.Event() # Asenkron tetikleyici bayrak
        
        # Modül Nesneleri
        self.yolo_analyzer = YoloAnalyzer(MODEL_PATH)
        self.scale_reader = ScaleReader(COM_PORT, BAUDRATE, self.on_weight_stable)
        
        self.load_database()

    def load_database(self):
        """Ürün Excel veritabanını Pandas ile belleğe alır."""
        try:
            self.db = pd.read_excel(DB_PATH)
            print(f"Veritabanı yüklendi. Toplam kayıt: {len(self.db)}")
        except Exception as e:
            print(f"Veritabanı yüklenemedi: {e}")

    def on_weight_stable(self, weight):
        """tarti.py tarafından stabil bir ağırlık bulunduğunda çağrılan Callback fonksiyonu."""
        # Eğer okunan ağırlık son okunan ile aynıysa (2 gram toleransla) tekrar işleme alma
        if self.current_weight is None or abs(self.current_weight - weight) > 2.0:
            self.current_weight = weight
            print(f"\n[Sensör] Stabil Ağırlık Alındı: {weight} g")
            # Karar mekanizmasını uyandır
            self.new_weight_flag.set()

    def logic_loop(self):
        """
        Karar mekanizması. Tartı ve YOLO verilerini veritabanıyla kıyaslar.
        Kamera (main) thread'ini dondurmamak için arka planda asenkron çalışır.
        """
        while True:
            # Yeni bir stabil ağırlık gelene kadar bekle (CPU dostu)
            self.new_weight_flag.wait()
            self.new_weight_flag.clear() 
            
            if self.db.empty:
                print("Veritabanı boş, doğrulama yapılamıyor.")
                continue

            print(f"[Analiz] Okunan Ağırlık: {self.current_weight}g | Görsel Tahmin: {self.current_visual_detection}")

            # 1. Senaryo: YOLO bir şey gördü mü?
            if self.current_visual_detection:
                # DB'de ismi eşleşen ve ağırlığı +-15g toleransında olan ürünü bul
                matched_product = self.db[
                    (self.db['product name'].str.lower() == str(self.current_visual_detection).lower()) & 
                    (abs(self.db['weight'] - self.current_weight) <= 15.0)
                ]
                
                # Kusursuz Eşleşme
                if not matched_product.empty:
                    self.add_to_cart(matched_product.iloc[0])
                else:
                    print("[Uyuşmazlık] YOLO tespiti ile ölçülen ağırlık örtüşmüyor!")
                    self.trigger_barcode_mode()
            
            # 2. Senaryo: Teraziye yük bindi ama YOLO hiçbir şey göremedi
            else:
                print("[Hata] Teraziye yük kondu ancak kamera nesneyi tanıyamadı!")
                self.trigger_barcode_mode()

    def add_to_cart(self, product_row, via_barcode=False):
        """Ürünü sepete ekler (Mükerrer eklemeyi engeller)"""
        product_name = product_row['product name']
        price = product_row['price']
        
        # Sepette var mı kontrolü
        if not any(item['name'] == product_name for item in self.cart):
            self.cart.append({"name": product_name, "price": price})
            method = "BARKOD" if via_barcode else "KUSURSUZ EŞLEŞME"
            print(f"[SEPETE EKLENDİ - {method}] {product_name} - {price} TL")
        else:
            print(f"[Uyarı] '{product_name}' zaten sepette bulunuyor, tekrar eklenmedi.")

    def trigger_barcode_mode(self):
        """Sistemi yedek güvenlik moduna (Barkod) geçirir."""
        print("[Durum Değişimi] BARKOD MODUNA GEÇİLİYOR. Lütfen ürünün barkodunu okutun.")
        self.state = "BARKOD"

    def run(self):
        """Ana döngü: Kameraları okur, ekrana çizer ve sistemi koordine eder."""
        # Tartı dinleme işlemlerini başlat
        self.scale_reader.start()
        
        # Karar mekanizmasını (Logic) ayrı bir thread olarak başlat
        logic_thread = threading.Thread(target=self.logic_loop, daemon=True)
        logic_thread.start()

        cap = cv2.VideoCapture(1, cv2.CAP_DSHOW) # USB kamera için 1, laptop kamerası için 0.
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

        print("\nSistem hazır! Çıkmak ve fiş yazdırmak için 'q' tuşuna basın.\n" + "-"*50)

        try:
            while cap.isOpened():
                ret, frame = cap.read()
                if not ret: continue

                # YOLO DURUMU (Varsayılan)
                if self.state == "YOLO":
                    annotated_frame, detection = self.yolo_analyzer.process_frame(frame)
                    # Karar mekanizmasının görebilmesi için son tespiti güncelle
                    self.current_visual_detection = detection
                    
                    # Arayüz Bilgileri
                    cv2.putText(annotated_frame, "MOD: YOLO AKTIF", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                    cv2.putText(annotated_frame, f"Sepet: {len(self.cart)} Urun", (10, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
                    
                    cv2.imshow("Gorsel Zeka & Agirlik Dogrulama", annotated_frame)

                # BARKOD DURUMU (Uyuşmazlık anında)
                elif self.state == "BARKOD":
                    # Görsel uyarı
                    cv2.rectangle(frame, (0, 0), (frame.shape[1], frame.shape[0]), (0, 0, 255), 10)
                    cv2.putText(frame, "UYUSMAZLIK! LUTFEN BARKOD OKUTUN", (40, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
                    
                    barcode_data = BarcodeScanner.scan(frame)
                    
                    if barcode_data:
                        print(f"\n[Barkod Okuyucu] Barkod tespit edildi: {barcode_data}")
                        if not self.db.empty:
                            matched = self.db[self.db['barcode'].astype(str) == str(barcode_data)]
                            
                            if not matched.empty:
                                self.add_to_cart(matched.iloc[0], via_barcode=True)
                            else:
                                print(f"[Hata] Okunan barkod ({barcode_data}) veritabanında bulunamadı!")
                        
                        # Okuma başarılı veya başarısız olsa da süreci tamamlayıp YOLO'ya dönüyoruz
                        print("[Durum Değişimi] YENİDEN YOLO MODUNA GEÇİLİYOR.\n")
                        self.state = "YOLO"
                        time.sleep(1.5) # Mod geçişinde kameraya nefes aldır ve sürekli okumayı engelle
                        
                    cv2.imshow("Gorsel Zeka & Agirlik Dogrulama", frame)

                # Çıkış Komutu
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break

        except KeyboardInterrupt:
            pass
        finally:
            self.scale_reader.stop()
            cap.release()
            cv2.destroyAllWindows()
            self.print_receipt()

    def print_receipt(self):
        """Kapanışta fiş özetini yazdırır."""
        print("\n" + "="*40)
        print("          KASA FİŞİ ÖZETİ")
        print("="*40)
        total = 0
        if not self.cart:
            print("Sepet boş.")
        else:
            for idx, item in enumerate(self.cart, 1):
                print(f"{idx}. {item['name'].ljust(25)} {item['price']} TL")
                total += float(item['price'])
        print("-" * 40)
        print(f"TOPLAM TUTAR:".ljust(28) + f"{total} TL")
        print("="*40 + "\n")

if __name__ == "__main__":
    system = SmartScaleSystem()
    system.run()