"""Widget do relógio"""

import tkinter as tk
import requests
from datetime import datetime, timedelta


class ClockWidget:
    def __init__(self, root, row, col):
        self.root = root
        self.frame = self._create_card(row, col)
        
        self.lbl_time = tk.Label(
            self.frame,
            text="--:--:--",
            font=("Arial", 40, "bold"),
            bg="white",
            fg="#2d2d2d"
        )
        self.lbl_time.pack(expand=True)
        
        self.api_time = None
        self._sync_time()
        self._update_clock()
    
    def _create_card(self, r, c):
        frame = tk.Frame(self.root, bg="white")
        frame.grid(row=r, column=c, sticky="nsew", padx=20, pady=20)
        return frame
    
    def _sync_time(self):
        """Sincroniza o tempo com API externa"""
        try:
            url = "http://worldtimeapi.org/api/timezone/Europe/Lisbon"
            r = requests.get(url, timeout=5)
            data = r.json()
            dt_str = data["datetime"].split(".")[0]
            self.api_time = datetime.fromisoformat(dt_str)
        except Exception:
            self.api_time = datetime.now()
        
        # Sincronizar novamente em 1 minuto
        self.root.after(60000, self._sync_time)
    
    def _update_clock(self):
        """Atualiza o relógio a cada segundo"""
        if self.api_time:
            self.lbl_time.config(text=self.api_time.strftime("%H:%M:%S"))
            self.api_time += timedelta(seconds=1)
        
        self.root.after(1000, self._update_clock)