# yolo.py
from ultralytics import YOLO
import cv2

class YoloAnalyzer:
    def __init__(self, model_path, confidence_threshold=0.60):
        """
        YOLO modelini başlatır ve belleğe yükler.
        """
        self.confidence_threshold = confidence_threshold
        try:
            self.model = YOLO(model_path)
            print(f"YOLO Modeli başarıyla yüklendi: {model_path}")
        except Exception as e:
            print(f"Model yükleme hatası: {e}")
            self.model = None

    def process_frame(self, frame):
        """
        Gelen video karesini analiz eder, en yüksek güvenli nesneyi bulur ve 
        çizilmiş (annotated) kare ile birlikte döner.
        """
        if self.model is None:
            return frame, None

        # Frame'i modele gönder, persist=True ile takip özelliğini kullan
        results = self.model.track(frame, persist=True, verbose=False)
        
        best_detection = None
        best_confidence = 0.0

        if results and len(results[0].boxes) > 0:
            for box in results[0].boxes:
                conf = float(box.conf[0])
                if conf > best_confidence and conf >= self.confidence_threshold:
                    best_confidence = conf
                    cls_id = int(box.cls[0])
                    best_detection = self.model.names[cls_id]

        # Modelin kendi çizdiği etiketli kareyi al
        annotated_frame = results[0].plot()

        return annotated_frame, best_detection