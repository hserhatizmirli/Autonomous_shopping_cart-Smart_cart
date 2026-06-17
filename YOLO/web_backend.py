from flask import Flask, render_template, request, jsonify
import iyzipay
import time
import random

# Flask web sunucumuzu başlatıyoruz
app = Flask(__name__)

# İyzico test (sandbox) API ayarları
api_key = 'sandbox-OcfP6a6SMhF7mSTajGdOglfgA6YnyvOf'
secret_key = 'sandbox-Nprw1bJ2eYRJtd79DtQ9cl1Uc78j4lhv'

options = {
    'api_key': api_key,
    'secret_key': secret_key,
    'base_url': 'https://sandbox-api.iyzipay.com'
}

# Geçici bir veritabanı
# Kamera bir ürünü onayladığında bu listeye eklenecek
anlik_sepet = []

# Kullanıcı ekrana baktığında ana sayfayı yükleyen fonksiyon
@app.route('/')
def ana_sayfa():
    # templates klasöründeki web_frontend.html'i ekrana basar
    return render_template('web_frontend.html')

# Sepetteki ürünleri anlık olarak HTML arayüzüne gönderen API (Senkronizasyon için)
@app.route('/sepet_bilgisi', methods=['GET'])
def sepet_bilgisi_getir():
    toplam_tutar = sum(urun['fiyat'] for urun in anlik_sepet)
    
    return jsonify({
        'urunler': anlik_sepet,
        'toplam': toplam_tutar
    })

# İyzico ödeme işlemini başlatan asıl API
@app.route('/odeme_yap', methods=['POST'])
def odeme_islemini_baslat():
    # Arayüzden (Frontend'den) gelen kart bilgilerini alıyoruz
    gelen_veri = request.json
    kart_no = gelen_veri.get('kart_no', '').replace(" ", "")
    
    toplam_tutar = sum(urun['fiyat'] for urun in anlik_sepet)
    
    if toplam_tutar == 0:
        return jsonify({'durum': 'hata', 'mesaj': 'Sepetiniz boş!'})

    # İyzico her siparişte farklı bir ID istiyor, o yüzden rastgele ID üretiyoruz
    siparis_id = str(random.randint(1000, 9999))
    
    # İyzico'ya gidecek veri paketi
    istek = {
        'locale': 'tr',
        'conversationId': siparis_id,
        'price': str(toplam_tutar),
        'paidPrice': str(toplam_tutar),
        'currency': 'TRY',
        'installment': '1',
        'basketId': 'SEPET_' + siparis_id,
        'paymentChannel': 'WEB',
        'paymentGroup': 'PRODUCT',
        'paymentCard': {
            'cardHolderName': 'Akilli Sepet Musterisi',
            'cardNumber': kart_no,
            'expireMonth': gelen_veri.get('ay'),
            'expireYear': gelen_veri.get('yil'),
            'cvc': gelen_veri.get('cvc'),
            'registerCard': '0'
        },
        # Sahte bilgiler
        'buyer': {
            'id': 'MUSTERI_1',
            'name': 'Misafir',
            'surname': 'Kullanici',
            'gsmNumber': '+905551234567',
            'email': 'proje@ksu.edu.tr',
            'identityNumber': '11111111111',
            'registrationAddress': 'KSU Muhendislik Fakultesi',
            'ip': '85.34.78.112',
            'city': 'Kahramanmaras',
            'country': 'Turkey',
            'zipCode': '46000'
        },
        'shippingAddress': {
            'contactName': 'Misafir Kullanici',
            'city': 'Kahramanmaras',
            'country': 'Turkey',
            'address': 'KSU Kampus',
            'zipCode': '46000'
        },
        'billingAddress': {
            'contactName': 'Misafir Kullanici',
            'city': 'Kahramanmaras',
            'country': 'Turkey',
            'address': 'KSU Kampus',
            'zipCode': '46000'
        },
        'basketItems': [
            {
                'id': 'URUN_1',
                'name': 'Sepet Toplami',
                'category1': 'Genel',
                'itemType': 'PHYSICAL',
                'price': str(toplam_tutar)
            }
        ]
    }

    try:
        time.sleep(1.2) 
        
        yanit = iyzipay.Payment().create(istek, options)
        sonuc = yanit.read()
        
        if sonuc.get('status') == 'success':
            anlik_sepet.clear() # Ödeme başarılıysa sanal sepeti boşalt
            return jsonify({'durum': 'basarili', 'mesaj': 'Ödeme başarıyla alındı!'})
        else:
            hata_mesaji = sonuc.get('errorMessage')
            return jsonify({'durum': 'hata', 'mesaj': f'Ödeme reddedildi: {hata_mesaji}'})
            
    except Exception as e:
        # Kod patlarsa sunucu çökmesin diye Try-Except kullandık
        return jsonify({'durum': 'hata', 'mesaj': 'Sistemsel Hata: ' + str(e)})


# Kamera (YOLO) ve Sensör onayı verdikten sonra ürünü sepete gönderen API
@app.route('/sepete_ekle', methods=['POST'])
def sepete_ekle():
    gelen_urun = request.json
    
    # Gelen veriyi (isim ve fiyat) listemize ekliyoruz
    anlik_sepet.append({
        'ad': gelen_urun.get('ad', 'Bilinmeyen Ürün'),
        'fiyat': float(gelen_urun.get('fiyat', 0.0))
    })
    
    return jsonify({'durum': 'basarili', 'mesaj': f"{gelen_urun.get('ad')} sepete eklendi!"})
    
    
# Kod dosyasını çalıştırdığımızda web sunucusunu ayağa kaldıran kısım
if __name__ == '__main__':
    # debug=True sayesinde kodda bir şeyi değiştirip kaydedince sunucu otomatik yenilenir
    app.run(debug=True, port=5000)