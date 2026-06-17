import cv2
from pyzbar.pyzbar import decode

def barkod_tara():
    # 0 numaralı (varsayılan) kamerayı başlat
    cap = cv2.VideoCapture(0)
    print("Barkod okuyucu aktif. Kameraya bir barkod gösterin...")
    print("Çıkmak için 'q' tuşuna basın.")

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        # Görüntüdeki tüm barkodları tara ve çöz
        algilanan_barkodlar = decode(frame)

        for barkod in algilanan_barkodlar:
            # Barkod verisi "byte" formatında gelir, onu normal string'e (yazıya) çeviriyoruz
            barkod_verisi = barkod.data.decode('utf-8')
            barkod_turu = barkod.type

            # Barkodun etrafına yeşil çerçeve çizelim
            (x, y, w, h) = barkod.rect
            cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
            
            # Okunan numarayı çerçevenin üstüne yazalım
            cv2.putText(frame, barkod_verisi, (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

            print(f"BARKOD YAKALANDI: Numarası: {barkod_verisi} - Türü: {barkod_turu}")
            


        # Kamerayı ekranda göster [cite: 156]
        cv2.imshow('Fail-Safe Barkod Okuyucu', frame)

        # 'q' tuşuna basılırsa kamerayı kapat ve çık [cite: 248]
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    # Kaynakları serbest bırak
    cap.release()
    cv2.destroyAllWindows()

# Sadece bu dosya çalıştırıldığında fonksiyonu çağır
if __name__ == "__main__":
    barkod_tara()