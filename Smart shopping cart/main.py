import cv2
import time
import threading
import json
import random
from multiprocessing import freeze_support
from flask import Flask, render_template, request, jsonify, Response
import iyzipay

# Kendi kodlarımızın modülleri / Our own code modules
from yolo import YoloAnalyzer  
from tarti import ScaleReader
from barkod1 import barkod_oku

# =================================================================
# 1. VERİTABANLARI VE AYARLAR / DATABASES AND SETTINGS
# =================================================================

DATABASE = {
    "kizilay_maden_suyu": 339.0, "beypazari_maden_suyu": 339.0, "60_sayfa_gipta_defter": 250.5,
    "80_sayfa_gipta_defter": 322.0, "cafex_kahve": 19.0, "mahmood_kahve": 19.0,
    "nazar_naneli_sakiz": 9.0, "nazar_damla_sakizli_sakiz": 8.0, "eti_hosbes_gofret": 31.0,
    "centro_gofret": 36.5, "torku_nobir_gofret": 35.0, "citkirildim_cubuk_kraker": 152.0,
    "eti_crax_cubuk_kraker": 92.0, "ulker_cokoprens_biskuvi": 81.0, "susse_biskuvi": 101.0,
    "pensan_mavi_tukenmez_kalem": 7.0, "pensan_siyah_tukenmez_kalem": 7.0
}

PRICE_DATABASE = {
    "kizilay_maden_suyu": 11.0, "beypazari_maden_suyu": 11.0, "60_sayfa_gipta_defter": 25.0,
    "80_sayfa_gipta_defter": 35.0, "cafex_kahve": 4.5, "mahmood_kahve": 6.75,
    "nazar_naneli_sakiz": 10.0, "nazar_damla_sakizli_sakiz": 10.0, "eti_hosbes_gofret": 15.0,
    "centro_gofret": 9.0, "torku_nobir_gofret": 15.75, "citkirildim_cubuk_kraker": 15.0,
    "eti_crax_cubuk_kraker": 14.5, "ulker_cokoprens_biskuvi": 10.0, "susse_biskuvi": 16.5,
    "pensan_mavi_tukenmez_kalem": 10.0, "pensan_siyah_tukenmez_kalem": 10.0
}

DISPLAY_NAMES = {
    "kizilay_maden_suyu": "Kızılay Maden Suyu", "beypazari_maden_suyu": "Beypazarı Maden Suyu",
    "60_sayfa_gipta_defter": "Gıpta Defter 60 Syf", "80_sayfa_gipta_defter": "Gıpta Defter 80 Syf",
    "cafex_kahve": "Cafex 3'ü 1 Arada", "mahmood_kahve": "Mahmood Kahve",
    "nazar_naneli_sakiz": "Nazar Naneli Sakız", "nazar_damla_sakizli_sakiz": "Nazar Damla Sakızlı",
    "eti_hosbes_gofret": "Eti Hoşbeş Gofret", "centro_gofret": "Centro Gofret",
    "torku_nobir_gofret": "Torku No:1 Gofret", "citkirildim_cubuk_kraker": "Çıt Kırıldım Kraker",
    "eti_crax_cubuk_kraker": "Eti Crax Kraker", "ulker_cokoprens_biskuvi": "Ülker Çokoprens",
    "susse_biskuvi": "Süsse Bisküvi", "pensan_mavi_tukenmez_kalem": "Pensan Mavi Kalem",
    "pensan_siyah_tukenmez_kalem": "Pensan Siyah Kalem"
}

BARKOD_DATABASE = {
    "8692813005574": "kizilay_maden_suyu", "8691381000486": "beypazari_maden_suyu",
    "8697236914663": "60_sayfa_gipta_defter", "8697236914649": "80_sayfa_gipta_defter",
    "8699118011767": "cafex_kahve", "8697449912456": "mahmood_kahve",
    "8693323008109": "nazar_naneli_sakiz", "8693323006105": "nazar_damla_sakizli_sakiz",
    "8690526953625": "eti_hosbes_gofret", "8695077098979": "centro_gofret",
    "8690120060170": "torku_nobir_gofret", "8699118068389": "citkirildim_cubuk_kraker",
    "8690533074016": "eti_crax_cubuk_kraker", "8690504008002": "ulker_cokoprens_biskuvi",
    "8695077082954": "susse_biskuvi", "8692404907034": "pensan_mavi_tukenmez_kalem",
    "8692404907027": "pensan_siyah_tukenmez_kalem"
}

# =================================================================
# 2. FLASK SUNUCUSU VE GLOBAL DEĞİŞKENLER / FLASK SERVER AND GLOBAL VARIABLES
# =================================================================
app = Flask(__name__)

# kendi ödeme api ve secret keylerinizi girin. / Enter your own payment API and secret keys.
options = {
    'api_key': 'sandbox-OcfP6a',
    'secret_key': 'sandbox-Nprw1b',
    'base_url': 'sandbox-api.iyzipay.com'
}

anlik_sepet = {} 
latest_frame = None 
SISTEM_MODU = "YOLO_TARTI"
YENI_TARTI_VERISI = None 

SON_ISLENEN_AGIRLIK = 0.0 
BOS_KARE_SAYACI = 0 
SON_EKLENME_ZAMANI = 0.0 

# =================================================================
# 3. YARDIMCI FONKSİYONLAR / HELPER FUNCTIONS
# =================================================================
# Tartı sabit bir ağırlık verdiğinde çağrılacak geri çağırma fonksiyonu. / Callback function for when the scale provides a stable weight
def tarti_tetiklendi(stable_weight):  
    global YENI_TARTI_VERISI
    if SISTEM_MODU == "YOLO_TARTI":
        YENI_TARTI_VERISI = stable_weight

# Sepete ürün ekleyen fonksiyon. / Function to add a product to the cart
def sepete_urun_ekle(sistem_id): 
    ad = DISPLAY_NAMES.get(sistem_id, sistem_id)
    fiyat = PRICE_DATABASE.get(sistem_id, 0.0)
    
    if sistem_id in anlik_sepet:
        anlik_sepet[sistem_id]['adet'] += 1
    else:
        anlik_sepet[sistem_id] = {'id': sistem_id, 'ad': ad, 'fiyat': fiyat, 'adet': 1}
        
    print("\n" + "*"*50)
    print(f"🛒 [WEB] SEPETE EKLENDİ: {ad} (x{anlik_sepet[sistem_id]['adet']})")
    print("*"*50 + "\n")

# Ürünü ağırlık ve tespitler ile sessizce değerlendirir. / Silently evaluates the product based on weight and detections
def urunu_degerlendir_sessiz(agirlik, tespitler):
    if not tespitler: 
        return False, None

    # 1. DURUM: yolo.py sadece tek bir metin (string) döndürüyorsa (Örn: "kizilay_maden_suyu") / If yolo.py returns only a single text (string)
    if isinstance(tespitler, str):
        beklenen = DATABASE.get(tespitler, 0.0)
        if beklenen > 0 and abs(beklenen - agirlik) <= 2.0:
            return True, tespitler
        return False, None

    # 2. DURUM: yolo.py bir liste döndürüyorsa / If yolo.py returns a list
    if isinstance(tespitler, list) and len(tespitler) > 0:
        # 2A: Liste içi sözlükse (Örn: [{'name': 'kizilay', 'conf': 0.9}]) / If the list contains dictionaries
        if isinstance(tespitler[0], dict):
            en_iyi_isim = tespitler[0].get('name', '')
            en_iyi_guven = tespitler[0].get('conf', 0.0)
            
            if en_iyi_guven >= 0.85: 
                
                return True, en_iyi_isim
                
            for aday in tespitler[:3]:
                aday_isim = aday.get('name', '')
                beklenen = DATABASE.get(aday_isim, 0.0)
                if beklenen > 0 and abs(beklenen - agirlik) <= 2.0:
                    return True, aday_isim
            return False, None

        # 2B: Liste içi düz metinse (Örn: ['kizilay', 'beypazari']) / If the list contains plain strings
        elif isinstance(tespitler[0], str):
            for aday_isim in tespitler[:3]:
                beklenen = DATABASE.get(aday_isim, 0.0)
                if beklenen > 0 and abs(beklenen - agirlik) <= 2.0:
                    return True, aday_isim
            return False, None

    # Eğer tanınamayan bir format gelirse pas geç / If an unrecognized format is received, skip
    return False, None

# =================================================================
# 4. ARKA PLAN KAMERA VE YOLO DÖNGÜSÜ / BACKGROUND CAMERA AND YOLO LOOP
# =================================================================
# Donanım döngüsünü başlatan fonksiyon. / Function to start the hardware loop
def donanim_dongusu_baslat():
    global YENI_TARTI_VERISI, SISTEM_MODU, latest_frame, SON_ISLENEN_AGIRLIK, BOS_KARE_SAYACI, SON_EKLENME_ZAMANI
    
    print("[1] Donanımlar Başlatılıyor...")
    # model yolunda eğer hata alırsanız tam halini yazın. / If you get an error in the model path, write the full path.
    model_path = r"/Smart shopping cart/runs/detect/yolo11/weights/best.pt"
    
    try:
        yolo_analyzer = YoloAnalyzer(model_path)
    except Exception as e:
        print(f"YOLO Modeli Yüklenemedi: {e}")
        return
    
    # Tartı bağlantısını başlatıyoruz. Aygıt yöneticisinden tartının bağlı olan portunu girin. Örneğin: 'COM6' / We start the scale connection. Enter the port to which the scale is connected from the device manager. For example: 'COM6'
    tarti = ScaleReader(port='COM5', baudrate=115200, on_stable_callback=tarti_tetiklendi)
    tarti.start()
    
    # Kamera başlatıyoruz. / Starting the camera
    cap = cv2.VideoCapture(1)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

    # Eğer kamera açılamadıysa veya YOLO modeli yüklenemediyse hata veriyoruz. / If the camera cannot be opened or the YOLO model cannot be loaded, we give an error.
    if not cap.isOpened() or getattr(yolo_analyzer, 'model', None) is None:
        print("[✗] Donanımlar başlatılamadı! Kamerayı kontrol et.")
        return

    print("[✓] DONANIMLAR AKTİF. LÜTFEN ÜRÜNÜ TARTININ ÜZERİNE BIRAKIN.\n")
    DEGERLENDIRME_BASLANGICI = None
    
    while True:
        ret, frame = cap.read()
        if not ret:
            time.sleep(0.01)
            continue
            
        display_frame = frame

        if SISTEM_MODU == "YOLO_TARTI":
            annotated_frame, LATEST_DETECTIONS = yolo_analyzer.process_frame(frame)
            display_frame = annotated_frame
            
            if not LATEST_DETECTIONS:
                BOS_KARE_SAYACI += 1
                if BOS_KARE_SAYACI > 15: 
                    SON_ISLENEN_AGIRLIK = 0.0 
            else:
                BOS_KARE_SAYACI = 0 
            
            if YENI_TARTI_VERISI is not None:
                if SON_ISLENEN_AGIRLIK > 0 and abs(YENI_TARTI_VERISI - SON_ISLENEN_AGIRLIK) < 10.0:
                    if time.time() - SON_EKLENME_ZAMANI < 5.0: 
                        YENI_TARTI_VERISI = None
                        continue

                if DEGERLENDIRME_BASLANGICI is None:
                    print(f" TARTI ONAYI GELDİ: {YENI_TARTI_VERISI}g. Analiz ediliyor (10 Saniye)...")
                    DEGERLENDIRME_BASLANGICI = time.time()
                
                basarili_mi, tespit_edilen = urunu_degerlendir_sessiz(YENI_TARTI_VERISI, LATEST_DETECTIONS)
                
                if basarili_mi:
                    print(f"ÜRÜN TANINDI: {tespit_edilen}")
                    sepete_urun_ekle(tespit_edilen)
                    
                    SON_ISLENEN_AGIRLIK = YENI_TARTI_VERISI
                    SON_EKLENME_ZAMANI = time.time() 
                    YENI_TARTI_VERISI = None
                    DEGERLENDIRME_BASLANGICI = None
                else:
                    if time.time() - DEGERLENDIRME_BASLANGICI >= 10.0:
                        print("10 Saniye doldu! Ürün tam teşhis edilemedi.")
                        print("BARKOD MODUNA GEÇİLİYOR. Lütfen ürünü okutunuz.")
                        SISTEM_MODU = "BARKOD"
                        YENI_TARTI_VERISI = None
                        DEGERLENDIRME_BASLANGICI = None

        elif SISTEM_MODU == "BARKOD":
            annotated_frame, bulunan_barkodlar = barkod_oku(frame)
            display_frame = annotated_frame
            cv2.putText(display_frame, "!!! LUTFEN BARKOD OKUTUNUZ !!!", (80, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 0, 255), 2)
            
            if bulunan_barkodlar:
                for barkod_verisi in bulunan_barkodlar:
                    urun_id = BARKOD_DATABASE.get(barkod_verisi, "bilinmeyen")
                    if urun_id != "bilinmeyen":
                        print(f"BARKOD YAKALANDI: {barkod_verisi}")
                        sepete_urun_ekle(urun_id)
                        SON_EKLENME_ZAMANI = time.time()
                        
                        print("Otomatik Moda (YOLO) geri dönülüyor...")
                        SISTEM_MODU = "YOLO_TARTI"
                        time.sleep(1.5)
                        break

        ret, buffer = cv2.imencode('.jpg', display_frame)
        if ret:
            latest_frame = buffer.tobytes()

        time.sleep(0.03) 

# =================================================================
# 5. FLASK (WEB ARAYÜZÜ) YÖNLENDİRMELERİ / FLASK (WEB INTERFACE) ROUTES
# =================================================================

@app.route('/')
def ana_sayfa():
    return render_template('web_frontend.html')

@app.route('/sepet_bilgisi', methods=['GET'])
def sepet_bilgisi_getir():
    toplam_tutar = sum(urun['fiyat'] * urun['adet'] for urun in anlik_sepet.values())
    return jsonify({'urunler': list(anlik_sepet.values()), 'toplam_tutar': toplam_tutar})

@app.route('/sepet_guncelle', methods=['POST'])
def sepet_guncelle():
    veri = request.json
    urun_id = veri.get('id')
    islem = veri.get('islem')
    
    if urun_id in anlik_sepet:
        if islem == 'artir':
            anlik_sepet[urun_id]['adet'] += 1
        elif islem == 'azalt':
            anlik_sepet[urun_id]['adet'] -= 1
            if anlik_sepet[urun_id]['adet'] <= 0:
                del anlik_sepet[urun_id]
        elif islem == 'sil':
            del anlik_sepet[urun_id]
            
    return jsonify({'durum': 'basarili'})

def video_akis_olusturucu():
    global latest_frame
    while True:
        if latest_frame is None:
            time.sleep(0.1)
            continue
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + latest_frame + b'\r\n')

@app.route('/video_akis')
def video_akis():
    return Response(video_akis_olusturucu(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/odeme_yap', methods=['POST'])
def odeme_yap():
    gelen_veri = request.json
    toplam_tutar = sum(urun['fiyat'] * urun['adet'] for urun in anlik_sepet.values())
    
    if toplam_tutar <= 0:
        return jsonify({'durum': 'hata', 'mesaj': 'Sepetiniz boş!'})

    siparis_id = str(random.randint(100000, 999999))
    fiyat_str = f"{toplam_tutar:.2f}"

    istek = {
        'locale': 'tr',
        'conversationId': siparis_id,
        'price': fiyat_str,
        'paidPrice': fiyat_str,
        'currency': 'TRY',
        'installment': '1',
        'basketId': 'SEPET_' + siparis_id,
        'paymentChannel': 'WEB',
        'paymentGroup': 'PRODUCT',
        'paymentCard': {
            'cardHolderName': gelen_veri.get('kart_isim', 'Deneme Kullanicisi'),
            'cardNumber': gelen_veri.get('kart_no', '').replace(' ', ''),
            'expireMonth': gelen_veri.get('ay', ''),
            'expireYear': gelen_veri.get('yil', ''),
            'cvc': gelen_veri.get('cvc', ''),
            'registerCard': '0'
        },
        'buyer': {
            'id': 'BY789',
            'name': 'Akilli',
            'surname': 'Sepet',
            'identityNumber': '11111111111',
            'email': 'proje@ksu.edu.tr',
            'gsmNumber': '+905350000000',
            'registrationAddress': 'KSU Muhendislik Fakultesi',
            'city': 'Kahramanmaras',
            'country': 'Turkey',
            'zipCode': '46000',
            'ip': '85.34.78.112',                      
            'lastLoginDate': '2023-10-05 12:43:35',     
            'registrationDate': '2013-04-21 15:12:09'  
        },
        'shippingAddress': {
            'contactName': 'Akilli Sepet',
            'city': 'Kahramanmaras',
            'country': 'Turkey',
            'address': 'KSU Kampus',
            'zipCode': '46000'
        },
        'billingAddress': {
            'contactName': 'Akilli Sepet',
            'city': 'Kahramanmaras',
            'country': 'Turkey',
            'address': 'KSU Kampus',
            'zipCode': '46000'
        },
        'basketItems': [
            {'id': 'BI101', 'name': 'Akilli Sepet Fisiniz', 'category1': 'Alisveris', 'itemType': 'PHYSICAL', 'price': fiyat_str}
        ]
    }

    # Iyzipay ödeme isteğini gönderiyoruz ve yanıtı işliyoruz. / We send the Iyzipay payment request and process the response.
    try:
        yanit = iyzipay.Payment().create(istek, options)
        
        raw_read = yanit.read()
        if isinstance(raw_read, bytes):
            raw_read = raw_read.decode('utf-8')
        
        sonuc = json.loads(raw_read)
        
        if sonuc.get('status') == 'success':
            anlik_sepet.clear()
            return jsonify({'durum': 'basarili', 'mesaj': 'Ödeme başarıyla alındı!'})
        else:
            return jsonify({'durum': 'hata', 'mesaj': f"Ödeme reddedildi: {sonuc.get('errorMessage')}"})
            
    except Exception as e:
        return jsonify({'durum': 'hata', 'mesaj': 'Sistemsel Hata: ' + str(e)})

if __name__ == '__main__':
    freeze_support()
    donanim_thread = threading.Thread(target=donanim_dongusu_baslat, daemon=True)
    donanim_thread.start()
    
    print("[Web] Sunucu başlatılıyor... Lütfen tarayıcıdan http://127.0.0.1:5000 adresine gidin.")
    app.run(host='0.0.0.0', port=5000, debug=True, use_reloader=False)