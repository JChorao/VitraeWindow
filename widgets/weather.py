"""Widget do tempo"""

import tkinter as tk
import requests


class WeatherWidget:
    def __init__(self, root, row, col):
        self.root = root
        self.frame = self._create_card(row, col)
        
        self.lbl_temp = tk.Label(
            self.frame,
            text="A carregar...",
            font=("Arial", 35),
            bg="white",
            fg="#4A90E2"
        )
        self.lbl_temp.pack(expand=True)
        
        self._get_weather()
    
    def _create_card(self, r, c):
        frame = tk.Frame(self.root, bg="white")
        frame.grid(row=r, column=c, sticky="nsew", padx=20, pady=20)
        return frame
    
    def _get_weather(self):
        """Obtém dados meteorológicos"""
        try:
            url = "https://api.open-meteo.com/v1/forecast?latitude=39.82&longitude=-7.49&current_weather=true"
            res = requests.get(url).json()
            temp = res['current_weather']['temperature']
            self.lbl_temp.config(text=f"{temp}°C")
        except:
            self.lbl_temp.config(text="Erro API")
        
        # Atualizar em 10 minutos
        self.root.after(600000, self._get_weather)