from flask import Flask, render_template, request, jsonify
import iyzipay
import time
import random

# Flask web sunucumuzu başlatıyoruz / Starting our Flask web server
app = Flask(__name__)

# İyzico test (sandbox) API ayarları, kendi api keylerinizi girin / Iyzico test (sandbox) API settings: Enter your own API keys.
api_key = 'sandbox-OcfP6a'
secret_key = 'sandbox-Nprw1b'

options = {
    'api_key': api_key,
    'secret_key': secret_key,
    'base_url': 'sandbox-api.iyzipay.com'
}

# Geçici bir veritabanı / Temporary database for the shopping cart
# Kamera bir ürünü onayladığında bu listeye eklenecek / When the camera approves a product, it will be added to this list
anlik_sepet = []

# Kullanıcı ekrana baktığında ana sayfayı yükleyen fonksiyon / Function that loads the main page when the user looks at the screen
@app.route('/')
def ana_sayfa():
    # templates klasöründeki web_frontend.html'i ekrana basar / Renders the web_frontend.html from the templates folder
    return render_template('web_frontend.html')

# Sepetteki ürünleri anlık olarak HTML arayüzüne gönderen API (Senkronizasyon için) / API that sends the products in the cart to the HTML interface in real-time (for synchronization)
@app.route('/sepet_bilgisi', methods=['GET'])
def sepet_bilgisi_getir():
    toplam_tutar = sum(urun['fiyat'] for urun in anlik_sepet)
    
    return jsonify({
        'urunler': anlik_sepet,
        'toplam': toplam_tutar
    })

# İyzico ödeme işlemini başlatan asıl API / The main API that initiates the Iyzico payment process
@app.route('/odeme_yap', methods=['POST'])
def odeme_islemini_baslat():
    # Arayüzden (Frontend'den) gelen kart bilgilerini alıyoruz / We are getting the card information coming from the frontend
    gelen_veri = request.json
    kart_no = gelen_veri.get('kart_no', '').replace(" ", "")
    
    toplam_tutar = sum(urun['fiyat'] for urun in anlik_sepet)
    
    if toplam_tutar == 0:
        return jsonify({'durum': 'hata', 'mesaj': 'Sepetiniz boş!'})

    # İyzico her siparişte farklı bir ID istiyor, o yüzden rastgele ID üretiyoruz / Iyzico requires a different ID for each order, so we generate a random ID
    siparis_id = str(random.randint(1000, 9999))
    
    # İyzico'ya gidecek veri paketi / Data package to be sent to Iyzico
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
            anlik_sepet.clear() # Ödeme başarılıysa sanal sepeti boşalt / If the payment is successful, clear the virtual cart
            return jsonify({'durum': 'basarili', 'mesaj': 'Ödeme başarıyla alındı!'})
        else:
            hata_mesaji = sonuc.get('errorMessage')
            return jsonify({'durum': 'hata', 'mesaj': f'Ödeme reddedildi: {hata_mesaji}'})
            
    except Exception as e:
        # Kod patlarsa sunucu çökmesin diye Try-Except kullandık / We used Try-Except so that the server does not crash if the code fails
        return jsonify({'durum': 'hata', 'mesaj': 'Sistemsel Hata: ' + str(e)})


# Kamera (YOLO) ve Sensör onayı verdikten sonra ürünü sepete gönderen API / API that sends the product to the cart after camera (YOLO) and sensor approval
@app.route('/sepete_ekle', methods=['POST'])
def sepete_ekle():
    gelen_urun = request.json
    
    # Gelen veriyi (isim ve fiyat) listemize ekliyoruz / We add the incoming data (name and price) to our list
    anlik_sepet.append({
        'ad': gelen_urun.get('ad', 'Bilinmeyen Ürün'),
        'fiyat': float(gelen_urun.get('fiyat', 0.0))
    })
    
    return jsonify({'durum': 'basarili', 'mesaj': f"{gelen_urun.get('ad')} sepete eklendi!"})
    
    
# Kod dosyasını çalıştırdığımızda web sunucusunu ayağa kaldıran kısım / The part that starts the web server when we run the code file
if __name__ == '__main__':
    # debug=True sayesinde kodda bir şeyi değiştirip kaydedince sunucu otomatik yenilenir / Thanks to debug=True, when we change something in the code and save it, the server automatically refreshes
    app.run(debug=True, port=5010)