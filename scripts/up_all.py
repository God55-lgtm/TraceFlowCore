import subprocess
import sys
import os
import threading
import time
import tkinter as tk
from tkinter import ttk, messagebox

# ----------------------------------------------------------------------
# CONFIGURACIÓN DE SERVICIOS (ajusta según tu proyecto)
# ----------------------------------------------------------------------
services = [
    {
        "name": "Frontend",
        "folder": "../frontend/traceflow-dashboard",
        "cmd": "npm start",
        "port": 4200,
    },
    {
        "name": "Backend",
        "folder": "../backend/traceFlow_Core",
        "cmd": "python manage.py runserver",
        "port": 8000,
    },
    {
        "name": "Tienda",
        "folder": "../microservicios/tienda",
        "cmd": "python -m uvicorn main:app --reload --port 8001",
        "port": 8001,
    },
    {
        "name": "Inventario",
        "folder": "../microservicios/inventario",
        "cmd": "python -m uvicorn main:app --reload --port 8004",
        "port": 8004,
    },
    {
        "name": "Notificacion",
        "folder": "../microservicios/notificacion",
        "cmd": "python -m uvicorn main:app --reload --port 8003",
        "port": 8003,
    },
    {
        "name": "Pago",
        "folder": "../microservicios/pago",
        "cmd": "python -m uvicorn main:app --reload --port 8002",
        "port": 8002,
    },
    
]

# ----------------------------------------------------------------------
# CLASE PRINCIPAL DE LA INTERFAZ
# ----------------------------------------------------------------------
class ServiceLauncher:
    def __init__(self, root):
        self.root = root
        self.root.title("Lanzador de servicios - TraceFlow")
        self.root.geometry("720x450")
        self.root.resizable(True, True)

        # Diccionario para almacenar los procesos activos {nombre_servicio: proceso}
        self.processes = {}

        # Variable de control para actualización de estado
        self.running = True

        self.create_widgets()
        self.update_statuses()
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def create_widgets(self):
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Cabecera
        ttk.Label(main_frame, text="Servicios disponibles", font=("Arial", 14, "bold")).grid(row=0, column=0, columnspan=4, pady=5)

        # Encabezados
        ttk.Label(main_frame, text="Servicio", font=("Arial", 10, "bold")).grid(row=1, column=0, sticky="w", padx=5)
        ttk.Label(main_frame, text="Puerto", font=("Arial", 10, "bold")).grid(row=1, column=1, sticky="w", padx=5)
        ttk.Label(main_frame, text="Estado", font=("Arial", 10, "bold")).grid(row=1, column=2, sticky="w", padx=5)
        ttk.Label(main_frame, text="Acciones", font=("Arial", 10, "bold")).grid(row=1, column=3, sticky="w", padx=5)

        ttk.Separator(main_frame, orient='horizontal').grid(row=2, column=0, columnspan=4, sticky="ew", pady=5)

        self.rows = []
        for idx, svc in enumerate(services):
            row_num = idx + 3

            # Nombre
            ttk.Label(main_frame, text=svc["name"]).grid(row=row_num, column=0, sticky="w", padx=5, pady=2)

            # Puerto
            ttk.Label(main_frame, text=str(svc.get("port", "-"))).grid(row=row_num, column=1, sticky="w", padx=5, pady=2)

            # Estado (variable y label)
            status_var = tk.StringVar(value="Stopped")
            lbl_status = ttk.Label(main_frame, textvariable=status_var, foreground="red")
            lbl_status.grid(row=row_num, column=2, sticky="w", padx=5, pady=2)

            # Botones
            btn_frame = ttk.Frame(main_frame)
            btn_frame.grid(row=row_num, column=3, sticky="w", padx=5, pady=2)

            btn_start = ttk.Button(btn_frame, text="Start", width=6,
                                   command=lambda s=svc: self.start_service(s))
            btn_start.pack(side=tk.LEFT, padx=2)

            btn_stop = ttk.Button(btn_frame, text="Stop", width=6,
                                  command=lambda s=svc: self.stop_service(s))
            btn_stop.pack(side=tk.LEFT, padx=2)

            self.rows.append({
                "service": svc,
                "status_var": status_var,
                "btn_start": btn_start,
                "btn_stop": btn_stop,
                "lbl_status": lbl_status
            })

        # Botones globales
        global_frame = ttk.Frame(main_frame)
        global_frame.grid(row=len(services)+3, column=0, columnspan=4, pady=15)

        ttk.Button(global_frame, text="Start All", command=self.start_all).pack(side=tk.LEFT, padx=10)
        ttk.Button(global_frame, text="Stop All", command=self.stop_all).pack(side=tk.LEFT, padx=10)

        ttk.Label(main_frame, text="Cada servicio se abre en su propia ventana de consola.", foreground="gray").grid(
            row=len(services)+4, column=0, columnspan=4, pady=5)

    def start_service(self, svc):
        name = svc["name"]
        folder = os.path.join(os.getcwd(), svc["folder"])
        cmd = svc["cmd"]

        if not os.path.isdir(folder):
            messagebox.showerror("Error", f"La carpeta '{folder}' no existe.")
            return

        if name in self.processes and self.processes[name].poll() is None:
            messagebox.showinfo("Información", f"El servicio '{name}' ya está corriendo.")
            return

        try:
            if sys.platform == "win32":
                proc = subprocess.Popen(
                    cmd,
                    cwd=folder,
                    creationflags=subprocess.CREATE_NEW_CONSOLE,
                    shell=True
                )
            else:
                # Para Linux/Mac (requiere xterm o similar)
                proc = subprocess.Popen(
                    ["xterm", "-e", f"cd {folder} && {cmd}"],
                    shell=False
                )
            self.processes[name] = proc
            self.update_row_status(name, "Running", "green")
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo iniciar {name}:\n{e}")

    def stop_service(self, svc):
        name = svc["name"]
        if name in self.processes:
            proc = self.processes[name]
            if proc.poll() is None:
                proc.terminate()
                try:
                    proc.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    proc.kill()
            del self.processes[name]
            self.update_row_status(name, "Stopped", "red")
        else:
            self.update_row_status(name, "Stopped", "red")

    def start_all(self):
        for row in self.rows:
            svc = row["service"]
            name = svc["name"]
            if name not in self.processes or self.processes[name].poll() is not None:
                self.start_service(svc)

    def stop_all(self):
        for row in self.rows:
            self.stop_service(row["service"])

    def update_row_status(self, service_name, text, color):
        for row in self.rows:
            if row["service"]["name"] == service_name:
                row["status_var"].set(text)
                row["lbl_status"].config(foreground=color)
                break

    def update_statuses(self):
        if not self.running:
            return

        for name, proc in list(self.processes.items()):
            if proc.poll() is not None:
                self.update_row_status(name, "Stopped", "red")
                del self.processes[name]

        self.root.after(1000, self.update_statuses)

    def on_closing(self):
        self.running = False
        self.stop_all()
        self.root.destroy()

# ----------------------------------------------------------------------
if __name__ == "__main__":
    root = tk.Tk()
    app = ServiceLauncher(root)
    root.mainloop()
