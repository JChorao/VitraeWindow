import customtkinter as ctk
import requests
import threading
from datetime import datetime
import os
import sys
import pytz  # Para os fusos horários

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
GAS_SENSOR_PIN = 26 

class VitraeDashboard:
    def __init__(self, root):
        self.root = root
        self.root.title("VitraeView - Produção")
        
        self.screen_width = self.root.winfo_screenwidth()
        self.screen_height = self.root.winfo_screenheight()
        self.root.geometry(f"{self.screen_width}x{self.screen_height}")
        
        self.bg_color = "#ffffff"
        self.root.configure(fg_color=self.bg_color)
        
        self.db = None
        self.device_id = None
        self.alert_active = False

        # DICIONÁRIO VITAL: Guarda os widgets que estão visíveis neste momento
        self.active_widgets = {}

        print("🔄 A Iniciar Sistema VitraeView...")
        self.setup_firebase()
        self.validate_device()
        self.report_resolution_to_firebase()

        self.start_layout_listener()
        
        GPIO.setwarnings(False)
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(GAS_SENSOR_PIN, GPIO.IN)
        self.check_gas_sensor()

        self.resize_timer = None
        self.root.bind("<Configure>", self.on_window_resize)

    def setup_firebase(self):
        try:
            if not firebase_admin._apps:
                cred = credentials.Certificate("serviceAccountKey.json")
                firebase_admin.initialize_app(cred)
            self.db = firestore.client()
            print("✅ Firebase ligada com sucesso!")
        except Exception as e:
            print(f"❌ Erro Firebase: {e}")
            sys.exit(1)

    def validate_device(self):
        id_file = "vitrae_id.txt"
        if not os.path.exists(id_file):
            print("❌ Erro: vitrae_id.txt não encontrado.")
            sys.exit(1)
        with open(id_file, "r") as f:
            self.device_id = f.read().strip()
            print(f"✅ Dispositivo Validado: {self.device_id}")

    def report_resolution_to_firebase(self):
        if self.db and self.device_id:
            try:
                # CORREÇÃO: set() com merge=True não dá erro se o documento for novo!
                self.db.collection('windows').document(self.device_id).set({
                    'resW': self.screen_width,
                    'resH': self.screen_height
                }, merge=True)
                print(f"📏 Resolução reportada: {self.screen_width}x{self.screen_height}")
            except Exception as e:
                print(f"⚠️ Erro ao reportar resolução: {e}")

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

    # ==========================================
    # CÉREBRO DINÂMICO DE WIDGETS
    # ==========================================
    def start_layout_listener(self):
        doc_ref = self.db.collection('windows').document(self.device_id)
        
        def on_snapshot(doc_snapshot, changes, read_time):
            for doc in doc_snapshot:
                if doc.exists:
                    data = doc.to_dict()
                    # O "self.root.after" garante que atualizamos a janela no momento certo
                    self.root.after(0, self.apply_dynamic_layout, data)

        doc_ref.on_snapshot(on_snapshot)
        print("🎧 A escutar base de dados em tempo real...")

    def apply_dynamic_layout(self, data):
        firebase_widgets = data.get('widgets', {})
        print(f"📦 Recebido layout da App: {len(firebase_widgets)} widgets encontrados.")

        # 1. ELIMINAR widgets que foram apagados na App
        active_ids = list(self.active_widgets.keys())
        for wid in active_ids:
            if wid not in firebase_widgets:
                self.destroy_widget(wid)

        # 2. CRIAR ou ATUALIZAR os widgets da App
        for wid, w_data in firebase_widgets.items():
            if wid not in self.active_widgets:
                self.create_dynamic_widget(wid, w_data)
            else:
                self.update_dynamic_widget(wid, w_data)

    def create_dynamic_widget(self, wid, w_data):
        w_type = w_data.get('type')
        x = w_data.get('x', 0.5)
        y = w_data.get('y', 0.5)

        print(f"✨ A criar {w_type} ID: {wid} nas coordenadas X:{x:.2f} Y:{y:.2f}")

        widget_info = {'type': w_type, 'update_job': None}

        if w_type == 'clock':
            frame = ctk.CTkFrame(self.root, fg_color="#1a1a1a", corner_radius=10, width=250, height=120)
            lbl_main = ctk.CTkLabel(frame, text="00:00", font=("Roboto", 40, "bold"), text_color="white")
            lbl_main.place(relx=0.5, rely=0.4, anchor="center")
            lbl_sub = ctk.CTkLabel(frame, text="", font=("Roboto", 14), text_color="gray")
            lbl_sub.place(relx=0.5, rely=0.75, anchor="center")
            
            widget_info.update({'frame': frame, 'lbl_main': lbl_main, 'lbl_sub': lbl_sub, 'tz': w_data.get('timezone', 'Local')})

        elif w_type == 'weather':
            frame = ctk.CTkFrame(self.root, fg_color="#2980b9", corner_radius=10, width=200, height=120)
            lbl_main = ctk.CTkLabel(frame, text="--°C", font=("Roboto", 32, "bold"), text_color="white")
            lbl_main.place(relx=0.5, rely=0.4, anchor="center")
            lbl_sub = ctk.CTkLabel(frame, text="", font=("Roboto", 14), text_color="#e0e0e0")
            lbl_sub.place(relx=0.5, rely=0.75, anchor="center")

            widget_info.update({'frame': frame, 'lbl_main': lbl_main, 'lbl_sub': lbl_sub, 'loc': w_data.get('location', 'Lisboa, PT')})

        elif w_type == 'gas':
            frame = ctk.CTkFrame(self.root, fg_color="#27ae60", corner_radius=10, width=220, height=80)
            lbl_main = ctk.CTkLabel(frame, text="✅ GÁS: OK", font=("Roboto", 18, "bold"), text_color="white")
            lbl_main.place(relx=0.5, rely=0.5, anchor="center")
            widget_info.update({'frame': frame})
        else:
            return

        # Guarda na nossa lista de widgets ativos
        self.active_widgets[wid] = widget_info
        
        # Coloca o bloco no ecrã 
        self.active_widgets[wid]['frame'].place(relx=x, rely=y, anchor="nw")

        # Inicia a "magia" interior do widget (horas reais ou API do clima)
        if w_type == 'clock':
            self.tick_clock(wid)
        elif w_type == 'weather':
            self.fetch_weather_thread(wid)

    def update_dynamic_widget(self, wid, w_data):
        w = self.active_widgets[wid]
        w_type = w['type']
        
        # Move o bloco no ecrã em tempo real
        w['frame'].place(relx=w_data.get('x', 0.5), rely=w_data.get('y', 0.5), anchor="nw")

        # Se as definições mudaram na app, atualiza
        if w_type == 'clock':
            w['tz'] = w_data.get('timezone', 'Local')
        elif w_type == 'weather':
            new_loc = w_data.get('location', 'Lisboa, PT')
            if w['loc'] != new_loc:
                w['loc'] = new_loc
                w['lbl_main'].configure(text="--°C") # Faz Reset visual
                self.fetch_weather_thread(wid) # Pede a nova cidade

    def destroy_widget(self, wid):
        w = self.active_widgets.get(wid)
        if w:
            if w.get('update_job'):
                self.root.after_cancel(w['update_job'])
            w['frame'].destroy()
            del self.active_widgets[wid]
            print(f"🗑️ Widget Apagado: {wid}")

    # ==========================================
    # LÓGICA DO RELÓGIO (COM FUSOS HORÁRIOS)
    # ==========================================
    def tick_clock(self, wid):
        if wid not in self.active_widgets: return
        w = self.active_widgets[wid]
        
        tz_string = w.get('tz', 'Local')
        
        if tz_string == 'Local':
            now = datetime.now()
            display_name = "Hora Local"
        else:
            try:
                tz = pytz.timezone(tz_string)
                now = datetime.now(tz)
                display_name = tz_string.split('/')[-1].replace('_', ' ') # "America/New_York" -> "New York"
            except:
                now = datetime.now()
                display_name = "Erro Fuso"

        w['lbl_main'].configure(text=now.strftime("%H:%M"))
        w['lbl_sub'].configure(text=display_name)
        
        w['update_job'] = self.root.after(1000, lambda: self.tick_clock(wid))

    # ==========================================
    # LÓGICA DO CLIMA (COORDENADAS GPS + METEO)
    # ==========================================
    def fetch_weather_thread(self, wid):
        if wid not in self.active_widgets: return
        threading.Thread(target=self._fetch_weather_logic, args=(wid,), daemon=True).start()

    def _fetch_weather_logic(self, wid):
        w = self.active_widgets.get(wid)
        if not w: return

        location = w.get('loc', 'Lisboa')
        print(f"☁️ A pesquisar clima para: {location}")
        
        try:
            # 1. API Nominatim: Transforma "Nova Iorque" em Latitude e Longitude (GPS)
            geo_url = f"https://nominatim.openstreetmap.org/search?q={location}&format=json&limit=1"
            headers = {'User-Agent': 'VitraeView-SmartWindow'}
            geo_res = requests.get(geo_url, headers=headers, timeout=5).json()
            
            if geo_res:
                lat = geo_res[0]['lat']
                lon = geo_res[0]['lon']
                
                # 2. API Open-Meteo: Vai buscar a temperatura para esse GPS
                meteo_url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=true"
                meteo_res = requests.get(meteo_url, timeout=5).json()
                temp = meteo_res['current_weather']['temperature']
                
                self.root.after(0, lambda: w['lbl_main'].configure(text=f"{temp}°C"))
                self.root.after(0, lambda: w['lbl_sub'].configure(text=location))
            else:
                self.root.after(0, lambda: w['lbl_main'].configure(text="? °C"))
                self.root.after(0, lambda: w['lbl_sub'].configure(text="Local Inválido"))
        except Exception as e:
            print(f"⚠️ Erro ao buscar clima para {location}: {e}")

        # Atualiza o clima a cada 15 minutos para não bloquear a API
        if wid in self.active_widgets:
             self.active_widgets[wid]['update_job'] = self.root.after(900000, lambda: self.fetch_weather_thread(wid))

    # ==========================================
    # LÓGICA DO SENSOR DE GÁS
    # ==========================================
    def check_gas_sensor(self):
        gas_detected = GPIO.input(GAS_SENSOR_PIN) == GPIO.LOW
        if gas_detected and not self.alert_active:
            self.activate_alert()
            if self.db:
                self.db.collection('windows').document(self.device_id).set({'gas': 1}, merge=True)
        elif not gas_detected and self.alert_active:
            self.deactivate_alert()
            if self.db:
                self.db.collection('windows').document(self.device_id).set({'gas': 0}, merge=True)
        self.root.after(1000, self.check_gas_sensor)

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