import cv2
import os
from ultralytics import YOLO
from multiprocessing import freeze_support

def model_train(model):
    model.train(
        data="D:/git/Kasiyersiz-Ak-ll-Al-veri-Sepeti/YOLO/Dataset/data.yaml",
        epochs=250,
        name='yolo11',
        project='D:/git/Kasiyersiz-Ak-ll-Al-veri-Sepeti/YOLO/runs/detect/', 
        exist_ok=True,  
        batch=8,
        workers=0,
        device=0, 
        amp=False 
    )

def kamera():
    best_pt = 'D:/git/Kasiyersiz-Ak-ll-Al-veri-Sepeti/YOLO/runs/detect/yolo11/weights/best.pt'
    
    if not os.path.exists(best_pt):
        print("Eğitilmiş model bulunamadı!")
        return
    
    model = YOLO(best_pt)
    print(f"Model yüklendi: {model.names}")
    
    cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)   
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    
    if not cap.isOpened():
        print(" Kamera açılamadı!")
        return

    print("Kamera çalışıyor. Çıkmak için 'q'")
    print("Ayarlar: conf=0.85, iou=0.3 (hassasiyet artırıldı)")
    
    while True:
        ret, frame = cap.read()
        if not ret:
            continue

        results = model.track(
            frame, 
            persist=True, 
            conf=0.70,      # Sadece %60'ten emin olduklarını göster
            iou=0.3,        # Çakışma eşiğini düşür (aynı nesneye 2 label gelmesini engeller)
            tracker="bytetrack.yaml",
            verbose=False
        ) 
        
        annotated_frame = results[0].plot()
        cv2.imshow('YOLO Takip', annotated_frame)
        
        # Tespitleri yazdır (debug için)
        if results[0].boxes is not None:
            for box in results[0].boxes:
                cls_id = int(box.cls[0])
                conf = float(box.conf[0])
                name = model.names[cls_id]
                print(f"Tespit: {name} - Güven: {conf:.2f}")
        
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == '__main__':
    freeze_support()
    model = YOLO('D:/git/Kasiyersiz-Ak-ll-Al-veri-Sepeti/YOLO/runs/detect/yolo11/weights/best.pt')
    model_train(model)
    #kamera()