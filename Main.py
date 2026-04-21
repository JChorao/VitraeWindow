import customtkinter as ctk
import requests
from PIL import Image
import threading
from datetime import datetime
from io import BytesIO
import os
import sys

# --- IMPORTAÇÕES FIREBASE ---
import firebase_admin
from firebase_admin import credentials, firestore

# --- MOCK PARA GPIO ---
try:
    import RPi.GPIO as GPIO
    ON_RASPBERRY = True
except (ImportError, RuntimeError):
    ON_RASPBERRY = False
    class GPIO_Mock:
        BCM = "BCM"
        IN = "IN"
        LOW = 0
        HIGH = 1        
        @staticmethod
        def setmode(mode): pass        
        @staticmethod
        def setup(pin, mode): pass        
        @staticmethod
        def input(pin): return 1          
        @staticmethod
        def setwarnings(flag): pass        
        @staticmethod
        def cleanup(): pass
    GPIO = GPIO_Mock()

# --- CONFIGURAÇÃO VISUAL ---
ctk.set_appearance_mode("light")
ctk.set_default_color_theme("blue")

# --- CONFIGURAÇÕES API ---
LASTFM_API_KEY = "TUA_API_KEY_AQUI"
LASTFM_USERNAME = "TEU_USERNAME_DO_LASTFM"
GAS_SENSOR_PIN = 26 


class VitraeDashboard:
    def __init__(self, root):
        self.root = root
        self.root.title("VitraeView - Produção")
        
        self.screen_width = self.root.winfo_screenwidth()
        self.screen_height = self.root.winfo_screenheight()
        self.root.geometry(f"{self.screen_width}x{self.screen_height}")
        
        self.bg_color = "#ffffff"
        self.text_color = "#1a1a1a"
        
        self.db = None
        self.device_id = None
        self.alert_active = False

        self.setup_firebase()
        self.validate_device()
        self.report_resolution_to_firebase()

        self.create_widgets()

        self.start_layout_listener()
        
        GPIO.setwarnings(False)
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(GAS_SENSOR_PIN, GPIO.IN)

        self.update_clock()
        self.check_gas_sensor()

        self.resize_timer = None
        self.root.bind("<Configure>", self.on_window_resize)

    def setup_firebase(self):
        try:
            if not firebase_admin._apps:
                cred = credentials.Certificate("serviceAccountKey.json")
                firebase_admin.initialize_app(cred)
            self.db = firestore.client()
        except Exception as e:
            print(f"Erro Firebase: {e}")
            sys.exit(1)

    def validate_device(self):
        id_file = "vitrae_id.txt"
        if not os.path.exists(id_file):
            print("❌ Erro: vitrae_id.txt não encontrado.")
            sys.exit(1)
        with open(id_file, "r") as f:
            self.device_id = f.read().strip()

    def report_resolution_to_firebase(self):
        if self.db and self.device_id:
            try:
                self.db.collection('windows').document(self.device_id).update({
                    'resW': self.screen_width,
                    'resH': self.screen_height
                })
            except Exception: pass

    def on_window_resize(self, event):
        if event.widget == self.root:
            if self.resize_timer:
                self.resize_timer.cancel()
            self.resize_timer = threading.Timer(1.0, self.handle_resize, args=[event.width, event.height])
            self.resize_timer.start()

    def handle_resize(self, width, height):
        if width != self.screen_width or height != self.screen_height:
            self.screen_width = width
            self.screen_height = height
            self.report_resolution_to_firebase()

    def create_widgets(self):
        """Cria os objetos com cores sólidas para espelhar exatamente as caixas do Flutter"""
        self.root.configure(fg_color=self.bg_color)

        self.clock_card = ctk.CTkFrame(self.root, fg_color="#1a1a1a", corner_radius=10, width=250, height=120)
        self.lbl_time = ctk.CTkLabel(self.clock_card, text="00:00:00", font=("Roboto", 40, "bold"), text_color="white")
        self.lbl_time.place(relx=0.5, rely=0.5, anchor="center")

        # Widget de Clima (Caixa inteira Azul)
        self.weather_card = ctk.CTkFrame(self.root, fg_color="#2980b9", corner_radius=10, width=200, height=120)
        self.lbl_temp = ctk.CTkLabel(self.weather_card, text="--°C", font=("Roboto", 32, "bold"), text_color="white")
        self.lbl_temp.place(relx=0.5, rely=0.5, anchor="center")

        # Widget de Gás (Caixa inteira Verde)
        self.gas_card = ctk.CTkFrame(self.root, fg_color="#27ae60", corner_radius=10, width=220, height=80)
        self.gas_indicator = ctk.CTkLabel(self.gas_card, text="GÁS: OK", font=("Roboto", 18, "bold"), text_color="white")
        self.gas_indicator.place(relx=0.5, rely=0.5, anchor="center")

    def start_layout_listener(self):
        doc_ref = self.db.collection('windows').document(self.device_id)
        def on_snapshot(doc_snapshot, changes, read_time):
            for doc in doc_snapshot:
                data = doc.to_dict()
                if data:
                    self.root.after(0, lambda: self.apply_dynamic_layout(data))
        doc_ref.on_snapshot(on_snapshot)

    def limit_coords(self, val):
        """Impede que o widget cole totalmente na borda (Margem de 5%)"""
        margin = 0.08 # 8% de margem de segurança
        return max(margin, min(val, 1.0 - margin))

    def apply_dynamic_layout(self, data):
        self.clock_card.place_forget()
        self.weather_card.place_forget()
        self.gas_card.place_forget()

        #Usamos anchor="nw" (North-West / Canto Superior Esquerdo)
        # para que a matemática bata certo com a app do Flutter!

        if 'clockX' in data and 'clockY' in data:
            self.clock_card.place(relx=data['clockX'], rely=data['clockY'], anchor="nw")

        if 'weatherX' in data and 'weatherY' in data:
            self.weather_card.place(relx=data['weatherX'], rely=data['weatherY'], anchor="nw")
            self.update_weather() 

        if 'gasX' in data and 'gasY' in data:
            self.gas_card.place(relx=data['gasX'], rely=data['gasY'], anchor="nw")

    def update_clock(self):
        self.lbl_time.configure(text=datetime.now().strftime("%H:%M:%S"))
        self.root.after(1000, self.update_clock)

    def update_weather(self):
        def fetch():
            try:
                url = "https://api.open-meteo.com/v1/forecast?latitude=39.82&longitude=-7.49&current_weather=true"
                res = requests.get(url, timeout=5).json()
                temp = res['current_weather']['temperature']
                self.root.after(0, lambda: self.lbl_temp.configure(text=f"{temp}°C"))
            except: pass
        threading.Thread(target=fetch, daemon=True).start()

    def check_gas_sensor(self):
        gas_detected = GPIO.input(GAS_SENSOR_PIN) == GPIO.LOW
        if gas_detected and not self.alert_active:
            self.activate_alert()
            self.send_gas_status(1)
        elif not gas_detected and self.alert_active:
            self.deactivate_alert()
            self.send_gas_status(0)
        self.root.after(1000, self.check_gas_sensor)

    def send_gas_status(self, val):
        if self.db:
            self.db.collection('windows').document(self.device_id).update({'gas': val})

    def activate_alert(self):
        self.alert_active = True
        self.alert_frame = ctk.CTkFrame(self.root, fg_color="#e74c3c")
        self.alert_frame.place(relx=0, rely=0, relwidth=1, relheight=1)
        ctk.CTkLabel(self.alert_frame, text="⚠️ FUGA DE GÁS!", font=("Roboto", 50, "bold"), text_color="white").place(relx=0.5, rely=0.5, anchor="center")

    def deactivate_alert(self):
        self.alert_active = False
        if hasattr(self, 'alert_frame'): self.alert_frame.destroy()


if __name__ == "__main__":
    root = ctk.CTk()
    app = VitraeDashboard(root)
    root.mainloop()