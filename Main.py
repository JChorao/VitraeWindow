import tkinter as tk
from datetime import datetime, timedelta
import requests
import atexit
from widgets.clock import ClockWidget
from widgets.weather import WeatherWidget
from widgets.spotify import SpotifyWidget
from widgets.calendar_widget import CalendarWidget
from widgets.emergency import EmergencyButton
from utils.network import get_local_ip, cleanup_certificates

class VitraeDashboard:
    def __init__(self, root):
        self.root = root
        self.root.title("VitraeView - Dashboard")
        self.root.geometry("1024x768")
        self.root.configure(bg="white")
        
        # Obter IP local
        self.local_ip = get_local_ip()
        print(f"📱 IP Local: {self.local_ip}")
        
        # Variável para controlar estado de alerta
        self.alert_active = False

        # Criar a Grelha 3x3
        for i in range(3):
            self.root.grid_columnconfigure(i, weight=1, uniform="equal")
            self.root.grid_rowconfigure(i, weight=1, uniform="equal")

        # Iniciar os Widgets nos Cantos
        ClockWidget(self.root, 0, 0)
        WeatherWidget(self.root, 0, 2)
        SpotifyWidget(self.root, 2, 0, self.local_ip)
        CalendarWidget(self.root, 2, 2)
        EmergencyButton(self.root, 2, 1, self.toggle_gas_alert)
        
        # Registrar cleanup ao fechar
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def on_closing(self):
        """Chamado quando a janela é fechada"""
        print("\n🧹 A limpar ficheiros temporários...")
        cleanup_certificates()
        self.root.destroy()

    def toggle_gas_alert(self):
        if self.alert_active:
            self.deactivate_alert()
        else:
            self.activate_alert()

    def activate_alert(self):
        self.alert_active = True
        
        for widget in self.root.winfo_children():
            widget.grid_forget()
        
        self.alert_frame = tk.Frame(self.root, bg="#C62828")
        self.alert_frame.place(x=0, y=0, relwidth=1, relheight=1)
        
        msg1 = tk.Label(self.alert_frame, text="Fuga de Gás",
                       font=("Arial", 65, "bold"),
                       bg="#C62828", fg="#1a1a1a")
        msg1.place(relx=0.5, rely=0.4, anchor="center")
        
        msg2 = tk.Label(self.alert_frame, text="detetada",
                       font=("Arial", 65, "bold"),
                       bg="#FF0000", fg="#1a1a1a")
        msg2.place(relx=0.5, rely=0.55, anchor="center")
        
        btn_close = tk.Button(self.alert_frame, text="✕ Desativar Alerta",
                             font=("Arial", 16, "bold"),
                             bg="#1a1a1a", fg="white",
                             activebackground="#333333",
                             command=self.deactivate_alert,
                             relief="flat", bd=0,
                             padx=30, pady=15)
        btn_close.place(relx=0.5, rely=0.85, anchor="center")
        
        self.pulse_alert()

    def deactivate_alert(self):
        self.alert_active = False
        
        if hasattr(self, 'alert_frame'):
            self.alert_frame.destroy()
        
        for i in range(3):
            self.root.grid_columnconfigure(i, weight=1, uniform="equal")
            self.root.grid_rowconfigure(i, weight=1, uniform="equal")
        
        ClockWidget(self.root, 0, 0)
        WeatherWidget(self.root, 0, 2)
        SpotifyWidget(self.root, 2, 0, self.local_ip)
        CalendarWidget(self.root, 2, 2)
        EmergencyButton(self.root, 2, 1, self.toggle_gas_alert)

    def pulse_alert(self):
        if self.alert_active and hasattr(self, 'alert_frame'):
            current_color = self.alert_frame.cget("bg")
            new_color = "#6D1616" if current_color == "#C62828" else "#C62828"
            
            self.alert_frame.config(bg=new_color)
            
            for widget in self.alert_frame.winfo_children():
                if isinstance(widget, tk.Label):
                    widget.config(bg=new_color)
            
            self.root.after(600, self.pulse_alert)


if __name__ == "__main__":
    # Registrar cleanup para quando o programa terminar
    atexit.register(cleanup_certificates)
    
    root = tk.Tk()
    root.bind("<Escape>", lambda e: root.destroy())
    app = VitraeDashboard(root)
    root.mainloop()
    
    # Cleanup final
    print("\n🧹 Programa terminado. A limpar...")
    cleanup_certificates()