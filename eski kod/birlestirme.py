import threading
import time
import cv2
import pandas as pd
from ultralytics import YOLO
# Aynı klasördeki (D:\AKILLI TARTI\mühendislik projesi\) diğer kod dosyalarımızı çağırıyoruz
import yolo
import barkod
import tarti

# --- AYARLAR VE KÜRESEL DEĞİŞKENLER (DOSYA YOLLARI EKLENDİ) ---
# Windows yollarında hata almamak için tırnak işaretinden önce 'r' harfi koyuyoruz.
VERITABANI_YOLU = r"D:\AKILLI TARTI\mühendislik projesi\yolo_database.xlsx"
MODEL_YOLU = r"D:\AKILLI TARTI\mühendislik projesi\runs\detect\yolo11\weights\best.pt"
PORT = "COM6"
BAUDRATE = 115200

kamera_modu = "YOLO"  # "YOLO" veya "BARKOD"
son_tespit_edilen_nesne = None
son_olculen_agirlik = None
yeni_agirlik_verisi_var = False
sepet = []
df_db = None

# --- YARDIMCI FONKSİYONLAR ---
def veritabani_yukle():
    global df_db
    try:
        # Dosya uzantısı .xlsx olduğu için read_excel kullanıyoruz
        df_db = pd.read_excel(VERITABANI_YOLU)
        print(f" Veritabanı yüklendi: {VERITABANI_YOLU}")
    except Exception as e:
        print(f" Veritabanı hatası: {e}")
        df_db = pd.DataFrame()

def tarti_tetiklendi(agirlik):
    """tarti.py stabil ağırlık bulduğunda otomatik olarak bu fonksiyonu çağırır."""
    global son_olculen_agirlik, yeni_agirlik_verisi_var
    
    # Mükerrer okumayı engellemek için tolerans kontrolü
    if son_olculen_agirlik is None or abs(son_olculen_agirlik - agirlik) > 2.0:
        son_olculen_agirlik = agirlik
        yeni_agirlik_verisi_var = True
        print(f"\n[Tartı] Stabil Ağırlık Yakalandı: {son_olculen_agirlik:.2f} g")

def mantik_dongusu():
    """Arka planda YOLO ve Tartı verilerini eşleştiren beyin fonksiyonu."""
    global yeni_agirlik_verisi_var, kamera_modu
    
    while True:
        if yeni_agirlik_verisi_var:
            yeni_agirlik_verisi_var = False # İşleme başladık, bayrağı indir
            
            print(f"[Analiz] Tartı: {son_olculen_agirlik:.2f}g | Görsel: {son_tespit_edilen_nesne}")
            
            if not df_db.empty and son_tespit_edilen_nesne:
                # Eşleşme Kontrolü: İsim uyuyor mu ve ağırlık +- 15 gram tolerans içinde mi?
                eslesen = df_db[
                    (df_db['product name'].str.lower() == str(son_tespit_edilen_nesne).lower()) & 
                    (abs(df_db['weight'] - son_olculen_agirlik) <= 15.0)
                ]
                
                if not eslesen.empty:
                    urun_adi = eslesen.iloc[0]['product name']
                    fiyat = eslesen.iloc[0]['price']
                    
                    # Sepette var mı kontrolü
                    if urun_adi not in [item['ad'] for item in sepet]:
                        sepet.append({"ad": urun_adi, "fiyat": fiyat})
                        print(f" [Sepet] KUSURSUZ EŞLEŞME: {urun_adi} ({fiyat} TL)")
                    else:
                        print(f" [Sepet] {urun_adi} zaten sepette!")
                else:
                    print(" [Uyuşmazlık] YOLO ile ağırlık eşleşmedi! Kamera BARKOD moduna geçiyor...")
                    kamera_modu = "BARKOD"
            else:
                print(" [Uyuşmazlık] Teraziye yük kondu ama nesne tespit edilemedi! Kamera BARKOD moduna geçiyor...")
                kamera_modu = "BARKOD"
                
        time.sleep(0.1)

# --- ANA PROGRAM ---
if __name__ == "__main__":
    print("\n" + "="*50)
    print("MODÜLER AKILLI TARTI SİSTEMİ BAŞLATILIYOR")
    print("="*50)
    
    # 1. Veritabanını ve Modeli Yükle
    veritabani_yukle()
    model = YOLO(MODEL_YOLU)
    
    if model is None:
        exit()

    # 2. Arka Plan İşlemlerini Başlat (Tartı dinleme ve Mantık/Eşleştirme)
    t_tarti = threading.Thread(target=tarti.baslat, args=(PORT, BAUDRATE, tarti_tetiklendi), daemon=True)
    t_mantik = threading.Thread(target=mantik_dongusu, daemon=True)
    
    t_tarti.start()
    t_mantik.start()
    
    # 3. Kamerayı Başlat (Ana Thread - Ekran çizimi için ana işlemcide olması zorunludur)
    cap = cv2.VideoCapture(1, cv2.CAP_DSHOW)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    
    try:
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret: continue

            if kamera_modu == "YOLO":
                # Görüntüyü YOLO modülüne gönder, sonucu al
                annotated_frame, tespit = yolo.nesne_tespit_et(model, frame)
                if tespit:
                    son_tespit_edilen_nesne = tespit
                cv2.imshow("Akilli Tarti - Sistem Gorus", annotated_frame)

            elif kamera_modu == "BARKOD":
                # Ekrana uyarı yaz ve görüntüyü Barkod modülüne gönder
                cv2.putText(frame, "BARKOD MODU - Barkodu Gosterin", (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
                
                okunan_barkodlar = barkod.barkod_tara(frame)
                
                if okunan_barkodlar:
                    barkod_metni = okunan_barkodlar[0]
                    print(f"\n[Barkod] Algılandı: {barkod_metni}")
                    
                    if not df_db.empty:
                        eslesen = df_db[df_db['barcode'].astype(str) == str(barkod_metni)]
                        if not eslesen.empty:
                            urun_adi = eslesen.iloc[0]['product name']
                            fiyat = eslesen.iloc[0]['price']
                            if urun_adi not in [item['ad'] for item in sepet]:
                                sepet.append({"ad": urun_adi, "fiyat": fiyat})
                                print(f" [Sepet] Barkod ile eklendi: {urun_adi} ({fiyat} TL)")
                            else:
                                print(f" [Sepet] {urun_adi} zaten sepette var!")
                        else:
                            print(" [Hata] Barkod veritabanında yok!")
                    
                    # Barkod işi bitince YOLO'ya geri dön
                    print(" [Sistem] Yeniden YOLO moduna geçiliyor.\n")
                    kamera_modu = "YOLO"
                    time.sleep(1) # Kameraya nefes aldır
                
                cv2.imshow("Akilli Tarti - Sistem Gorus", frame)

            # 'q' tuşuna basılarak çıkış
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

    except KeyboardInterrupt:
        pass
    
    # Kapanış Ekranı Fiş Yazdırma
    cap.release()
    cv2.destroyAllWindows()
    
    print("\n" + "="*30)
    print("SİSTEM KAPATILDI. FİŞ ÖZETİ:")
    toplam = 0
    for i, urun in enumerate(sepet, 1):
        print(f"{i}. {urun['ad']} - {urun['fiyat']} TL")
        toplam += urun['fiyat']
    print("-" * 30)
    print(f"TOPLAM TUTAR: {toplam} TL")
    print("="*30)