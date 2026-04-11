import subprocess
import sys
import os
import time
import tkinter as tk
from tkinter import ttk, messagebox
import webbrowser
from datetime import datetime

# ----------------------------------------------------------------------
# CONFIGURACIÓN DE SERVICIOS (ajusta según tu proyecto)
# ----------------------------------------------------------------------
services = [
    {"name": "Frontend", "folder": "../frontend/traceflow-dashboard", "cmd": "npm start", "port": 4200},
    {"name": "Backend", "folder": "../backend/traceFlow_Core", "cmd": "python manage.py runserver", "port": 8000},
    {"name": "Tienda", "folder": "../microservicios/tienda", "cmd": "python -m uvicorn main:app --reload --port 8001", "port": 8001},
    {"name": "Inventario", "folder": "../microservicios/inventario", "cmd": "python -m uvicorn main:app --reload --port 8004", "port": 8004},
    {"name": "Notificacion", "folder": "../microservicios/notificacion", "cmd": "python -m uvicorn main:app --reload --port 8003", "port": 8003},
    {"name": "Pago", "folder": "../microservicios/pago", "cmd": "python -m uvicorn main:app --reload --port 8002", "port": 8002},
]

# Crear carpeta de logs si no existe
LOGS_DIR = os.path.join(os.getcwd(), "logs")
os.makedirs(LOGS_DIR, exist_ok=True)

# ----------------------------------------------------------------------
# FUNCIONES AUXILIARES PARA MANEJO DE PUERTOS Y PROCESOS (Windows)
# ----------------------------------------------------------------------
def is_port_in_use(port):
    """Devuelve True si el puerto está en uso (Windows)."""
    if sys.platform != "win32":
        return False
    result = subprocess.run(f"netstat -ano | findstr :{port}", shell=True, capture_output=True, text=True)
    return "LISTENING" in result.stdout

def kill_process_on_port(port):
    """Mata el proceso que está usando el puerto (Windows)."""
    if sys.platform != "win32":
        return False
    try:
        # Obtener PID del proceso que escucha en el puerto
        result = subprocess.run(f"netstat -ano | findstr :{port} | findstr LISTENING", shell=True, capture_output=True, text=True)
        if not result.stdout:
            return False
        lines = result.stdout.strip().splitlines()
        for line in lines:
            parts = line.split()
            if len(parts) >= 5:
                pid = parts[4]
                subprocess.run(f"taskkill /F /PID {pid}", shell=True, capture_output=True)
                return True
    except Exception:
        pass
    return False

def kill_processes_by_name(names):
    """Mata procesos que contengan alguno de los nombres en la lista (Windows)."""
    if sys.platform != "win32":
        return
    for name in names:
        subprocess.run(f"taskkill /F /IM {name}", shell=True, capture_output=True)

def kill_orphan_processes():
    """Mata procesos huérfanos relacionados con los servicios (python, node, uvicorn, npm, manage.py)."""
    if sys.platform != "win32":
        messagebox.showinfo("Info", "Eliminación de procesos solo soportada en Windows.")
        return
    # Nombres de procesos a matar (cuidado: podría matar otros procesos no deseados)
    process_names = ["python.exe", "node.exe", "uvicorn.exe", "npm.exe", "cmd.exe"]
    # También podemos matar procesos por título de ventana o por línea de comandos, pero es más complejo
    # Por ahora matamos por nombre (puede ser agresivo)
    respuesta = messagebox.askyesno("Matar procesos huérfanos",
                                    "Se eliminarán todos los procesos python.exe, node.exe, uvicorn.exe, npm.exe y cmd.exe.\n"
                                    "¿Está seguro? (Puede cerrar otros programas no relacionados)")
    if respuesta:
        kill_processes_by_name(process_names)
        messagebox.showinfo("Info", "Procesos eliminados (si existían).")
    else:
        messagebox.showinfo("Cancelado", "No se eliminaron procesos.")

# ----------------------------------------------------------------------
# CLASE PRINCIPAL
# ----------------------------------------------------------------------
class ServiceLauncher:
    def __init__(self, root):
        self.root = root
        self.root.title("Lanzador de servicios - TraceFlow")
        self.root.geometry("820x550")
        self.root.resizable(True, True)

        self.processes = {}      # {nombre: (process, log_file_handle)}
        self.running = True

        self.create_widgets()
        self.update_statuses()
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def create_widgets(self):
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Cabecera
        ttk.Label(main_frame, text="Servicios disponibles", font=("Arial", 14, "bold")).grid(row=0, column=0, columnspan=5, pady=5)
        ttk.Label(main_frame, text="Servicio", font=("Arial", 10, "bold")).grid(row=1, column=0, sticky="w", padx=5)
        ttk.Label(main_frame, text="Puerto", font=("Arial", 10, "bold")).grid(row=1, column=1, sticky="w", padx=5)
        ttk.Label(main_frame, text="Estado", font=("Arial", 10, "bold")).grid(row=1, column=2, sticky="w", padx=5)
        ttk.Label(main_frame, text="Acciones", font=("Arial", 10, "bold")).grid(row=1, column=3, sticky="w", padx=5)
        ttk.Label(main_frame, text="Logs", font=("Arial", 10, "bold")).grid(row=1, column=4, sticky="w", padx=5)
        ttk.Separator(main_frame, orient='horizontal').grid(row=2, column=0, columnspan=5, sticky="ew", pady=5)

        self.rows = []
        for idx, svc in enumerate(services):
            row_num = idx + 3
            ttk.Label(main_frame, text=svc["name"]).grid(row=row_num, column=0, sticky="w", padx=5, pady=2)
            ttk.Label(main_frame, text=str(svc.get("port", "-"))).grid(row=row_num, column=1, sticky="w", padx=5, pady=2)

            status_var = tk.StringVar(value="Stopped")
            lbl_status = ttk.Label(main_frame, textvariable=status_var, foreground="red")
            lbl_status.grid(row=row_num, column=2, sticky="w", padx=5, pady=2)

            btn_frame = ttk.Frame(main_frame)
            btn_frame.grid(row=row_num, column=3, sticky="w", padx=5, pady=2)
            btn_start = ttk.Button(btn_frame, text="Start", width=6, command=lambda s=svc: self.start_service(s))
            btn_start.pack(side=tk.LEFT, padx=2)
            btn_stop = ttk.Button(btn_frame, text="Stop", width=6, command=lambda s=svc: self.stop_service(s))
            btn_stop.pack(side=tk.LEFT, padx=2)

            btn_logs = ttk.Button(main_frame, text="Ver logs", width=10, command=lambda s=svc: self.open_log(s))
            btn_logs.grid(row=row_num, column=4, sticky="w", padx=5, pady=2)

            self.rows.append({
                "service": svc,
                "status_var": status_var,
                "btn_start": btn_start,
                "btn_stop": btn_stop,
                "lbl_status": lbl_status,
                "btn_logs": btn_logs
            })

        # Botones globales
        global_frame = ttk.Frame(main_frame)
        global_frame.grid(row=len(services)+3, column=0, columnspan=5, pady=15)

        ttk.Button(global_frame, text="Start All (ordenado)", command=self.start_all).pack(side=tk.LEFT, padx=10)
        ttk.Button(global_frame, text="Stop All", command=self.stop_all).pack(side=tk.LEFT, padx=10)
        ttk.Button(global_frame, text="Abrir Dashboard", command=self.open_dashboard).pack(side=tk.LEFT, padx=10)
        ttk.Button(global_frame, text="Limpiar logs", command=self.clear_logs).pack(side=tk.LEFT, padx=10)
        ttk.Button(global_frame, text="Matar procesos huérfanos", command=kill_orphan_processes).pack(side=tk.LEFT, padx=10)

        ttk.Label(main_frame, text="Los logs se guardan en la carpeta 'logs/'. Use 'Ver logs' para abrir el archivo.", foreground="gray").grid(
            row=len(services)+4, column=0, columnspan=5, pady=5)

    def get_log_path(self, service_name):
        safe_name = service_name.replace(" ", "_").lower()
        return os.path.join(LOGS_DIR, f"{safe_name}.log")

    def start_service(self, svc):
        name = svc["name"]
        port = svc.get("port")
        folder = os.path.join(os.getcwd(), svc["folder"])
        cmd = svc["cmd"]

        if not os.path.isdir(folder):
            messagebox.showerror("Error", f"La carpeta '{folder}' no existe.")
            return

        if name in self.processes and self.processes[name][0].poll() is None:
            messagebox.showinfo("Información", f"El servicio '{name}' ya está corriendo.")
            return

        # Verificar si el puerto está en uso (solo para servicios que tienen puerto definido)
        if port and is_port_in_use(port):
            respuesta = messagebox.askyesno("Puerto ocupado",
                                            f"El puerto {port} ya está en uso.\n"
                                            "¿Desea matar el proceso que lo ocupa e iniciar el servicio?")
            if respuesta:
                if kill_process_on_port(port):
                    messagebox.showinfo("Info", f"Proceso en el puerto {port} eliminado.")
                    # Esperar un momento para que el puerto se libere
                    time.sleep(1)
                else:
                    messagebox.showerror("Error", f"No se pudo matar el proceso en el puerto {port}.\n"
                                                  "Intente manualmente o reinicie.")
                    return
            else:
                messagebox.showinfo("Cancelado", f"No se inició {name} porque el puerto {port} está ocupado.")
                return

        log_file = self.get_log_path(name)
        log_fd = open(log_file, "a", encoding="utf-8")
        log_fd.write(f"\n--- Iniciando {name} en {datetime.now()} ---\n")
        log_fd.flush()

        try:
            if sys.platform == "win32":
                proc = subprocess.Popen(
                    cmd,
                    cwd=folder,
                    stdout=log_fd,
                    stderr=subprocess.STDOUT,
                    shell=True,
                    creationflags=subprocess.CREATE_NO_WINDOW
                )
            else:
                proc = subprocess.Popen(
                    cmd,
                    cwd=folder,
                    stdout=log_fd,
                    stderr=subprocess.STDOUT,
                    shell=True,
                    preexec_fn=os.setpgrp
                )
            self.processes[name] = (proc, log_fd)
            self.update_row_status(name, "Running", "green")
        except Exception as e:
            log_fd.close()
            messagebox.showerror("Error", f"No se pudo iniciar {name}:\n{e}")

    def stop_service(self, svc):
        name = svc["name"]
        if name in self.processes:
            proc, log_fd = self.processes[name]
            if proc.poll() is None:
                proc.terminate()
                try:
                    proc.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    proc.kill()
            log_fd.close()
            del self.processes[name]
            self.update_row_status(name, "Stopped", "red")
        else:
            self.update_row_status(name, "Stopped", "red")

    def open_log(self, svc):
        name = svc["name"]
        log_file = self.get_log_path(name)
        if os.path.exists(log_file):
            if sys.platform == "win32":
                os.startfile(log_file)
            elif sys.platform == "darwin":
                subprocess.run(["open", log_file])
            else:
                subprocess.run(["xdg-open", log_file])
        else:
            messagebox.showinfo("Información", f"El archivo de log para '{name}' aún no existe. Inicie el servicio primero.")

    def open_dashboard(self):
        webbrowser.open("http://localhost:4200")

    def clear_logs(self):
        respuesta = messagebox.askyesno("Limpiar logs", "¿Está seguro de que desea borrar todo el contenido de los archivos de log?\nEsta acción no se puede deshacer.")
        if not respuesta:
            return
        cleared = 0
        errors = 0
        for filename in os.listdir(LOGS_DIR):
            if filename.endswith(".log"):
                filepath = os.path.join(LOGS_DIR, filename)
                try:
                    with open(filepath, "w", encoding="utf-8") as f:
                        f.write("")
                    cleared += 1
                except Exception as e:
                    errors += 1
                    print(f"Error limpiando {filename}: {e}")
        messagebox.showinfo("Limpiar logs", f"Se limpiaron {cleared} archivos de log.\nErrores: {errors}")

    def get_start_order(self):
        micro = []
        backend = None
        frontend = None
        other = []
        for svc in services:
            folder = svc.get("folder", "")
            if "microservicios" in folder:
                micro.append(svc)
            elif "backend" in folder:
                backend = svc
            elif "frontend" in folder:
                frontend = svc
            else:
                other.append(svc)
        ordered = micro
        if backend:
            ordered.append(backend)
        if frontend:
            ordered.append(frontend)
        ordered.extend(other)
        return ordered

    def start_all(self):
        for svc in self.get_start_order():
            name = svc["name"]
            if name not in self.processes or self.processes[name][0].poll() is not None:
                self.start_service(svc)
                time.sleep(2)

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
        for name, (proc, log_fd) in list(self.processes.items()):
            if proc.poll() is not None:
                self.update_row_status(name, "Stopped", "red")
                log_fd.close()
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