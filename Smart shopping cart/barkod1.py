import cv2
from pyzbar.pyzbar import decode

def barkod_oku(frame):
    
    # Ana koddan (main) gelen kareyi alır, içindeki barkodları çözer. / It takes the square file from the main code and decodes the barcodes inside it.
    # Bulunan barkodları ve yeşil çerçeve çizilmiş kareyi geri döndürür. / Returns the found barcodes and the square with the green frame drawn on it.
    
    algilanan_barkodlar = decode(frame)
    bulunan_barkodlar = []

    for barkod in algilanan_barkodlar:
        # Barkod verisi "byte" formatında gelir, onu normal string'e (yazıya) çeviriyoruz / The barcode data comes in "byte" format, we convert it to a normal string (text)
        barkod_verisi = barkod.data.decode('utf-8')
        
        # Barkodun etrafına yeşil çerçeve çizer / Draws a green frame around the barcode
        (x, y, w, h) = barkod.rect
        cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
        
        # Okunan numarayı çerçevenin üstüne yazar / Writes the read number on top of the frame
        cv2.putText(frame, barkod_verisi, (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        
        # Bulunan veriyi listeye ekle / Add the found data to the list  
        bulunan_barkodlar.append(barkod_verisi)

    return frame, bulunan_barkodlar