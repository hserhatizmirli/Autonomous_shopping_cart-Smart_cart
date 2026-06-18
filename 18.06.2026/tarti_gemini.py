import serial
import re
import time
import threading
from collections import deque

class ScaleReader:
    def __init__(self, port, baudrate, on_stable_callback):
        self.port = port
        self.baudrate = baudrate
        self.on_stable_callback = on_stable_callback
        
        self.serial_conn = None
        self.is_running = False
        
        # Son 5 okumayı hafızada tutacak kuyruk (queue)
        self.readings = deque(maxlen=5)
        # Sadece ağırlık verisini yakalamak için regex
        self.regex = re.compile(r"Okuma:\s*([-\d\.]+)")

    def start(self):
        """Seri port bağlantısını başlatır ve dinleme thread'ini ayağa kaldırır."""
        try:
            self.serial_conn = serial.Serial(self.port, self.baudrate, timeout=1)
            self.serial_conn.reset_input_buffer() # Boot mesajlarını atlamak için buffer'ı temizle
            self.is_running = True
            
            # Dinleme döngüsünü arka planda başlat
            thread = threading.Thread(target=self._read_loop, daemon=True)
            thread.start()
            print(f"[✓] Tartı bağlantısı başarılı ({self.port})")
            
        except serial.SerialException as e:
            print(f"[✗] Tartı bağlantı hatası ({self.port}): {e}")
            print(" -> Lütfen port numarasını kontrol edin ve Arduino IDE Seri Port Ekranı'nın kapalı olduğundan emin olun.")

    def _read_loop(self):
        """Sürekli olarak seri porttan gelen veriyi okuyan ve analiz eden özel metot."""
        while self.is_running and self.serial_conn and self.serial_conn.is_open:
            try:
                line = self.serial_conn.readline().decode('utf-8', errors='ignore').strip()
                if not line:
                    continue
                
                match = self.regex.search(line)
                if match:
                    weight = float(match.group(1))
                    
                    # Terminalde anlık ağırlığı görmek için eklenen satır
                    print(f" [Tartı Anlık Veri]: {weight:.1f}g", end='\r') 
                    
                    self.readings.append(weight)
                    self._check_stability()
                    
            except Exception:
                # Anlık okuma hatalarını yoksay ve devam et
                pass
            time.sleep(0.01) # CPU'yu yormamak için kısa bekleme

    def _check_stability(self):
        """Son 5 ölçümün son 4'ünü kontrol ederek stabilitesini denetler."""
        if len(self.readings) == 5:
            # Son 4 ölçümü al
            last_4 = list(self.readings)[1:5]
            max_val = max(last_4)
            min_val = min(last_4)
            
            # Eğer son 4 okuma arasındaki maksimum fark 0.5 gramdan küçükse ve ağırlık > 2.0 ise
            if (max_val - min_val) < 0.5 and sum(last_4)/4 > 2.0:
                stable_weight = round(sum(last_4) / 4, 2)
                
                # Terminalin daha temiz görünmesi için yeni bir satıra geç
                print("") 
                
                # Callback fonksiyonunu tetikle
                self.on_stable_callback(stable_weight)
                # Sürekli tetiklenmeyi önlemek için kuyruğu temizle
                self.readings.clear() 

    def stop(self):
        """Sistemi ve portu güvenli şekilde kapatır."""
        self.is_running = False
        if self.serial_conn and self.serial_conn.is_open:
            self.serial_conn.close()
            print(f"\n[!] Tartı bağlantısı kapatıldı ({self.port}).")