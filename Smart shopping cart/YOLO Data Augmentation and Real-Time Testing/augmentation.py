import os
import tensorflow as tf
import glob
import random
import shutil

# --- GEREKSİZ UYARILARI SUSTURMA / SILENCE UNNECESSARY DOLLARS ---
os.environ['TF_ENABLE_ONEDNN_OPTS'] = '0'
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'

# augmentation.py dosyasının bulunduğu klasörü otomatik bulur / Finds the folder where augmentation.py is located automatically
MEVCUT_KLASOR = os.path.dirname(os.path.abspath(__file__))

# Hemen yanındaki "raw data" ve "Aug data" klasörlerine kilitlenir / Locks onto the "raw data" and "Aug data" folders right next to it
source_dir = os.path.join(MEVCUT_KLASOR, "raw data")
target_dir = os.path.join(MEVCUT_KLASOR, "Aug data")

# Eğer raw data klasörü yanlışlıkla silindiyse kod çökmesin diye boş oluşturur / If the raw data folder is accidentally deleted, it creates an empty one to prevent code crash
os.makedirs(source_dir, exist_ok=True)

# --- TEMİZLİK: Hedef klasör varsa sil ve yeniden oluştur / Clean: If target folder exists, delete and recreate it ---
if os.path.exists(target_dir):
    shutil.rmtree(target_dir)
os.makedirs(target_dir, exist_ok=True)

# Resimleri Bul / Find images
resim_uzantilari = ['*.jpg', '*.jpeg', '*.png', '*.JPG', '*.JPEG', '*.PNG']
resim_listesi = []
for uzanti in resim_uzantilari:
    resim_listesi.extend(glob.glob(os.path.join(source_dir, uzanti)))

# Aynı dosyanın listede iki kez olmasını engelle / Prevent the same file from appearing twice in the list
resim_listesi = list(set(resim_listesi))

print(f"Kaynak klasördeki net orijinal resim sayısı: {len(resim_listesi)}")

# ---------- AYARLAR / SETTINGS ----------
target_size = (640, 640)
dark_factor = 0.28
bright_factor = 0.28
# -----------------------------

def apply_rotate_and_blur(image):
    # 1. Rotate
    angles = [a for a in range(0, 360, 10)]
    chosen_angle = random.choice(angles)
    factor = chosen_angle / 360.0
    rotate_layer = tf.keras.layers.RandomRotation(factor=(factor, factor), fill_mode='constant')
    
    image = tf.expand_dims(image, 0)
    processed = rotate_layer(image, training=True)
    
    # 2. Blur
    kernel = tf.ones((3, 3, 3, 1)) / 9.0
    processed = tf.nn.depthwise_conv2d(processed, kernel, strides=[1, 1, 1, 1], padding='SAME')
    
    return tf.squeeze(processed, 0), chosen_angle

def apply_dark(image, factor=0.32):
    image = tf.expand_dims(image, 0)
    image = tf.keras.layers.RandomBrightness(factor=(-factor, -factor))(image, training=True)
    return tf.squeeze(image, 0)

def apply_bright(image, factor=0.32):
    image = tf.expand_dims(image, 0)
    image = tf.keras.layers.RandomBrightness(factor=(factor, factor))(image, training=True)
    return tf.squeeze(image, 0)

def save_image(image_array, filename):
    image_array = tf.clip_by_value(image_array, 0, 255)
    image_array = tf.cast(image_array, tf.uint8)
    pil_img = tf.keras.utils.array_to_img(image_array)
    pil_img.save(filename, quality=95)

sayac = 0
for img_path in resim_listesi:
    base_name = os.path.basename(img_path)
    
    # Orijinal resmi yükle / Load the original image
    img = tf.keras.utils.load_img(img_path, target_size=target_size)
    original_array = tf.keras.utils.img_to_array(img)
    
    # --- 1. process: Rotate + Blur ---
    rot_blur_img, angle = apply_rotate_and_blur(original_array)
    save_image(rot_blur_img, os.path.join(target_dir, f"v1_rot{angle}_blur_{base_name}"))
    
    # --- 2. process: Dark ---
    dark_img = apply_dark(original_array, factor=dark_factor)
    save_image(dark_img, os.path.join(target_dir, f"v2_dark_{base_name}"))
    
    # --- 3. process: Bright ---
    bright_img = apply_bright(original_array, factor=bright_factor)
    save_image(bright_img, os.path.join(target_dir, f"v3_bright_{base_name}"))
    
    sayac += 3

print("-" * 50)
print(f"İŞLEM TAMAM!")
print(f"Girdi: {len(resim_listesi)} resim")
print(f"Çıktı: {sayac} resim (Tam olarak 3 katı)")
print(f"Klasör: {target_dir}")