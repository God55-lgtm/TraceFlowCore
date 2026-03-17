@echo off
echo Iniciando Angular...
start http://localhost:4200
start cmd /k "cd frontend/traceflow-dashboard && ng serve"

echo Iniciando Django...
cd traceflow_backend
start cmd /k "python manage.py runserver"