import tkinter as tk
import atexit
from widgets.clock import ClockWidget
from widgets.weather import WeatherWidget
from widgets.spotify import SpotifyWidget
from widgets.calendar_widget import CalendarWidget
from widgets.emergency import EmergencyButton
from utils.network import get_local_ip, cleanup_app_data

class VitraeDashboard:
    def __init__(self, root):
        self.root = root
        self.root.title("VitraeView - Dashboard")
        self.root.geometry("1024x768") # Resolução fixa
        self.root.resizable(False, False)
        self.root.configure(bg="white")
        
        self.local_ip = get_local_ip()
        print(f"📱 Sistema Iniciado no IP: {self.local_ip}")
        
        for i in range(3):
            self.root.grid_columnconfigure(i, weight=1, uniform="equal")
            self.root.grid_rowconfigure(i, weight=1, uniform="equal")

        ClockWidget(self.root, 0, 0)
        WeatherWidget(self.root, 0, 2)
        SpotifyWidget(self.root, 2, 0, self.local_ip)
        CalendarWidget(self.root, 2, 2)
        EmergencyButton(self.root, 2, 1, callback=self.on_closing)

        self.root.bind("<Escape>", lambda e: self.on_closing())
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def on_closing(self):
        print("\n🧹 A realizar limpeza profunda...")
        cleanup_app_data()
        self.root.destroy()

if __name__ == "__main__":
    atexit.register(cleanup_app_data)
    root = tk.Tk()
    app = VitraeDashboard(root)
    root.mainloop()