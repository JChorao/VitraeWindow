"""Widget do Spotify com autenticação via QR code"""

import tkinter as tk
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import qrcode
from PIL import Image, ImageTk
import threading
import webbrowser
import subprocess
import sys
import os
from server.auth_server import run_server_thread, wait_for_auth_code
from utils.network import generate_self_signed_cert

# Configuração do Spotify
SPOTIPY_CLIENT_ID = '98292ab34200413ead2790c21a2788f6'
SPOTIPY_CLIENT_SECRET = '72ca31c9c22e420eacca1679284d753b'


class SpotifyWidget:
    def __init__(self, root, row, col, local_ip):
        self.root = root
        self.local_ip = local_ip
        self.redirect_uri = f'https://{local_ip}:8888/callback'
        self.sp = None
        self.auth_manager = None
        self.current_track_url = None
        
        print(f"🔗 Redirect URI: {self.redirect_uri}")
        print(f"⚠️  IMPORTANTE: Adiciona este URI no Spotify Dashboard:")
        print(f"   {self.redirect_uri}\n")
        
        # Criar interface
        self.frame = self._create_card(row, col)
        
        self.spot_label = tk.Label(
            self.frame,
            text="Spotify",
            font=("Arial", 14, "bold"),
            bg="white",
            fg="#1DB954",
            cursor="hand2"
        )
        self.spot_label.pack(pady=5)
        
        self.track_label = tk.Label(
            self.frame,
            text="A iniciar servidor...",
            font=("Arial", 11),
            bg="white",
            fg="#1DB954",
            wraplength=200,
            cursor="hand2"
        )
        self.track_label.pack(pady=5)
        
        self.qr_label = tk.Label(self.frame, bg="white", cursor="hand2")
        self.qr_label.pack(pady=5)
        
        self.ip_label = tk.Label(
            self.frame,
            text=f"IP: {local_ip}:8888",
            font=("Arial", 8),
            bg="white",
            fg="#999"
        )
        self.ip_label.pack(pady=2)
        
        # Bind de cliques em TODOS os elementos
        self.frame.bind("<Button-1>", self._open_spotify)
        self.spot_label.bind("<Button-1>", self._open_spotify)
        self.track_label.bind("<Button-1>", self._open_spotify)
        self.qr_label.bind("<Button-1>", self._open_spotify)
        self.ip_label.bind("<Button-1>", self._open_spotify)
        
        # Iniciar servidor e autenticação
        self._start_auth_server()
    
    def _create_card(self, r, c):
        frame = tk.Frame(self.root, bg="white", cursor="hand2")
        frame.grid(row=r, column=c, sticky="nsew", padx=20, pady=20)
        return frame
    
    def _open_url_windows(self, url):
        """Abre URL no Windows usando múltiplos métodos"""
        try:
            # Método 1: os.startfile (Windows específico)
            os.startfile(url)
            print(f"✓ URL aberto com os.startfile: {url}")
            return True
        except Exception as e1:
            print(f"❌ os.startfile falhou: {e1}")
            
            try:
                # Método 2: subprocess com start
                subprocess.Popen(['start', url], shell=True)
                print(f"✓ URL aberto com subprocess: {url}")
                return True
            except Exception as e2:
                print(f"❌ subprocess falhou: {e2}")
                
                try:
                    # Método 3: webbrowser padrão
                    webbrowser.open(url)
                    print(f"✓ URL aberto com webbrowser: {url}")
                    return True
                except Exception as e3:
                    print(f"❌ webbrowser falhou: {e3}")
                    return False
    
    def _open_spotify(self, event=None):
        """Abre o Spotify Web ou a música atual"""
        print(f"\n🖱️ Clique detectado!")
        
        url = self.current_track_url if self.current_track_url else "https://open.spotify.com"
        print(f"🔗 URL a abrir: {url}")
        
        # Tentar abrir com múltiplos métodos
        success = self._open_url_windows(url)
        
        if not success:
            print("❌ Não foi possível abrir o browser automaticamente")
            print(f"📋 Copia este link manualmente: {url}")
            
            # Copiar para clipboard
            try:
                self.root.clipboard_clear()
                self.root.clipboard_append(url)
                print("✓ Link copiado para a clipboard!")
                
                # Mostrar notificação temporária
                self._show_notification("Link copiado!")
            except:
                pass
    
    def _show_notification(self, message):
        """Mostra uma notificação temporária"""
        # Criar label temporário
        notif = tk.Label(
            self.frame,
            text=message,
            font=("Arial", 9, "bold"),
            bg="#4CAF50",
            fg="white",
            padx=10,
            pady=5
        )
        notif.place(relx=0.5, rely=0.5, anchor="center")
        
        # Remover após 2 segundos
        self.root.after(2000, notif.destroy)
    
    def _start_auth_server(self):
        """Inicia o servidor HTTPS"""
        # Gerar certificado SSL
        cert_file, key_file = generate_self_signed_cert()
        
        # Iniciar servidor em background
        run_server_thread(cert_file, key_file, port=8888)
        
        # Aguardar um pouco e gerar QR code
        self.root.after(1000, self._show_qr_code)
    
    def _show_qr_code(self):
        """Gera e mostra o QR code de autenticação"""
        try:
            scope = "user-read-currently-playing user-read-playback-state"
            
            self.auth_manager = SpotifyOAuth(
                client_id=SPOTIPY_CLIENT_ID,
                client_secret=SPOTIPY_CLIENT_SECRET,
                redirect_uri=self.redirect_uri,
                scope=scope,
                cache_path=".spotify_cache"
            )
            
            # Verificar se já tem token guardado
            token_info = self.auth_manager.get_cached_token()
            if token_info:
                self.sp = spotipy.Spotify(auth=token_info['access_token'])
                self._on_auth_success()
                return
            
            # Obter URL de autenticação
            auth_url = self.auth_manager.get_authorize_url()
            
            # Gerar QR Code
            qr = qrcode.QRCode(version=1, box_size=5, border=2)
            qr.add_data(auth_url)
            qr.make(fit=True)
            
            img = qr.make_image(fill_color="black", back_color="white")
            img = img.resize((130, 130))
            
            # Converter para Tkinter
            photo = ImageTk.PhotoImage(img)
            self.qr_label.config(image=photo)
            self.qr_label.image = photo
            
            self.track_label.config(text="Scanneia com o telemóvel", fg="#1DB954")
            
            # Aguardar autenticação em background
            threading.Thread(target=self._wait_for_auth, daemon=True).start()
            
        except Exception as e:
            self.track_label.config(text=f"Erro: {str(e)[:40]}", fg="#E53935")
            print(f"Erro ao gerar QR: {e}")
    
    def _wait_for_auth(self):
        """Aguarda o código de autenticação"""
        auth_code = wait_for_auth_code(timeout=300)
        
        if auth_code:
            try:
                # Trocar o código por um token
                token_info = self.auth_manager.get_access_token(auth_code, as_dict=True)
                
                if token_info:
                    self.sp = spotipy.Spotify(auth=token_info['access_token'])
                    self.root.after(0, self._on_auth_success)
                else:
                    self.root.after(0, lambda: self.track_label.config(
                        text="Erro na autenticação", fg="#E53935"))
            except Exception as e:
                print(f"Erro ao trocar token: {e}")
                self.root.after(0, lambda: self.track_label.config(
                    text=f"Erro: {str(e)[:30]}", fg="#E53935"))
        else:
            self.root.after(0, lambda: self.track_label.config(
                text="Timeout - scanneia novamente", fg="#FF9800"))
    
    def _on_auth_success(self):
        """Chamado quando autenticação é bem sucedida"""
        self.qr_label.pack_forget()
        self.ip_label.pack_forget()
        self.track_label.config(text="✓ Conectado!\n(Clica para abrir)", fg="#1DB954")
        self._update_spotify_info()
    
    def _update_spotify_info(self):
        """Atualiza informação da música a tocar"""
        if self.sp:
            try:
                current = self.sp.current_playback()
                if current and current['is_playing']:
                    track = current['item']['name']
                    artist = current['item']['artists'][0]['name']
                    
                    # Guardar URL da música
                    self.current_track_url = current['item']['external_urls']['spotify']
                    
                    self.track_label.config(
                        text=f"🎵 A tocar:\n{track}\n{artist}\n\n(Clica para abrir)",
                        fg="#2d2d2d"
                    )
                else:
                    self.current_track_url = None
                    self.track_label.config(
                        text="⏸ Pausado\n(Dá play no telemóvel)\n\n(Clica para abrir Spotify)",
                        fg="#FF9800"
                    )
            except spotipy.exceptions.SpotifyException as e:
                if e.http_status == 403:
                    # Erro 403 - App em Development Mode
                    self.current_track_url = None
                    self.track_label.config(
                        text="⚠️ Erro 403\nAdiciona o teu email\nno Spotify Dashboard\n(User Management)",
                        fg="#E53935",
                        font=("Arial", 9)
                    )
                    print("\n⚠️ ERRO 403: A app está em Development Mode!")
                    print("Solução: Vai ao Spotify Dashboard → User Management")
                    print("E adiciona o email da tua conta Spotify\n")
                    return  # Não tentar novamente
                else:
                    # Tentar refresh token
                    try:
                        token_info = self.auth_manager.get_cached_token()
                        if token_info:
                            self.sp = spotipy.Spotify(auth=token_info['access_token'])
                    except:
                        pass
            except Exception as e:
                print(f"Erro inesperado: {e}")
            
            # Atualizar a cada 5 segundos
            self.root.after(5000, self._update_spotify_info)