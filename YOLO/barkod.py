# barkod.py
from pyzbar.pyzbar import decode
import cv2

class BarcodeScanner:
    @staticmethod
    def scan(frame):
        """
        Gelen video karesinde (frame) barkod taraması yapar.
        İlk bulduğu barkodu string (metin) olarak döner, bulamazsa None döner.
        """
        try:
            # İşlem hızını artırmak için görüntüyü siyah-beyaz'a (gri tonlamaya) çeviriyoruz
            gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            detected_barcodes = decode(gray_frame)
            
            for barcode in detected_barcodes:
                if barcode.data:
                    # Okunan veri bayt formatındadır, bunu utf-8 string'e çeviriyoruz
                    barcode_text = barcode.data.decode('utf-8')
                    
                    # Opsiyonel: Ekranda okunan barkodun etrafına kutu çizmek istenirse
                    # (x, y, w, h) = barcode.rect
                    # cv2.rectangle(frame, (x, y), (x + w, y + h), (255, 0, 0), 2)
                    
                    return barcode_text
                    
            return None
        except Exception as e:
            print(f"Barkod okuma sisteminde hata oluştu: {e}")
            return None