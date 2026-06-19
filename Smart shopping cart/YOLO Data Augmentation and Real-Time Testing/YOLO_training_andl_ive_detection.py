import cv2
import os
from ultralytics import YOLO
from multiprocessing import freeze_support

def model_train(model):
    model.train(
        data=r'/Smart shopping cart/Dataset/data.yaml', # Veri seti dosyasının yolu (hata alırsanız tam yolu gireiblirsiniz.) / The path to the dataset file (if you get an error, you can enter the full path.)
        epochs=250,
        name='yolo11',
        project=r'/Smart shopping cart/runs/detect/', # Modelin kaydedileceği klasör (hata alırsanız tam yolu gireiblirsiniz.) / The folder where the model will be saved (if you get an error, you can enter the full path.)
        exist_ok=True,  
        batch=8,
        workers=0,
        device=0, 
        amp=False 
    )

def kamera():
    best_pt = r'/Smart shopping cart/YOLO/runs/detect/yolo11/weights/best.pt' # Eğitilmiş modelin yolu (hata alırsanız tam yolu gireiblirsiniz.) / The path to the trained model (if you get an error, you can enter the full path.)
    
    if not os.path.exists(best_pt):
        print("Eğitilmiş model bulunamadı!")
        return
    
    model = YOLO(best_pt)
    print(f"Model yüklendi: {model.names}")
    
    cap = cv2.VideoCapture(1, cv2.CAP_DSHOW)
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
            conf=0.70,      # Sadece %70'ten emin olduklarını göster / Only show detections with confidence >= 70%
            iou=0.3,        # Çakışma eşiğini düşür (aynı nesneye 2 label gelmesini engeller) / Lower the IoU threshold to avoid multiple labels for the same object
            tracker="bytetrack.yaml",
            verbose=False
        ) 
        
        annotated_frame = results[1].plot()
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
    # 
    model = YOLO(r'/Smart shopping cart/YOLO/runs/detect/yolo11/weights/best.pt') 
    # sadece birini kullanmak için yorum satırlarını açıp kapatabilirsiniz / Uncomment one of the following lines to use either training or camera
    model_train(model)  # Eğitimi başlat / Start training 
    kamera() # Kamerayı başlat / Start the camera