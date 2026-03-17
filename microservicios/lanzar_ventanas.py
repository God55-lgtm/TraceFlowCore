import subprocess
import os
import sys

services = [
    {"name": "tienda", "port": 8001, "folder": "tienda"},
    {"name": "pago", "port": 8002, "folder": "pago"},
    {"name": "inventario", "port": 8004, "folder": "inventario"},
    {"name": "notificacion", "port": 8005, "folder": "notificacion"},
]

for svc in services:
    folder = os.path.join(os.getcwd(), svc["folder"])
    if not os.path.exists(folder):
        print(f"❌ Carpeta {folder} no encontrada")
        continue

    cmd = f'cd /d "{folder}" && python -m uvicorn main:app --reload --port {svc["port"]}'
    # En Windows, START abre una nueva ventana de cmd
    subprocess.Popen(f'start "TraceFlow - {svc["name"]}" cmd /k "{cmd}"', shell=True)

print("✅ Microservicios lanzados en ventanas separadas.")
print("Cierra cada ventana manualmente para detener el servicio.")