import cv2
import os
from ultralytics import YOLO

def analyze_my_image_small():
    # Model yükleme
    model_path = 'D:/YOLO/runs/detect/yolo11/weights/best.pt'
    
    if not os.path.exists(model_path):
        print(f"[✗] Model bulunamadı, pretrained kullanılıyor...")
        model = YOLO('yolo11n.pt')
    else:
        model = YOLO(model_path)
    
    # Fotoğraf yolu
    image_path = r'D:\indir\WhatsApp Image 2026-04-25 at 11.41.35.jpeg'
    
    if not os.path.exists(image_path):
        print(f"[✗] Fotoğraf bulunamadı!")
        return
    
    # Fotoğrafı küçük boyutta oku
    image = cv2.imread(image_path)
    if image is None:
        print("[✗] Fotoğraf okunamadı!")
        return
    
    # Önce küçült, sonra analiz et (daha hızlı)
    small_image = cv2.resize(image, (640, 480))
    
    print("[✓] Fotoğraf analiz ediliyor (640x480)...")
    
    # Küçültülmüş görüntüde detection yap
    results = model(small_image, conf=0.70, iou=0.3)
    
    # Sonucu çiz
    annotated_image = results[0].plot()
    
    # Tespitleri yazdır
    if results[0].boxes is not None:
        print(f"\n{'='*40}")
        print(f"TESPİT EDİLEN NESNELER:")
        print(f"{'='*40}")
        for i, box in enumerate(results[0].boxes, 1):
            cls_id = int(box.cls[0])
            conf = float(box.conf[0])
            name = model.names[cls_id]
            print(f"{i}. {name}: %{conf*100:.1f}")
        print(f"{'='*40}\n")
    else:
        print("[!] Nesne tespit edilmedi!")
    
    # Göster
    cv2.imshow('Detection Result', annotated_image)
    print("\nÇıkmak için 'q' veya 'ESC'")
    print("Kaydetmek için 's'")
    
    while True:
        key = cv2.waitKey(0) & 0xFF
        if key == ord('q') or key == 27:  # q veya ESC
            break
        elif key == ord('s'):
            cv2.imwrite(r'D:\indir\detection_result.jpg', annotated_image)
            print("[✓] Kaydedildi: D:\\indir\\detection_result.jpg")
    
    cv2.destroyAllWindows()

if __name__ == '__main__':
    analyze_my_image_small()