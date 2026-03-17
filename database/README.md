#### Si la base de datos ya existe y quieres crear las tablas
psql -U postgres -d traceflow_db -f database/init.sql

# Si quieres recrear todo desde cero (¡CUIDADO! borra datos)
psql -U postgres -f database/init.sql

## Restaurar desde un backup
Si tienes un archivo de backup (por ejemplo, `backup_20250317.sql`), puedes restaurarlo con:


# Opción 1: Restaurar sobre la base de datos existente
psql -U postgres -d traceflow_db < backup/backup_20250317.sql

# Opción 2: Crear una nueva base de datos y restaurar
createdb -U postgres traceflow_db_nueva
psql -U postgres -d traceflow_db_nueva < backup/backup_20250317.sql