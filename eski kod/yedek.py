import cv2
import os
from ultralytics import YOLO
from multiprocessing import freeze_support
import time
from collections import defaultdict

class SmartProductDetector:
    def __init__(self, model, confidence_threshold=0.85, cooldown_seconds=3):
        self.model = model  # model'i sınıfa ekledim
        self.confidence_threshold = confidence_threshold  # %85 eşik
        self.cooldown_seconds = cooldown_seconds  # Ürün eklendikten sonra bekleme süresi
        self.last_added_product = None
        self.last_added_time = 0
        self.product_in_view = {}  # Hangi ürünün şu anda görüş alanında olduğu
        self.product_last_seen = {}  # Ürünün en son ne zaman görüldüğü
        
    def process_detections(self, detections, current_time):
        """
        Tespitleri işler ve sadece en yüksek güvenli ürünü döndürür
        """
        if detections is None or len(detections) == 0:
            # Hiç ürün yoksa, tüm ürünleri görüşten kaldır
            self.product_in_view.clear()
            return None, None
        
        # Tüm tespitleri topla ve en yüksek güvenli bul
        best_detection = None
        best_confidence = 0
        all_detections = []
        
        for box in detections:
            conf = float(box.conf[0])
            cls_id = int(box.cls[0])
            name = self.model.names[cls_id]  # self.model kullan
            all_detections.append((name, conf))
            
            if conf > best_confidence:
                best_confidence = conf
                best_detection = name
        
        # Şu an görülen ürünleri güncelle
        current_products = set([d[0] for d in all_detections])
        for product in current_products:
            self.product_in_view[product] = current_time
            self.product_last_seen[product] = current_time
        
        # Eski ürünleri temizle (2 saniyeden fazla görülmeyen)
        to_remove = []
        for product, last_time in self.product_in_view.items():
            if current_time - last_time > 2:
                to_remove.append(product)
        for product in to_remove:
            del self.product_in_view[product]
            print(f"[i] Ürün görüşten kayboldu: {product}")
        
        # Debug: Şu anki tespitleri göster (opsiyonel)
        if all_detections and best_confidence >= 0.70:
            print(f"[DEBUG] En iyi: {best_detection} ({best_confidence:.2f})")
        
        # Güven eşiğini kontrol et
        if best_detection and best_confidence >= self.confidence_threshold:
            # Cooldown kontrolü (aynı ürün hemen tekrar eklenmesin)
            if (best_detection != self.last_added_product or 
                current_time - self.last_added_time > self.cooldown_seconds):
                
                # Ürün hala görüş alanında mı kontrol et
                if best_detection in self.product_in_view:
                    self.last_added_product = best_detection
                    self.last_added_time = current_time
                    return best_detection, best_confidence
        
        return None, None

def kamera():
    best_pt = 'D:/YOLO/runs/detect/yolo11/weights/best.pt'
    
    if not os.path.exists(best_pt):
        print("[✗] Eğitilmiş model bulunamadı!")
        return
    
    model = YOLO(best_pt)
    print(f"[✓] Model yüklendi: {model.names}")
    
    cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    
    if not cap.isOpened():
        print("[✗] Kamera açılamadı!")
        return
    
    # Detector'ü başlat - model'i parametre olarak gönder
    detector = SmartProductDetector(model, confidence_threshold=0.85, cooldown_seconds=3)
    
    print("[✓] Kamera çalışıyor. Çıkmak için 'q'")
    print("[✓] AYARLAR:")
    print("    - Güven eşiği: %85 ve üzeri")
    print("    - Aynı ürün için bekleme: 3 saniye")
    print("    - Sadece EN YÜKSEK güvenli tespit sepete eklenir")
    print("    - Ürün görüşten kaybolana kadar beklenir")
    
    sepet = []
    frame_counter = 0
    processed_products = set()  # Daha önce eklenen ürünleri hatırla
    
    while True:
        ret, frame = cap.read()
        if not ret:
            continue
        
        current_time = time.time()
        frame_counter += 1
        
        # Her 3 frame'de bir işlem yap (performans için)
        if frame_counter % 3 == 0:
            results = model.track(
                frame, 
                persist=True, 
                conf=0.50,  # Tespit için düşük eşik, biz zaten filtreleyeceğiz
                iou=0.5,
                tracker="bytetrack.yaml",
                verbose=False
            ) 
            
            # Sadece en yüksek güvenli ürünü al
            product, confidence = detector.process_detections(results[0].boxes, current_time)
            
            if product and product not in processed_products:
                # Yeni ürün sepete eklendi
                print(f"\n{'='*50}")
                print(f"[✓✓✓] SEPETE EKLENDİ: {product} (Güven: {confidence:.2f})")
                print(f"{'='*50}\n")
                sepet.append(product)
                processed_products.add(product)
                
                # Ekrana bildirim yaz
                cv2.putText(frame, f"EKLENDI: {product}", (10, 90), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
            
            # Anlık en iyi tespiti ekranda göster (debug için)
            if results[0].boxes is not None and len(results[0].boxes) > 0:
                best_conf = 0
                best_name = ""
                for box in results[0].boxes:
                    conf = float(box.conf[0])
                    if conf > best_conf:
                        best_conf = conf
                        cls_id = int(box.cls[0])
                        best_name = model.names[cls_id]
                
                if best_name:
                    color = (0, 255, 0) if best_conf >= 0.85 else (0, 255, 255)
                    cv2.putText(frame, f"Tespit: {best_name} ({best_conf:.2f})", (10, 30), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
        
        # Sepet özetini göster
        y_offset = frame.shape[0] - 80
        cv2.putText(frame, f"SEPET ({len(sepet)} urun)", (10, y_offset), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        
        for i, urun in enumerate(sepet[-5:]):  # Son 5 ürün
            cv2.putText(frame, f"{i+1}. {urun}", (10, y_offset + 25 + (i * 25)), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        
        # Son eklenen ürünü vurgula
        if sepet:
            cv2.putText(frame, f"Son: {sepet[-1]}", (frame.shape[1] - 200, 30), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
        
        annotated_frame = results[0].plot() if frame_counter % 3 == 0 else frame
        cv2.imshow('Akilli Sepet - YOLO', annotated_frame)
        
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            break
        elif key == ord('s'):
            print("\n" + "="*50)
            print("SEPET OZETI")
            print("="*50)
            for i, urun in enumerate(sepet, 1):
                print(f"{i}. {urun}")
            print(f"\nToplam: {len(sepet)} urun")
            print("="*50)
        elif key == ord('r'):
            # Sepeti sıfırla
            sepet.clear()
            processed_products.clear()
            detector.last_added_product = None
            print("\n[!] SEPET SIFIRLANDI!")
    
    # Program sonu
    print("\n" + "="*50)
    print("FINAL SEPET RAPORU")
    print("="*50)
    for i, urun in enumerate(sepet, 1):
        print(f"{i}. {urun}")
    print(f"\nToplam {len(sepet)} urun alindi.")
    
    cap.release()
    cv2.destroyAllWindows()

if __name__ == '__main__':
    freeze_support()
    kamera()