#!/usr/bin/env python3
"""
Script unificado para levantar backend y frontend juntos.
Funciona en Windows, Linux y Mac.
"""

import os
import sys
import subprocess
import time
import platform
import signal
from pathlib import Path

# Colores ANSI (opcional)
class Colors:
    GREEN = '\033[92m' if platform.system() != 'Windows' else ''
    RED = '\033[91m' if platform.system() != 'Windows' else ''
    YELLOW = '\033[93m' if platform.system() != 'Windows' else ''
    CYAN = '\033[96m' if platform.system() != 'Windows' else ''
    RESET = '\033[0m' if platform.system() != 'Windows' else ''

    @classmethod
    def green(cls, text): return f"{cls.GREEN}{text}{cls.RESET}"
    @classmethod
    def red(cls, text): return f"{cls.RED}{text}{cls.RESET}"
    @classmethod
    def yellow(cls, text): return f"{cls.YELLOW}{text}{cls.RESET}"
    @classmethod
    def cyan(cls, text): return f"{cls.CYAN}{text}{cls.RESET}"

def check_port(port):
    """Verifica si un puerto está libre"""
    import socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind(('localhost', port))
            return True
        except socket.error:
            return False

def run_command(cmd, cwd=None, shell=True):
    """Ejecuta un comando y retorna el proceso"""
    if platform.system() == 'Windows':
        return subprocess.Popen(cmd, cwd=cwd, shell=shell, creationflags=subprocess.CREATE_NEW_CONSOLE)
    else:
        # En Linux/Mac, abrimos en una nueva terminal si es posible
        if sys.platform == 'darwin':  # Mac
            terminal_cmd = ['open', '-a', 'Terminal', '--args'] + cmd.split()
            return subprocess.Popen(terminal_cmd, cwd=cwd)
        else:  # Linux (diferentes terminales)
            terminals = ['gnome-terminal', 'xterm', 'konsole']
            for term in terminals:
                try:
                    if term == 'gnome-terminal':
                        return subprocess.Popen([term, '--', 'bash', '-c', f"{cmd}; exec bash"], cwd=cwd)
                    elif term == 'xterm':
                        return subprocess.Popen([term, '-e', f"{cmd}; bash"], cwd=cwd)
                except FileNotFoundError:
                    continue
            # Fallback: ejecutar en la misma terminal
            return subprocess.Popen(cmd, cwd=cwd, shell=True)

def main():
    print(Colors.cyan("="*50))
    print(Colors.cyan("TraceFlow Core - Levantar Backend y Frontend"))
    print(Colors.cyan("="*50))

    # Verificar puertos
    if not check_port(8000):
        print(Colors.red(f"❌ El puerto 8000 ya está en uso"))
        sys.exit(1)
    if not check_port(4200):
        print(Colors.red(f"❌ El puerto 4200 ya está en uso"))
        sys.exit(1)

    # Verificar estructura de carpetas
    script_dir = Path(__file__).parent.absolute()
    project_root = script_dir.parent
    backend_dir = project_root / "backend"
    frontend_dir = project_root / "frontend"

    if not backend_dir.exists():
        print(Colors.red(f"❌ No se encuentra la carpeta backend en {backend_dir}"))
        sys.exit(1)
    if not frontend_dir.exists():
        print(Colors.red(f"❌ No se encuentra la carpeta frontend en {frontend_dir}"))
        sys.exit(1)

    print(Colors.green("✅ Estructura de carpetas verificada"))

    # Activar entorno virtual (opcional, en Windows)
    backend_cmd = "python manage.py runserver"
    if platform.system() == 'Windows':
        # Verificar si existe venv
        if (backend_dir / "venv" / "Scripts" / "activate").exists():
            backend_cmd = "venv\\Scripts\\activate && python manage.py runserver"
        elif (backend_dir / "venv" / "Scripts" / "python.exe").exists():
            backend_cmd = "venv\\Scripts\\python.exe manage.py runserver"

    frontend_cmd = "ng serve -o"

    print(Colors.yellow("\n🚀 Iniciando backend Django..."))
    backend_proc = run_command(backend_cmd, cwd=backend_dir)
    time.sleep(3)

    print(Colors.yellow("🚀 Iniciando frontend Angular..."))
    frontend_proc = run_command(frontend_cmd, cwd=frontend_dir)

    print(Colors.green("\n✅ Backend y frontend iniciados correctamente"))
    print(Colors.cyan(f"📌 Backend:  http://localhost:8000"))
    print(Colors.cyan(f"📌 Frontend: http://localhost:4200"))

    print(Colors.yellow("\n⚠️  Presiona Ctrl+C para detener ambos servicios"))

    try:
        # Mantener el script corriendo
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print(Colors.yellow("\n🛑 Deteniendo servicios..."))
        backend_proc.terminate()
        frontend_proc.terminate()
        print(Colors.green("✅ Servicios detenidos"))

if __name__ == "__main__":
    main()