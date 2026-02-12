"""Widget do calendário (placeholder)"""

import tkinter as tk


class CalendarWidget:
    def __init__(self, root, row, col):
        self.root = root
        self.frame = self._create_card(row, col)
        
        tk.Label(
            self.frame,
            text="Google Calendar",
            font=("Arial", 18, "bold"),
            bg="white",
            fg="#4285F4"
        ).pack(expand=True)
        
        tk.Label(
            self.frame,
            text="Sem eventos",
            font=("Arial", 10),
            bg="white",
            fg="gray"
        ).pack()
    
    def _create_card(self, r, c):
        frame = tk.Frame(self.root, bg="white")
        frame.grid(row=r, column=c, sticky="nsew", padx=20, pady=20)
        return frame