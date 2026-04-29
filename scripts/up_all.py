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

def get_processes_by_commandline_keywords(keywords):
    """
    Retorna lista de PIDs de procesos (con nombre python.exe, node.exe, npm.exe, uvicorn.exe, cmd.exe)
    cuya línea de comandos contenga alguna de las keywords (rutas de proyecto).
    Excluye el PID actual.
    """
    current_pid = os.getpid()
    pids = set()
    process_names = ["python.exe", "node.exe", "npm.exe", "uvicorn.exe", "cmd.exe"]
    for name in process_names:
        cmd = f'wmic process where name="{name}" get ProcessId,CommandLine /format:csv'
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if result.returncode != 0:
            continue
        lines = result.stdout.strip().splitlines()
        for line in lines:
            if ',' not in line:
                continue
            parts = line.split(',')
            if len(parts) < 2:
                continue
            try:
                pid_candidate = parts[-1].strip()
                if not pid_candidate.isdigit():
                    continue
                pid = int(pid_candidate)
                if pid == current_pid:
                    continue
                # La línea de comandos puede tener comas en medio, reconstruir
                command_line = ','.join(parts[1:-1]) if len(parts) > 2 else parts[1] if len(parts) == 2 else ""
                if any(keyword.lower() in command_line.lower() for keyword in keywords):
                    pids.add(pid)
            except:
                continue
    return list(pids)

def kill_processes_by_pids(pids):
    """Mata los procesos dados por PID usando taskkill /F /T (incluye hijos)."""
    for pid in pids:
        try:
            subprocess.run(f"taskkill /F /T /PID {pid}", shell=True, capture_output=True, check=False)
        except:
            pass

def kill_all_related_processes():
    """Mata todos los procesos relacionados con los servicios de TraceFlow (excepto el actual)."""
    keywords = [
        "frontend\\traceflow-dashboard",
        "backend\\traceFlow_Core",
        "microservicios\\tienda",
        "microservicios\\inventario",
        "microservicios\\notificacion",
        "microservicios\\pago",
        "traceflow",
    ]
    pids = get_processes_by_commandline_keywords(keywords)
    if pids:
        kill_processes_by_pids(pids)
    return len(pids)

# ----------------------------------------------------------------------
# CLASE PRINCIPAL
# ----------------------------------------------------------------------
class ServiceLauncher:
    def __init__(self, root):
        self.root = root
        self.root.title("Lanzador de servicios - TraceFlow")
        self.root.geometry("880x600")
        self.root.resizable(True, True)
        
        # Configurar estilo moderno
        self.setup_styles()

        self.processes = {}      # {nombre: (process, log_file_handle)}
        self.running = True

        self.create_widgets()
        self.update_statuses()
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def setup_styles(self):
        style = ttk.Style()
        style.theme_use('clam')
        
        # Colores personalizados
        style.configure("TLabel", font=("Segoe UI", 10))
        style.configure("TButton", font=("Segoe UI", 9), padding=5)
        style.configure("Accent.TButton", background="#4CAF50", foreground="white")
        style.configure("Danger.TButton", background="#f44336", foreground="white")
        style.configure("Info.TButton", background="#2196F3", foreground="white")
        style.configure("Warning.TButton", background="#FF9800", foreground="white")
        
        # Título
        style.configure("Title.TLabel", font=("Segoe UI", 16, "bold"), foreground="#2c3e50")
        style.configure("Header.TLabel", font=("Segoe UI", 10, "bold"), foreground="#34495e")

    def create_widgets(self):
        main_frame = ttk.Frame(self.root, padding="15")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Título principal
        title_frame = ttk.Frame(main_frame)
        title_frame.pack(fill=tk.X, pady=(0, 15))
        ttk.Label(title_frame, text="🚀 TraceFlow - Lanzador de Servicios", style="Title.TLabel").pack()
        ttk.Label(title_frame, text="Administra los microservicios, backend y frontend con un solo click", font=("Segoe UI", 9), foreground="gray").pack()

        # Frame para la tabla de servicios
        table_frame = ttk.Frame(main_frame)
        table_frame.pack(fill=tk.BOTH, expand=True)

        # Cabecera de la tabla
        headers = ["Servicio", "Puerto", "Estado", "Acciones", "Logs"]
        for col, text in enumerate(headers):
            ttk.Label(table_frame, text=text, style="Header.TLabel").grid(row=0, column=col, sticky="w", padx=10, pady=5)

        separator = ttk.Separator(table_frame, orient='horizontal')
        separator.grid(row=1, column=0, columnspan=5, sticky="ew", pady=5)

        self.rows = []
        for idx, svc in enumerate(services):
            row_num = idx + 2

            # Nombre del servicio
            ttk.Label(table_frame, text=svc["name"], font=("Segoe UI", 10)).grid(row=row_num, column=0, sticky="w", padx=10, pady=5)

            # Puerto
            ttk.Label(table_frame, text=str(svc.get("port", "-")), font=("Segoe UI", 10)).grid(row=row_num, column=1, sticky="w", padx=10, pady=5)

            # Estado (con color)
            status_var = tk.StringVar(value="Stopped")
            lbl_status = ttk.Label(table_frame, textvariable=status_var, font=("Segoe UI", 10, "bold"), foreground="red")
            lbl_status.grid(row=row_num, column=2, sticky="w", padx=10, pady=5)

            # Botones de acciones (Start / Stop)
            btn_frame = ttk.Frame(table_frame)
            btn_frame.grid(row=row_num, column=3, sticky="w", padx=10, pady=5)
            
            btn_start = ttk.Button(btn_frame, text="▶️ Start", width=8, command=lambda s=svc: self.start_service(s))
            btn_start.pack(side=tk.LEFT, padx=2)
            
            btn_stop = ttk.Button(btn_frame, text="⏹️ Stop", width=8, command=lambda s=svc: self.stop_service(s))
            btn_stop.pack(side=tk.LEFT, padx=2)

            # Botón Ver logs
            btn_logs = ttk.Button(table_frame, text="📄 Ver logs", width=10, command=lambda s=svc: self.open_log(s))
            btn_logs.grid(row=row_num, column=4, sticky="w", padx=10, pady=5)

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
        global_frame.pack(fill=tk.X, pady=20)

        btn_start_all = ttk.Button(global_frame, text="🚀 Start All", command=self.start_all, style="Accent.TButton")
        btn_start_all.pack(side=tk.LEFT, padx=5)

        btn_stop_all = ttk.Button(global_frame, text="🛑 Stop All", command=self.stop_all, style="Danger.TButton")
        btn_stop_all.pack(side=tk.LEFT, padx=5)

        btn_dashboard = ttk.Button(global_frame, text="🌐 Abrir Dashboard", command=self.open_dashboard, style="Info.TButton")
        btn_dashboard.pack(side=tk.LEFT, padx=5)

        btn_clean_logs = ttk.Button(global_frame, text="🧹 Limpiar logs", command=self.clear_logs, style="Warning.TButton")
        btn_clean_logs.pack(side=tk.LEFT, padx=5)

        # Barra de estado (informativa)
        self.status_bar = ttk.Label(main_frame, text="Listo", relief=tk.SUNKEN, anchor=tk.W, font=("Segoe UI", 8))
        self.status_bar.pack(fill=tk.X, side=tk.BOTTOM, pady=(10, 0))

        # Información de logs
        ttk.Label(main_frame, text="📁 Los logs se guardan en la carpeta 'logs/'", font=("Segoe UI", 8), foreground="gray").pack(pady=(5, 0))

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

        # Verificar si el puerto está en uso
        if port and is_port_in_use(port):
            respuesta = messagebox.askyesno("Puerto ocupado",
                                            f"El puerto {port} ya está en uso.\n"
                                            "¿Desea matar el proceso que lo ocupa e iniciar el servicio?")
            if respuesta:
                if kill_process_on_port(port):
                    messagebox.showinfo("Info", f"Proceso en el puerto {port} eliminado.")
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
            self.update_status_bar(f"{name} iniciado correctamente.")
        except Exception as e:
            log_fd.close()
            messagebox.showerror("Error", f"No se pudo iniciar {name}:\n{e}")
            self.update_status_bar(f"Error al iniciar {name}: {e}")

    def stop_service(self, svc):
        name = svc["name"]
        if name in self.processes:
            proc, log_fd = self.processes[name]
            if proc.poll() is None:
                proc.terminate()
                try:
                    proc.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    # Forzar terminación con todo el árbol de procesos
                    subprocess.run(f"taskkill /F /T /PID {proc.pid}", shell=True, capture_output=True)
            log_fd.close()
            del self.processes[name]
            self.update_row_status(name, "Stopped", "red")
            self.update_status_bar(f"{name} detenido.")
        else:
            self.update_row_status(name, "Stopped", "red")
            self.update_status_bar(f"{name} ya estaba detenido.")

    def stop_all(self):
        """Detiene todos los servicios controlados y luego mata procesos huérfanos (sin matarse a sí mismo)."""
        # Primero detener los servicios que tenemos controlados
        for row in self.rows:
            self.stop_service(row["service"])
        # Esperar un momento para que terminen
        time.sleep(1)
        # Luego matar procesos huérfanos (python, node, etc.) excluyendo el actual
        killed = kill_all_related_processes()
        self.update_status_bar(f"Procesos huérfanos eliminados: {killed}")
        messagebox.showinfo("Completado", f"Todos los servicios detenidos. Se eliminaron {killed} procesos huérfanos (excepto este lanzador).")

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
        self.update_status_bar("Abriendo dashboard en el navegador...")

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
        self.update_status_bar(f"Logs limpiados: {cleared} archivos.")

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
        self.update_status_bar("Iniciando todos los servicios en orden...")
        for svc in self.get_start_order():
            name = svc["name"]
            if name not in self.processes or self.processes[name][0].poll() is not None:
                self.start_service(svc)
                time.sleep(2)
        self.update_status_bar("Todos los servicios solicitados fueron iniciados.")

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
                self.update_status_bar(f"Servicio {name} se detuvo inesperadamente.")
        self.root.after(1000, self.update_statuses)

    def update_status_bar(self, message):
        self.status_bar.config(text=message)
        self.root.after(3000, lambda: self.status_bar.config(text="Listo"))  # resetea después de 3 segundos

    def on_closing(self):
        self.running = False
        self.stop_all()   # Esto asegura limpiar procesos al cerrar
        self.root.destroy()

# ----------------------------------------------------------------------
if __name__ == "__main__":
    root = tk.Tk()
    app = ServiceLauncher(root)
    root.mainloop()