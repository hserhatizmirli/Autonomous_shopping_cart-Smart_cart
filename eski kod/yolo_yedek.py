# yolo.py
from ultralytics import YOLO

class YoloAnalyzer:
    def __init__(self, model_path):
        """YOLO modelini başlatır ve belleğe yükler."""
        try:
            self.model = YOLO(model_path)
            print(f"YOLO Modeli başarıyla yüklendi: {model_path}")
        except Exception as e:
            print(f"Model yükleme hatası: {e}")
            self.model = None

    def process_frame(self, frame):
        """
        Kareyi analiz eder ve en yüksek güvene sahip İLK 3 tespiti döndürür.
        """
        if self.model is None:
            return frame, []

        results = self.model.track(frame, persist=True, verbose=False)
        
        detections = []

        if results and len(results[0].boxes) > 0:
            for box in results[0].boxes:
                conf = float(box.conf[0])
                # Çok düşük (çöp) verileri elemek için min 0.20 sınırı koyuyoruz
                if conf >= 0.20: 
                    cls_id = int(box.cls[0])
                    name = self.model.names[cls_id]
                    detections.append({"name": name, "conf": conf})

        # Güven skoruna göre büyükten küçüğe sırala ve ilk 3'ü al
        detections = sorted(detections, key=lambda x: x["conf"], reverse=True)[:3]

        # Modelin kendi çizdiği etiketli kareyi al
        annotated_frame = results[0].plot()

        return annotated_frame, detections