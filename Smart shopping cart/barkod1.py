import cv2
from pyzbar.pyzbar import decode

def barkod_oku(frame):
    """
    Ana koddan (main) gelen kareyi alır, içindeki barkodları çözer.
    Bulunan barkodları ve yeşil çerçeve çizilmiş kareyi geri döndürür.
    """
    algilanan_barkodlar = decode(frame)
    bulunan_barkodlar = []

    for barkod in algilanan_barkodlar:
        # Barkod verisi "byte" formatında gelir, onu normal string'e (yazıya) çeviriyoruz
        barkod_verisi = barkod.data.decode('utf-8')
        
        # Barkodun etrafına yeşil çerçeve çizelim
        (x, y, w, h) = barkod.rect
        cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
        
        # Okunan numarayı çerçevenin üstüne yazalım
        cv2.putText(frame, barkod_verisi, (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        
        # Bulunan veriyi listeye ekle
        bulunan_barkodlar.append(barkod_verisi)

    return frame, bulunan_barkodlar