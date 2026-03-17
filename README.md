# TraceFlow Core - Componente de Logging Distribuido con Trazabilidad

TraceFlow Core es un componente de software para logging distribuido y trazabilidad en arquitecturas de microservicios. Proporciona generación automática de identificadores de correlación (traceId, spanId), propagación de contexto mediante W3C Trace Context, almacenamiento centralizado en PostgreSQL y un dashboard Angular para visualización y auditoría.

## Estructura del Proyecto
traceflow-core/
├── backend/ # Backend Django (API REST)
├── frontend/ # Dashboard Angular
├── microservicios/ # Microservicios de ejemplo (FastAPI)
├── database/ # Scripts de base de datos
├── docs/ # Documentación
├── scripts/ # Scripts de utilidad
└── README.md

## Requisitos Previos

- Python 3.11+
- Node.js 18+ y npm
- PostgreSQL 16+
- (Opcional) Docker y Docker Compose

## Instalación Rápida

1. **Clonar el repositorio**
   ```bash
   git clone https://github.com/god55-lgtm/traceflow-core.git
   cd traceflow-core

**Configurar la base de datos**
cd database
psql -U postgres -f init.sql
Backend Django

**Configurar Backend**
cd backend
python -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
Frontend Angular

**Configurar Frontend**
bash
cd frontend
npm install
ng serve
Microservicios (opcional)


**Microservicios**
bash
cd microservicios/scripts
./levantar_todos.ps1  # En Windows PowerShell
# o python launcher.py
Accede al dashboard en http://localhost:4200 (usuario: admin / contraseña: admin).

