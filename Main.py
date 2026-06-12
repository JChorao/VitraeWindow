import customtkinter as ctk
import requests
import threading
import time
import os
import sys
import pytz
import serial
import subprocess
from datetime import datetime, timedelta

# --- IMPORTAÇÕES FIREBASE ---
import firebase_admin
from firebase_admin import credentials, firestore

# --- MOCK PARA GPIO ---
try:
    import RPi.GPIO as GPIO
    ON_RASPBERRY = True
except (ImportError, RuntimeError):
    ON_RASPBERRY = False
    print("⚠️ RPi.GPIO não detetado ou sem permissões. MOCK GPIO ATIVADO.")
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

# --- CONFIGURAÇÃO GOOGLE CALENDAR ---
GOOGLE_CLIENT_ID = "555974802803-4na1f4nbj856kmqkfc2hv5808fc17kmk.apps.googleusercontent.com"

# CORREÇÃO DE SEGURANÇA: Ler o Secret de um ficheiro local
def load_client_secret():
    try:
        with open('client_secret.txt', 'r') as f:
            return f.read().strip()
    except Exception as e:
        print("❌ ERRO: Ficheiro 'client_secret.txt' não encontrado!")
        print("Por favor, crie este ficheiro ao lado do Main.py e cole lá o seu Segredo do Cliente.")
        sys.exit(1)

GOOGLE_CLIENT_SECRET = load_client_secret()

# --- CONFIGURAÇÃO VISUAL ---
ctk.set_appearance_mode("light")
ctk.set_default_color_theme("blue")
ctk.set_widget_scaling(1.0) # <-- DESATIVA O ZOOM SECRETO DO WINDOWS
ctk.set_window_scaling(1.0) # <-- DESATIVA O ZOOM SECRETO DO WINDOWS
GAS_SENSOR_PIN = 26 

class VitraeDashboard:
    def __init__(self, root):
        self.root = root
        self.root.title("VitraeView - Produção")
        
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        self.screen_width = self.root.winfo_screenwidth()
        self.screen_height = self.root.winfo_screenheight()
        self.root.geometry(f"{self.screen_width}x{self.screen_height}")
        
        self.bg_color = "#ffffff"
        self.root.configure(fg_color=self.bg_color)
        
        self.db = None
        self.device_id = None
        self.alert_active = False

        self.tela_ativa = True
        self.override_manual = False
        self.ser_radar = None
        self.radar_buffer = b''

        self.active_widgets = {}
        self.current_layout_data = {} 
        self.layout_watch = None 

        print("🔄 A Iniciar Sistema VitraeView...")
        self.setup_firebase()
        self.validate_device()
        self.report_estado_to_firebase(True)
        self.report_resolution_to_firebase()

        self.start_layout_listener()
        
        GPIO.setwarnings(False)
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(GAS_SENSOR_PIN, GPIO.IN)
        self.check_gas_sensor()

        self.setup_radar()

        self.root.bind_all('9', lambda event: self.alternar_tela_manual())

        self.resize_timer = None
        self.root.bind("<Configure>", self.on_window_resize)

    # ==========================================
    # LÓGICA DO SENSOR DE PRESENÇA E INTERFACE
    # ==========================================
    def setup_radar(self):
        try:
            self.ser_radar = serial.Serial('/dev/ttyS0', 256000, timeout=0.1)
            threading.Thread(target=self.rotina_presenca_radar, daemon=True).start()
            print("📡 Módulo de Radar HLK-LD2450 Iniciado com Sucesso!")
        except Exception as e:
            print(f"⚠️ Aviso: Não foi possível iniciar o Radar (Serial: {e})")

    def controlar_widgets(self, estado):
        if estado:
            self.tela_ativa = True
            self.root.configure(fg_color=self.bg_color) 
            print("🖥️ [Interface] Presença detetada! A criar widgets do zero...")
            if self.current_layout_data:
                self.apply_dynamic_layout(self.current_layout_data)
            self.report_estado_to_firebase(True)
        else:
            self.tela_ativa = False
            self.root.configure(fg_color="#FFFFFF")
            print("🖥️ [Interface] Divisão vazia! A eliminar todos os widgets...")
            self.limpar_todos_widgets()
            self.report_estado_to_firebase(False)

    def limpar_todos_widgets(self):
        active_ids = list(self.active_widgets.keys())
        for wid in active_ids:
            self.destroy_widget(wid)

    def alternar_tela_manual(self):
        if self.tela_ativa:
            self.controlar_widgets(0)
            self.override_manual = True
            self.root.after(10000, self.limpar_override) 
        else:
            self.controlar_widgets(1)
            self.override_manual = True
            self.root.after(5000, self.limpar_override)
            
    def limpar_override(self):
        self.override_manual = False

    def rotina_presenca_radar(self):
        ultimo_momento_com_presenca = time.time()
        tempo_limite_vazio = 5  

        while self.ser_radar and self.ser_radar.is_open:
            if self.ser_radar.in_waiting > 0:
                self.radar_buffer += self.ser_radar.read(self.ser_radar.in_waiting)
                if self.override_manual:
                    self.radar_buffer = b'' 
                    time.sleep(0.5)
                    continue

                idx = self.radar_buffer.find(b'\xaa\xff')
                if idx != -1:
                    if len(self.radar_buffer) >= idx + 30:
                        frame = self.radar_buffer[idx : idx+30]
                        self.radar_buffer = self.radar_buffer[idx+30 :]
                        presenca_detectada = False
                        
                        for i in range(3):
                            inicio = 4 + (i * 8)
                            bytes_alvo = frame[inicio : inicio+8]
                            if len(bytes_alvo) == 8:
                                y = bytes_alvo[2] + ((bytes_alvo[3] & 0x7F) << 8)
                                vel = bytes_alvo[4] + ((bytes_alvo[5] & 0x7F) << 8)
                                if bytes_alvo[5] & 0x80: vel = -vel
                                if 400 < y < 4000 and vel != 0:
                                    presenca_detectada = True
                                    break 
                        
                        if presenca_detectada:
                            ultimo_momento_com_presenca = time.time()
                            if not self.tela_ativa:
                                self.root.after(0, self.controlar_widgets, 1)
                        else:
                            if self.tela_ativa and (time.time() - ultimo_momento_com_presenca > tempo_limite_vazio):
                                self.root.after(0, self.controlar_widgets, 0)
            time.sleep(0.05)

    # ==========================================
    # CÓDIGO DA INTERFACE E FIREBASE
    # ==========================================
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

    def report_resolution_to_firebase(self):
        if self.db and self.device_id:
            try:
                self.db.collection('windows').document(self.device_id).set({
                    'resW': self.screen_width,
                    'resH': self.screen_height
                }, merge=True)
            except Exception:
                pass

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

    def start_layout_listener(self):
        doc_ref = self.db.collection('windows').document(self.device_id)
        
        def on_snapshot(doc_snapshot, changes, read_time):
            try:
                for doc in doc_snapshot:
                    if doc.exists:
                        data = doc.to_dict()
                        self.root.after(0, self.apply_dynamic_layout, data)
            except Exception as e:
                print(f"❌ [Listener] Erro no snapshot: {e}. A reiniciar em 2s...")
                try:
                    if self.layout_watch:
                        self.layout_watch.unsubscribe()
                except Exception:
                    pass
                self.root.after(2000, self.start_layout_listener)

        self.layout_watch = doc_ref.on_snapshot(on_snapshot)
        print("👂 Listener de layout ativo.")

    def apply_dynamic_layout(self, data):
        self.current_layout_data = data
        if not self.tela_ativa: return

        firebase_widgets = data.get('widgets', {})
        active_ids = list(self.active_widgets.keys())
        for wid in active_ids:
            if wid not in firebase_widgets:
                self.destroy_widget(wid)

        for wid, w_data in firebase_widgets.items():
            if wid not in self.active_widgets:
                self.create_dynamic_widget(wid, w_data)
            else:
                self.update_dynamic_widget(wid, w_data)

    def create_dynamic_widget(self, wid, w_data):
        w_type = w_data.get('type')
        x = w_data.get('x', 0.5)
        y = w_data.get('y', 0.5)
        scale = w_data.get('scale', 1.0) # Lê logo a escala na criação

        widget_info = {'type': w_type, 'update_job': None, 'update_job_calendar': None, 'scale': scale}

        if w_type == 'clock':
            w_w, w_h = 250, 120
            frame = ctk.CTkFrame(self.root, fg_color="#1a1a1a", corner_radius=10, width=int(w_w * scale), height=int(w_h * scale))
            frame.pack_propagate(False) # IMPEDE O WIDGET DE TRANSBORDAR
            lbl_main = ctk.CTkLabel(frame, text="00:00", font=("Roboto", int(40 * scale), "bold"), text_color="white")
            lbl_main.place(relx=0.5, rely=0.4, anchor="center")
            lbl_sub = ctk.CTkLabel(frame, text="", font=("Roboto", int(14 * scale)), text_color="gray")
            lbl_sub.place(relx=0.5, rely=0.75, anchor="center")
            
            widget_info.update({'frame': frame, 'lbl_main': lbl_main, 'lbl_sub': lbl_sub, 'tz': w_data.get('timezone', 'Local')})

        elif w_type == 'weather':
            w_w, w_h = 200, 120
            frame = ctk.CTkFrame(self.root, fg_color="#2980b9", corner_radius=10, width=int(w_w * scale), height=int(w_h * scale))
            frame.pack_propagate(False) # IMPEDE O WIDGET DE TRANSBORDAR
            lbl_main = ctk.CTkLabel(frame, text="--°C", font=("Roboto", int(32 * scale), "bold"), text_color="white")
            lbl_main.place(relx=0.5, rely=0.4, anchor="center")
            lbl_sub = ctk.CTkLabel(frame, text="", font=("Roboto", int(14 * scale)), text_color="#e0e0e0")
            lbl_sub.place(relx=0.5, rely=0.75, anchor="center")

            widget_info.update({'frame': frame, 'lbl_main': lbl_main, 'lbl_sub': lbl_sub, 'loc': w_data.get('location', 'Lisboa, PT')})

        elif w_type == 'gas':
            w_w, w_h = 220, 80
            frame = ctk.CTkFrame(self.root, fg_color="#27ae60", corner_radius=10, width=int(w_w * scale), height=int(w_h * scale))
            frame.pack_propagate(False) # IMPEDE O WIDGET DE TRANSBORDAR
            lbl_main = ctk.CTkLabel(frame, text="✅ GÁS: OK", font=("Roboto", int(18 * scale), "bold"), text_color="white")
            lbl_main.place(relx=0.5, rely=0.5, anchor="center")
            widget_info.update({'frame': frame, 'lbl_main': lbl_main})

        elif w_type == 'calendar':
            w_w, w_h = 310, 250
            bg_color = w_data.get('bg_color', '#1a1a1a')
            title_color = w_data.get('title_color', '#ffffff')
            time_color = w_data.get('time_color', '#3498db')
            view_mode = w_data.get('view_mode', 'Semana')

            titulos_agenda = {"Dia": "Agenda do Dia", "Semana": "Agenda da Semana", "Mês": "Agenda do Mês"}
            texto_titulo = titulos_agenda.get(view_mode, f"Agenda da {view_mode}")

            frame = ctk.CTkFrame(self.root, fg_color=bg_color, corner_radius=10, width=int(w_w * scale), height=int(w_h * scale))
            frame.pack_propagate(False) # A MAGIA! Impede a caixa cinzenta principal de esticar
            lbl_title = ctk.CTkLabel(frame, text=texto_titulo, font=("Roboto", int(18 * scale), "bold"), text_color=title_color)
            lbl_title.place(relx=0.5, rely=0.12, anchor="center")

            events_frame = ctk.CTkFrame(frame, fg_color="transparent", width=int(280 * scale), height=int(180 * scale))
            events_frame.pack_propagate(False) # A MAGIA! Impede o texto longo de empurrar as bordas
            events_frame.place(relx=0.5, rely=0.58, anchor="center")

            widget_info.update({
                'frame': frame, 
                'events_frame': events_frame,
                'lbl_title': lbl_title,  
                'events': [],
                'google_auth_code': w_data.get('google_auth_code'),
                'bg_color': bg_color,
                'title_color': title_color,
                'time_color': time_color,
                'view_mode': view_mode
            })
            self._render_calendar_events(events_frame, [], title_color, time_color, scale)
        else:
            return

        self.active_widgets[wid] = widget_info
        
        # --- LÊ A LARGURA REAL DA JANELA NESTE EXATO MILISSEGUNDO ---
        win_w = self.root.winfo_width()
        win_h = self.root.winfo_height()
        # Prevenção caso o ecrã ainda não tenha acabado de desenhar
        if win_w < 100: win_w = self.screen_width
        if win_h < 100: win_h = self.screen_height
        
        max_x = max(0.0, 1.0 - ((w_w * scale) / win_w))
        max_y = max(0.0, 1.0 - ((w_h * scale) / win_h))
        
        final_x = min(max(x, 0.0), max_x)
        final_y = min(max(y, 0.0), max_y)
        
        self.active_widgets[wid]['frame'].place(relx=final_x, rely=final_y, anchor="nw")

        if w_type == 'clock':
            self.tick_clock(wid)
        elif w_type == 'weather':
            self.fetch_weather_thread(wid)
        elif w_type == 'calendar':
            self.fetch_calendar_thread(wid)

    def update_dynamic_widget(self, wid, w_data):
        w = self.active_widgets[wid]
        w_type = w['type']
        
        novo_scale = w_data.get('scale', 1.0)
        old_scale = w.get('scale', 1.0)
        
        if w_type == 'clock': w_w, w_h = 250, 120
        elif w_type == 'weather': w_w, w_h = 200, 120
        elif w_type == 'gas': w_w, w_h = 220, 80
        elif w_type == 'calendar': w_w, w_h = 310, 250
        else: w_w, w_h = 200, 200

        # --- APLICA A ESCALA AOS TAMANHOS DE TODOS OS WIDGETS ---
        if old_scale != novo_scale:
            w['scale'] = novo_scale
            w['frame'].configure(width=int(w_w * novo_scale), height=int(w_h * novo_scale))
            
            if w_type == 'clock':
                w['lbl_main'].configure(font=("Roboto", int(40 * novo_scale), "bold"))
                w['lbl_sub'].configure(font=("Roboto", int(14 * novo_scale)))
            elif w_type == 'weather':
                w['lbl_main'].configure(font=("Roboto", int(32 * novo_scale), "bold"))
                w['lbl_sub'].configure(font=("Roboto", int(14 * novo_scale)))
            elif w_type == 'gas':
                w['lbl_main'].configure(font=("Roboto", int(18 * novo_scale), "bold"))
            elif w_type == 'calendar':
                w['events_frame'].configure(width=int(280 * novo_scale), height=int(180 * novo_scale))
                w['lbl_title'].configure(font=("Roboto", int(18 * novo_scale), "bold"))
                self._render_calendar_events(w['events_frame'], w.get('events', []), w.get('title_color', '#ffffff'), w.get('time_color', '#3498db'), novo_scale)

        # --- ATUALIZA AS RESTANTES DEFINIÇÕES ---
        if w_type == 'clock':
            w['tz'] = w_data.get('timezone', 'Local')
        elif w_type == 'weather':
            new_loc = w_data.get('location', 'Lisboa, PT')
            if w['loc'] != new_loc:
                w['loc'] = new_loc
                w['lbl_main'].configure(text="--°C")
                self.fetch_weather_thread(wid)
                
        elif w_type == 'calendar':
            if 'google_auth_code' in w_data:
                w['google_auth_code'] = w_data['google_auth_code']
                self.fetch_calendar_thread(wid)

            novo_bg = w_data.get('bg_color', '#1a1a1a')
            novo_title = w_data.get('title_color', '#ffffff')
            novo_time = w_data.get('time_color', '#3498db')
            novo_view = w_data.get('view_mode', 'Semana')

            if w.get('bg_color') != novo_bg:
                w['bg_color'] = novo_bg
                w['frame'].configure(fg_color=novo_bg)
            
            if w.get('title_color') != novo_title or w.get('time_color') != novo_time or w.get('view_mode') != novo_view:
                old_view = w.get('view_mode') # Guarda o modo antigo
                
                w['title_color'] = novo_title
                w['time_color'] = novo_time
                w['view_mode'] = novo_view
                
                titulos_agenda = {"Dia": "Agenda do Dia", "Semana": "Agenda da Semana", "Mês": "Agenda do Mês"}
                texto_titulo = titulos_agenda.get(novo_view, f"Agenda da {novo_view}")
                
                w['lbl_title'].configure(text=texto_titulo, text_color=novo_title)
                self._render_calendar_events(w['events_frame'], w.get('events', []), novo_title, novo_time, novo_scale)

                # --- A MAGIA: Se mudares o filtro na App, ele vai imediatamente à Google buscar os novos dados! ---
                if old_view != novo_view:
                    self.fetch_calendar_thread(wid)
                
                w['lbl_title'].configure(text=texto_titulo, text_color=novo_title)
                self._render_calendar_events(w['events_frame'], w.get('events', []), novo_title, novo_time, novo_scale)
        
        # --- POSICIONAMENTO COM BLINDAGEM PERFEITA ---
        win_w = self.root.winfo_width()
        win_h = self.root.winfo_height()
        if win_w < 100: win_w = self.screen_width
        if win_h < 100: win_h = self.screen_height

        max_x = max(0.0, 1.0 - ((w_w * novo_scale) / win_w))
        max_y = max(0.0, 1.0 - ((w_h * novo_scale) / win_h))
        
        final_x = min(max(w_data.get('x', 0.5), 0.0), max_x)
        final_y = min(max(w_data.get('y', 0.5), 0.0), max_y)
        
        w['frame'].place(relx=final_x, rely=final_y, anchor="nw")

    # ==========================================
    # MOTOR AUTÓNOMO DO GOOGLE CALENDAR
    # ==========================================
    def fetch_calendar_thread(self, wid):
        if wid not in self.active_widgets: return
        threading.Thread(target=self._fetch_calendar_logic, args=(wid,), daemon=True).start()

    def _fetch_calendar_logic(self, wid):
        w = self.active_widgets.get(wid)
        if not w: return

        refresh_token = self._load_refresh_token()
        auth_code = w.get('google_auth_code')

        # 1. SE TEM CÓDIGO NOVO (Vindo do botão "Forçar Sincronizar" da app), PRIORIZA-O
        if auth_code:
            print("🔑 Novo código recebido da App! A trocar por Refresh Token...")
            novo_refresh_token = self._exchange_code_for_token(auth_code)
            if novo_refresh_token:
                self._save_refresh_token(novo_refresh_token)
                refresh_token = novo_refresh_token # Atualiza a variável para usar já a seguir
                print("✅ Novo Refresh Token guardado com sucesso!")
                if self.db:
                    try:
                        self.db.collection('windows').document(self.device_id).update({
                            f'widgets.{wid}.google_auth_code': firestore.DELETE_FIELD
                        })
                    except Exception as e:
                        print(f"⚠️ Erro ao apagar auth_code da firebase: {e}")
            else:
                print("❌ Erro ao trocar o código. O código pode já ter sido usado.")
            w.pop('google_auth_code', None) # Limpa da memória local

        # 2. SE NÃO TEM TOKEN DE TODO, AGUARDA.
        if not refresh_token:
            self._agendar_proxima_verificacao(wid, w, 10000)
            return

        # 3. SE TEMOS REFRESH TOKEN, BUSCAMOS AS TAREFAS
        try:
            access_token = self._get_access_token(refresh_token)
            if access_token:
                
                # --- NOVA LÓGICA DE DATAS BLINDADA ---
                view_mode = w.get('view_mode', 'Semana')
                now = datetime.utcnow()
                # Força o início a ser às 00:00h de hoje, para apanhar as tarefas matinais e de "Dia todo"
                hoje_meia_noite = now.replace(hour=0, minute=0, second=0, microsecond=0)
                
                if view_mode == 'Dia':
                    time_max = hoje_meia_noite + timedelta(days=1)
                elif view_mode == 'Mês':
                    time_max = hoje_meia_noite + timedelta(days=30)
                else: # Semana (default)
                    time_max = hoje_meia_noite + timedelta(days=7)

                now_str = hoje_meia_noite.isoformat() + 'Z'
                time_max_str = time_max.isoformat() + 'Z'
                
                url = f"https://www.googleapis.com/calendar/v3/calendars/primary/events?timeMin={now_str}&timeMax={time_max_str}&singleEvents=true&orderBy=startTime"
                headers = {'Authorization': f'Bearer {access_token}'}
                res = requests.get(url, headers=headers, timeout=10)
                
                if res.status_code == 200:
                    dados = res.json()
                    events_list = []
                    for item in dados.get('items', []):
                        start_str = item['start'].get('dateTime', item['start'].get('date'))
                        if 'T' in start_str:
                            data_part = start_str.split('T')[0].split('-')
                            hora = start_str.split('T')[1][:5]
                            dia = f"{data_part[2]}/{data_part[1]}"
                        else:
                            data_part = start_str.split('-')
                            dia = f"{data_part[2]}/{data_part[1]}"
                            hora = "Dia todo"
                        events_list.append({"day": dia, "time": hora, "title": item.get('summary', 'Sem Título')})

                    # OTIMIZAÇÃO: Força SEMPRE o desenho e passa a escala correta!
                    w['events'] = events_list
                    self.root.after(0, lambda: self._render_calendar_events(
                        w['events_frame'], 
                        events_list,
                        w.get('title_color', '#ffffff'), 
                        w.get('time_color', '#3498db'),
                        w.get('scale', 1.0)
                    ))
                else:
                    print(f"⚠️ Erro API Calendar ({res.status_code}): {res.text}")
            else:
                # SE O TOKEN DE ACESSO FALHOU, O REFRESH TOKEN FOI REVOGADO/É ZOMBIE. VAMOS APAGÁ-LO.
                print("⚠️ Token de Acesso falhou. O Refresh Token expirou ou a chave mudou. A apagar ficheiro...")
                if os.path.exists('calendar_token.txt'):
                    os.remove('calendar_token.txt')
                
        except Exception as e:
            print(f"⚠️ Erro crítico no Google Calendar: {e}")

        # O RELÓGIO DA JANELA: Repete a extração daqui a 1 MINUTO (60000 ms)
        self._agendar_proxima_verificacao(wid, w, 60000)

    def _agendar_proxima_verificacao(self, wid, w, delay_ms):
        def _executar():
            if wid in self.active_widgets:
                if w.get('update_job_calendar'): 
                    self.root.after_cancel(w['update_job_calendar'])
                w['update_job_calendar'] = self.root.after(delay_ms, lambda id=wid: self.fetch_calendar_thread(id))
        self.root.after(0, _executar)

    def _exchange_code_for_token(self, auth_code):
        url = "https://oauth2.googleapis.com/token"
        payload = {
            'code': auth_code,
            'client_id': GOOGLE_CLIENT_ID,
            'client_secret': GOOGLE_CLIENT_SECRET,
            'grant_type': 'authorization_code',
            'redirect_uri': '' 
        }
        try:
            res = requests.post(url, data=payload, timeout=10).json()
            return res.get('refresh_token')
        except:
            return None

    def _get_access_token(self, refresh_token):
        url = "https://oauth2.googleapis.com/token"
        payload = {
            'client_id': GOOGLE_CLIENT_ID,
            'client_secret': GOOGLE_CLIENT_SECRET,
            'refresh_token': refresh_token,
            'grant_type': 'refresh_token'
        }
        try:
            res = requests.post(url, data=payload, timeout=10).json()
            return res.get('access_token')
        except:
            return None

    def _save_refresh_token(self, token):
        try:
            with open('calendar_token.txt', 'w') as f:
                f.write(token)
        except Exception as e:
            print("⚠️ Erro ao guardar token:", e)

    def _load_refresh_token(self):
        if os.path.exists('calendar_token.txt'):
            try:
                with open('calendar_token.txt', 'r') as f:
                    return f.read().strip()
            except:
                pass
        return None

    # ==========================================
    # OUTRAS FUNÇÕES DOS WIDGETS
    # ==========================================
    def _render_calendar_events(self, parent_frame, events_list, title_color="#ffffff", time_color="#3498db", scale=1.0):
        for widget in parent_frame.winfo_children():
            widget.destroy()

        # Calcula o tamanho da letra com base na escala (int para evitar erros do Tkinter)
        font_empty = int(13 * scale)
        font_time = int(11 * scale)
        font_event = int(12 * scale)

        if not events_list:
            lbl_empty = ctk.CTkLabel(parent_frame, text="Sem tarefas agendadas.", font=("Roboto", font_empty), text_color=title_color)
            lbl_empty.pack(expand=True, pady=int(40 * scale))
            return

        max_items = 4
        for event in events_list[:max_items]:
            hora = event.get('time', '--:--')
            dia = event.get('day', '')  
            titulo = event.get('title', 'Sem Título')

            string_tempo = f"{dia} {hora}".strip() if dia else hora

            event_row = ctk.CTkFrame(parent_frame, fg_color="transparent")
            event_row.pack(fill="x", pady=int(4 * scale), padx=int(2 * scale))

            lbl_time = ctk.CTkLabel(event_row, text=string_tempo, font=("Roboto", font_time, "bold"), text_color=time_color)
            lbl_time.pack(side="left", padx=int(8 * scale), pady=int(5 * scale))

            lbl_title = ctk.CTkLabel(event_row, text=titulo, font=("Roboto", font_event), text_color=title_color, anchor="w")
            lbl_title.pack(side="left", fill="x", expand=True, padx=int(4 * scale), pady=int(5 * scale))

    def destroy_widget(self, wid):
        w = self.active_widgets.get(wid)
        if w:
            if w.get('update_job'):
                self.root.after_cancel(w['update_job'])
            if w.get('update_job_calendar'):
                self.root.after_cancel(w['update_job_calendar'])
            w['frame'].destroy()
            del self.active_widgets[wid]

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
                display_name = tz_string.split('/')[-1].replace('_', ' ')
            except Exception as e:
                now = datetime.now()
                display_name = "Hora Local"

        w['lbl_main'].configure(text=now.strftime("%H:%M"))
        w['lbl_sub'].configure(text=display_name)
        
        w['update_job'] = self.root.after(1000, lambda id=wid: self.tick_clock(id))

    def fetch_weather_thread(self, wid):
        if wid not in self.active_widgets: return
        threading.Thread(target=self._fetch_weather_logic, args=(wid,), daemon=True).start()

    def _fetch_weather_logic(self, wid):
        w = self.active_widgets.get(wid)
        if not w: return

        location = w.get('loc', 'Lisboa')
        
        try:
            geo_url = f"https://nominatim.openstreetmap.org/search?q={location}&format=json&limit=1"
            headers = {'User-Agent': 'VitraeView-SmartWindow'}
            geo_res = requests.get(geo_url, headers=headers, timeout=10).json() 
            
            if geo_res:
                lat = geo_res[0]['lat']
                lon = geo_res[0]['lon']
                
                meteo_url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=true"
                meteo_res = requests.get(meteo_url, timeout=10).json() 
                temp = meteo_res['current_weather']['temperature']
                
                self.root.after(0, lambda: w['lbl_main'].configure(text=f"{temp}°C"))
                self.root.after(0, lambda: w['lbl_sub'].configure(text=location))
            else:
                self.root.after(0, lambda: w['lbl_main'].configure(text="? °C"))
                self.root.after(0, lambda: w['lbl_sub'].configure(text="Local Inválido"))
        except Exception as e:
            pass

        if wid in self.active_widgets:
             self.active_widgets[wid]['update_job'] = self.root.after(900000, lambda id=wid: self.fetch_weather_thread(id))

    def check_gas_sensor(self):
        sensor_value = GPIO.input(GAS_SENSOR_PIN)
        gas_detected = (sensor_value == GPIO.LOW)
        
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
        
        if not self.tela_ativa:
            self.controlar_widgets(1)

    def deactivate_alert(self):
        self.alert_active = False
        if hasattr(self, 'alert_frame'): self.alert_frame.destroy()

    def on_closing(self):
        print("\nA encerrar o sistema e a limpar conexões...")
        if hasattr(self, 'ser_radar') and self.ser_radar:
            self.ser_radar.close()
        try:
            if self.db and self.device_id:
                self.db.collection('windows').document(self.device_id).set(
                    {'estado': 'Inativa'}, merge=True)
        except Exception:
            pass
        self.root.destroy()

    def report_estado_to_firebase(self, ativo):
        if self.db and self.device_id:
            def _enviar():
                try:
                    self.db.collection('windows').document(self.device_id).set(
                        {'estado': 'Ativa' if ativo else 'Inativa'}, merge=True)
                except Exception:
                    pass
            threading.Thread(target=_enviar, daemon=True).start()

if __name__ == "__main__":
    root = ctk.CTk()
    app = VitraeDashboard(root)
    root.mainloop()