import customtkinter as ctk
import serial
import threading
import time

MAX_DISTANCE_MM = 6000
RADAR_SIZE = 600
SCALE = RADAR_SIZE / MAX_DISTANCE_MM

class RadarVisualizer(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("VitraeView - Interface Radar com Filtro")
        self.geometry(f"{RADAR_SIZE + 40}x{RADAR_SIZE + 100}")
        self.resizable(False, False)

        self.lbl_title = ctk.CTkLabel(self, text="Radar - Filtro de Fantasmas", font=("Roboto", 24, "bold"), text_color="#2ecc71")
        self.lbl_title.pack(pady=10)

        self.canvas = ctk.CTkCanvas(self, width=RADAR_SIZE, height=RADAR_SIZE, bg="#1a1a1a", highlightthickness=0)
        self.canvas.pack(pady=10)

        self.targets = []
        self.buffer = b''

        try:
            self.ser = serial.Serial('/dev/ttyS0', 256000, timeout=0.1)
            threading.Thread(target=self.read_serial_loop, daemon=True).start()
        except Exception as e:
            self.lbl_title.configure(text="Erro de Comunicação", text_color="#e74c3c")

        self.update_gui()

    def decode_target(self, data_bytes):
        x = data_bytes[0] + ((data_bytes[1] & 0x7F) << 8)
        if data_bytes[1] & 0x80: x = -x
            
        y = data_bytes[2] + ((data_bytes[3] & 0x7F) << 8)
        
        # NOVA MATEMÁTICA: Extração da Velocidade (Bytes 4 e 5)
        vel = data_bytes[4] + ((data_bytes[5] & 0x7F) << 8)
        if data_bytes[5] & 0x80: vel = -vel
            
        return x, y, vel

    def read_serial_loop(self):
        while True:
            try:
                if self.ser and self.ser.in_waiting > 0:
                    self.buffer += self.ser.read(self.ser.in_waiting)
                    idx = self.buffer.find(b'\xaa\xff')
                    
                    if idx != -1:
                        if len(self.buffer) >= idx + 30: 
                            frame = self.buffer[idx : idx+30]
                            self.buffer = self.buffer[idx+30 :]
                            
                            novos_alvos = []
                            for i in range(3):
                                inicio = 4 + (i * 8)
                                bytes_alvo = frame[inicio : inicio+8]
                                
                                if len(bytes_alvo) == 8:
                                    x, y, vel = self.decode_target(bytes_alvo)
                                    
                                    # Aceita os alvos na zona válida e passa a velocidade para a interface
                                    if 400 < y < 6000 and abs(x) < 4000:
                                        novos_alvos.append((x, y, vel))
                                        
                            self.targets = novos_alvos
            except Exception:
                self.buffer = b''
            time.sleep(0.01)

    def draw_radar_background(self):
        self.canvas.delete("all")
        origin_x = RADAR_SIZE / 2
        origin_y = RADAR_SIZE
        
        colors = ["#2c3e50", "#34495e", "#7f8c8d"]
        distances_m = [6, 4, 2] 
        
        for d, color in zip(distances_m, colors):
            raio_px = (d * 1000) * SCALE
            self.canvas.create_arc(
                origin_x - raio_px, origin_y - raio_px, 
                origin_x + raio_px, origin_y + raio_px,
                start=0, extent=180, outline=color, width=2, style="arc"
            )
            self.canvas.create_text(origin_x, origin_y - raio_px - 10, text=f"{d} Metros", fill=color, font=("Roboto", 10))

        self.canvas.create_line(origin_x, origin_y, origin_x, 0, fill="#2c3e50", dash=(4, 4))
        self.canvas.create_rectangle(origin_x - 15, origin_y - 10, origin_x + 15, origin_y, fill="#e74c3c")

    def update_gui(self):
        self.draw_radar_background()
        origin_x = RADAR_SIZE / 2
        origin_y = RADAR_SIZE

        for i, (x_mm, y_mm, vel) in enumerate(self.targets):
            px_x = origin_x + (x_mm * SCALE)
            px_y = origin_y - (y_mm * SCALE)
            
            if 0 <= px_x <= RADAR_SIZE and 0 <= px_y <= RADAR_SIZE:
                raio = 8 
                
                # A MAGIA ACONTECE AQUI:
                # Se a velocidade for 0, desenha a Cinzento (Fantasma detetado)
                # Se tiver velocidade, desenha a Azul Ciano (Humano)
                cor_ponto = "#00d2d3" if vel != 0 else "#7f8c8d"
                
                self.canvas.create_oval(px_x - raio, px_y - raio, px_x + raio, px_y + raio, fill=cor_ponto, outline="#ffffff")
                texto = f"Alvo {i+1} | Vel: {vel}\nX:{x_mm/1000:.2f}m\nY:{y_mm/1000:.2f}m"
                self.canvas.create_text(px_x, px_y - 25, text=texto, fill="#ffffff", font=("Roboto", 10))

        self.after(33, self.update_gui)

if __name__ == "__main__":
    app = RadarVisualizer()
    app.mainloop()
