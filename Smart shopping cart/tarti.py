import serial
import re
import time
import threading
from collections import deque

# Tartı Okuma Sınıfı / Scale Reading Class
class ScaleReader:
    def __init__(self, port, baudrate, on_stable_callback):
        self.port = port
        self.baudrate = baudrate
        self.on_stable_callback = on_stable_callback
        
        self.serial_conn = None
        self.is_running = False
        
        # Son 5 okumayı hafızada tutacak kuyruk (queue) / Keep the last 5 readings in memory
        self.readings = deque(maxlen=5)
        # Sadece ağırlık verisini yakalamak için regex / Regular expression to capture only the weight data
        self.regex = re.compile(r"Okuma:\s*([-\d\.]+)")

    def start(self):
        #Seri port bağlantısını başlatır ve dinleme thread'ini ayağa kaldırır. / Starts the serial port connection and launches the listening thread.
        try:
            self.serial_conn = serial.Serial(self.port, self.baudrate, timeout=1)
            # Boot mesajlarını atlamak için buffer'ı temizle / Clear the buffer to skip boot messages
            self.serial_conn.reset_input_buffer() 
            self.is_running = True
            
            # Dinleme döngüsünü arka planda başlat / Start the listening loop in the background
            thread = threading.Thread(target=self._read_loop, daemon=True)
            thread.start()
            print(f"[✓] Tartı bağlantısı başarılı ({self.port})")
            
        except serial.SerialException as e:
            print(f"[✗] Tartı bağlantı hatası ({self.port}): {e}")
            print(" -> Lütfen port numarasını kontrol edin ve Arduino IDE Seri Port Ekranı'nın kapalı olduğundan emin olun.")

    def _read_loop(self):
        # Sürekli olarak seri porttan gelen veriyi okuyan ve analiz eden özel metot. / A specialized method that continuously reads and analyzes data coming from a serial port.
        while self.is_running and self.serial_conn and self.serial_conn.is_open:
            try:
                line = self.serial_conn.readline().decode('utf-8', errors='ignore').strip()
                if not line:
                    continue
                
                match = self.regex.search(line)
                if match:
                    weight = float(match.group(1))
                    
                    # Terminalde anlık ağırlığı görmek için eklenen satır / Added line to see the instantaneous weight in the terminal
                    print(f" [Tartı Anlık Veri]: {weight:.1f}g", end='\r') 
                    
                    self.readings.append(weight)
                    self._check_stability()
                    
            except Exception:
                # Anlık okuma hatalarını yoksay ve devam et / Ignore instantaneous reading errors and continue
                pass
            time.sleep(0.01) # CPU'yu yormamak için kısa bekleme / Short wait to avoid overloading the CPU

    def _check_stability(self):
        """Son 5 ölçümün son 4'ünü kontrol ederek stabilitesini denetler."""
        if len(self.readings) == 5:
            # Son 4 ölçümü al / Take the last 4 readings
            last_4 = list(self.readings)[1:5]
            max_val = max(last_4)
            min_val = min(last_4)
            
            # Eğer son 4 okuma arasındaki maksimum fark 0.5 gramdan küçükse ve ağırlık > 2.0 ise / If the maximum difference between the last 4 readings is less than 0.5 grams and the weight > 2.0
            if (max_val - min_val) < 0.5 and sum(last_4)/4 > 2.0:
                stable_weight = round(sum(last_4) / 4, 2)
                
                # Terminalin daha temiz görünmesi için yeni bir satıra geç / Move to a new line for a cleaner terminal appearance
                print("") 
                
                # Callback fonksiyonunu tetikle / Trigger the callback function
                self.on_stable_callback(stable_weight)
                # Sürekli tetiklenmeyi önlemek için kuyruğu temizle / Clear the queue to prevent continuous triggering
                self.readings.clear() 

    def stop(self):
        """Sistemi ve portu güvenli şekilde kapatır."""
        self.is_running = False
        if self.serial_conn and self.serial_conn.is_open:
            self.serial_conn.close()
            print(f"\n[!] Tartı bağlantısı kapatıldı ({self.port}).")