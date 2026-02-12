"""Botão de emergência"""

import tkinter as tk


class EmergencyButton:
    def __init__(self, root, row, col, callback):
        self.root = root
        self.callback = callback
        
        frame = tk.Frame(self.root, bg="white")
        frame.grid(row=row, column=col, sticky="nsew", padx=20, pady=20)
        
        btn = tk.Button(
            frame,
            text="⚠️ ALERTA GÁS",
            font=("Arial", 14, "bold"),
            bg="#E53935",
            fg="white",
            activebackground="#C62828",
            relief="raised",
            bd=3,
            command=callback
        )
        btn.pack(expand=True, fill="both", padx=30, pady=30)