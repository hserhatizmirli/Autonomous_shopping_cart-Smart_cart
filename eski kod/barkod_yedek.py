import cv2
from pyzbar.pyzbar import decode

class BarcodeScanner:
    @staticmethod
    def scan(frame):
        """
        main.py'dan gelen anlık kamera görüntüsünü (frame) analiz eder.
        Barkod bulunursa numarasını döner, bulunamazsa None döner.
        """
        # Görüntüdeki tüm barkodları tara ve çöz
        algilanan_barkodlar = decode(frame)

        for barkod in algilanan_barkodlar:
            # Barkod verisini string'e (yazıya) çeviriyoruz
            barkod_verisi = barkod.data.decode('utf-8')

            # Barkodun etrafına yeşil çerçeve çizelim
            (x, y, w, h) = barkod.rect
            cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
            
            # Okunan numarayı çerçevenin üstüne yazalım
            cv2.putText(frame, barkod_verisi, (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

            # Algılanan ilk barkod verisini doğrudan ana programa gönder
            return barkod_verisi
            
        # Eğer frame içinde hiç barkod bulunamadıysa None döner
        return None
