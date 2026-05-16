import tensorflow as tf
import os
import glob

print("TensorFlow sürümü:", tf.__version__)

# Klasör Yolları
source_dir = 'C:\\Users\\hsisec\\Desktop\\ekle'
target_dir = 'C:\\Users\\hsisec\\Desktop\\yeni'
os.makedirs(target_dir, exist_ok=True)

# Resimleri Bul
resim_uzantilari = ['*.jpg', '*.jpeg', '*.png']
resim_listesi = []
for uzanti in resim_uzantilari:
    resim_listesi.extend(glob.glob(os.path.join(source_dir, uzanti)))
    resim_listesi.extend(glob.glob(os.path.join(source_dir, uzanti.upper())))

print(f"Bulunan resim sayısı: {len(resim_listesi)}")

# ---------- BOYUT AYARI ----------
target_size = (640, 640)
# ---------------------------------

print(f"Hedef boyut: {target_size[0]}×{target_size[1]}")

# Efektler
rotate_angles = [1, 2, 3, 4]  # 90°, 180°, 270°, 360°
dark_factor = 0.32
bright_factor = 0.32
blur_sigma = 2.8

print(f"Her orijinal görüntü için:")
print(f"  1. 4 farklı döndürme (90°, 180°, 270°, 360°)")
print(f"  2. Her döndürülmüş görüntüye:")
print(f"     - Dark (karartma)")
print(f"     - Bright (aydınlatma)")
print(f"     - Blur (bulanıklaştırma)")
print(f"Toplam: {len(resim_listesi)} × 4 rotasyon × 3 efekt = {len(resim_listesi) * 4 * 3} resim")
print("-" * 50)

def apply_rotate(image, k):
    """90 derece döndürme"""
    return tf.image.rot90(image, k=k)

def apply_dark(image, factor=0.3):
    """Karartma"""
    image = tf.expand_dims(image, 0)
    image = tf.keras.layers.RandomBrightness(factor=-factor)(image, training=True)
    return tf.squeeze(image, 0)

def apply_bright(image, factor=0.3):
    """Aydınlatma"""
    image = tf.expand_dims(image, 0)
    image = tf.keras.layers.RandomBrightness(factor=factor)(image, training=True)
    return tf.squeeze(image, 0)

def apply_blur(image, sigma=1.0):
    """Bulanıklaştırma"""
    image = tf.expand_dims(image, 0)
    try:
        image = tf.image.gaussian_filter2d(image, sigma=sigma)
    except:
        kernel = tf.ones((3, 3, 3, 1)) / 9.0
        image = tf.nn.depthwise_conv2d(image, kernel, strides=[1, 1, 1, 1], padding='SAME')
    return tf.squeeze(image, 0)

def save_image(image_array, filename):
    """Görüntüyü kaydetme yardımcı fonksiyonu"""
    image_array = tf.clip_by_value(image_array, 0, 255)
    image_array = tf.cast(image_array, tf.uint8)
    pil_img = tf.keras.utils.array_to_img(image_array)
    pil_img.save(filename, quality=95)

sayac = 0
for img_path in resim_listesi:
    print(f"İşleniyor: {os.path.basename(img_path)}")
    
    # Resmi yükle
    img = tf.keras.utils.load_img(img_path, target_size=target_size)
    img_array = tf.keras.utils.img_to_array(img)
    
    # Her döndürme açısı için
    for r in rotate_angles:
        # Önce döndürme işlemini uygula
        rotated = apply_rotate(img_array, r)
        rot_angle = r * 90
        
        # ----- 1. DARK (karartılmış döndürülmüş) -----
        dark_img = apply_dark(rotated, factor=dark_factor)
        save_path = os.path.join(target_dir, f"rotate_{rot_angle}deg_dark_{os.path.basename(img_path)}")
        save_image(dark_img, save_path)
        sayac += 1
        
        # ----- 2. BRIGHT (aydınlatılmış döndürülmüş) -----
        bright_img = apply_bright(rotated, factor=bright_factor)
        save_path = os.path.join(target_dir, f"rotate_{rot_angle}deg_bright_{os.path.basename(img_path)}")
        save_image(bright_img, save_path)
        sayac += 1
        
        # ----- 3. BLUR (bulanıklaştırılmış döndürülmüş) -----
        blur_img = apply_blur(rotated, sigma=blur_sigma)
        save_path = os.path.join(target_dir, f"rotate_{rot_angle}deg_blur_{os.path.basename(img_path)}")
        save_image(blur_img, save_path)
        sayac += 1
    
    print(f"  ✓ {os.path.basename(img_path)} için 12 varyasyon (4 rotasyon × 3 efekt) oluşturuldu")

print(f"\n TOPLAM {sayac/2} resim oluşturuldu!")
print(f" Klasör: {target_dir}")
print(f" Boyut: {target_size[0]}×{target_size[1]}")
print(f" Oran: Her orijinal görüntü 12 kata çıkarıldı (4 rotasyon × 3 efekt)")