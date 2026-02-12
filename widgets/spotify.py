import tkinter as tk
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import qrcode
from PIL import Image, ImageTk
import threading
from server.auth_server import run_server_thread, wait_for_auth_code
from utils.network import generate_self_signed_cert

# Credenciais (Certifica-te que o e-mail está em 'User Management' no Dashboard do Spotify)
SPOTIPY_CLIENT_ID = '98292ab34200413ead2790c21a2788f6'
SPOTIPY_CLIENT_SECRET = '72ca31c9c22e420eacca1679284d753b'

class SpotifyWidget:
    def __init__(self, root, row, col, local_ip):
        self.root = root
        self.local_ip = local_ip
        # URI HTTPS obrigatória
        self.redirect_uri = f'https://{local_ip}:8888/callback'
        self.sp = None
        self.auth_manager = None
        
        self.frame = tk.Frame(self.root, bg="white", highlightbackground="#e0e0e0", highlightthickness=1)
        self.frame.grid(row=row, column=col, sticky="nsew", padx=20, pady=20)
        
        tk.Label(self.frame, text="Spotify", font=("Arial", 14, "bold"), bg="white", fg="#1DB954").pack(pady=5)
        self.status_label = tk.Label(self.frame, text="A iniciar...", font=("Arial", 9, "italic"), bg="white", fg="gray")
        self.status_label.pack()
        self.track_label = tk.Label(self.frame, text="", font=("Arial", 11, "bold"), bg="white", fg="#2d2d2d", wraplength=200)
        self.track_label.pack(pady=10)
        self.qr_label = tk.Label(self.frame, bg="white")
        self.qr_label.pack(pady=5)
        
        self._start_auth_server()

    def _start_auth_server(self):
        cert_file, key_file = generate_self_signed_cert()
        run_server_thread(cert_file, key_file, port=8888)
        self.root.after(1000, self._show_qr_code)

    def _show_qr_code(self):
        scope = "user-read-currently-playing user-read-playback-state user-read-email"
        self.auth_manager = SpotifyOAuth(
            client_id=SPOTIPY_CLIENT_ID, 
            client_secret=SPOTIPY_CLIENT_SECRET,
            redirect_uri=self.redirect_uri, 
            scope=scope, 
            cache_path=".spotify_cache"
        )
        
        token_info = self.auth_manager.get_cached_token()
        if token_info:
            self._on_auth_success(token_info)
            return
        
        auth_url = self.auth_manager.get_authorize_url()
        qr = qrcode.QRCode(version=1, box_size=3, border=2)
        qr.add_data(auth_url)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white").resize((90, 90))
        
        photo = ImageTk.PhotoImage(img)
        self.qr_label.config(image=photo)
        self.qr_label.image = photo
        
        threading.Thread(target=self._wait_for_auth, daemon=True).start()

    def _on_auth_success(self, token_info):
        self.sp = spotipy.Spotify(auth=token_info['access_token'])
        self.qr_label.pack_forget()
        self.status_label.config(text="Ligado", fg="#1DB954")
        self._update_spotify_info()

    def _update_spotify_info(self):
        if self.sp:
            try:
                current = self.sp.current_playback()
                if current and current['is_playing']:
                    self.track_label.config(text=f"🎵 {current['item']['name']}\n👤 {current['item']['artists'][0]['name']}")
                else:
                    self.track_label.config(text="⏸ Pausado", fg="gray")
            except: pass
        self.root.after(3000, self._update_spotify_info)

    def _wait_for_auth(self):
        code = wait_for_auth_code(timeout=300)
        if code:
            # Troca código por token e cria .spotify_cache
            token_info = self.auth_manager.get_access_token(code, as_dict=True)
            self.root.after(0, lambda: self._on_auth_success(token_info))