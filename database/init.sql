-- =====================================================
-- TraceFlow Core - Script de inicialización de base de datos
-- =====================================================

-- Eliminar la base de datos si existe (¡CUIDADO! Esto borra todos los datos)
-- DROP DATABASE IF EXISTS traceflow_db;

-- Crear la base de datos (si no existe)
CREATE DATABASE traceflow_db;

-- Conectarse a la base de datos (útil para ejecución manual)
\c traceflow_db;

-- =====================================================
-- Tabla: traces (almacena todos los spans)
-- =====================================================
CREATE TABLE IF NOT EXISTS traces (
    id BIGSERIAL PRIMARY KEY,
    trace_id VARCHAR(32) NOT NULL,
    span_id VARCHAR(16) NOT NULL,
    parent_span_id VARCHAR(16),
    data JSONB NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Índices para búsquedas rápidas
CREATE INDEX IF NOT EXISTS idx_traces_trace_id ON traces(trace_id);
CREATE INDEX IF NOT EXISTS idx_traces_created_at ON traces(created_at);
CREATE INDEX IF NOT EXISTS idx_traces_parent_span_id ON traces(parent_span_id);

-- Índice GIN para búsquedas dentro del campo JSON (opcional, mejora rendimiento)
CREATE INDEX IF NOT EXISTS idx_traces_data ON traces USING GIN (data);

-- Comentarios (opcional, para documentación)
COMMENT ON TABLE traces IS 'Almacena todos los spans generados por los microservicios';
COMMENT ON COLUMN traces.trace_id IS 'Identificador único de la traza (32 caracteres hexadecimales)';
COMMENT ON COLUMN traces.span_id IS 'Identificador del span actual (16 caracteres hexadecimales)';
COMMENT ON COLUMN traces.parent_span_id IS 'Identificador del span padre (null si es el span raíz)';
COMMENT ON COLUMN traces.data IS 'Datos completos del span en formato JSONB';
COMMENT ON COLUMN traces.created_at IS 'Momento en que se insertó el span (automático)';

-- =====================================================
-- Tabla: users (para autenticación en microservicios)
-- =====================================================
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    email VARCHAR(100),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_login TIMESTAMP WITH TIME ZONE
);

CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);

COMMENT ON TABLE users IS 'Usuarios para autenticación en microservicios';
COMMENT ON COLUMN users.username IS 'Nombre de usuario único';
COMMENT ON COLUMN users.password_hash IS 'Hash de la contraseña (bcrypt)';
COMMENT ON COLUMN users.email IS 'Correo electrónico del usuario';
COMMENT ON COLUMN users.created_at IS 'Fecha de registro';
COMMENT ON COLUMN users.last_login IS 'Último inicio de sesión';

-- =====================================================
-- Datos de ejemplo (opcional, puedes comentar si no los necesitas)
-- =====================================================

-- Insertar usuario admin por defecto (contraseña: Secret123!)
-- El hash corresponde a bcrypt de "Secret123!"
INSERT INTO users (username, password_hash, email)
VALUES (
    'admin',
    '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBPj2NqK5X5yKq',
    'admin@traceflow.local'
) ON CONFLICT (username) DO NOTHING;

-- Insertar usuarios de ejemplo
INSERT INTO users (username, password_hash, email) VALUES
    ('ricardo.perez', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBPj2NqK5X5yKq', 'ricardo@email.com'),
    ('ana.garcia',    '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBPj2NqK5X5yKq', 'ana.garcia@email.com'),
    ('carlos.lopez',  '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBPj2NqK5X5yKq', 'carlos.l@email.com'),
    ('laura.martin',  '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBPj2NqK5X5yKq', 'laura.m@email.com'),
    ('jose.rodriguez','$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBPj2NqK5X5yKq', 'jose.r@email.com')
ON CONFLICT (username) DO NOTHING;

-- Insertar algunas trazas de ejemplo (opcional, para pruebas)
-- Nota: Los datos son simulados, puedes omitir esta parte si prefieres empezar vacío
INSERT INTO traces (trace_id, span_id, parent_span_id, data) VALUES
    ('a1b2c3d4e5f6789012345678901234567', 'span1234567890', NULL, '{"service_name": "tienda-service", "path": "/health", "method": "GET", "status_code": 200, "duration_ms": 45}'),
    ('a1b2c3d4e5f6789012345678901234567', 'span2345678901', 'span1234567890', '{"service_name": "pago-service", "path": "/pay", "method": "POST", "status_code": 200, "duration_ms": 120}'),
    ('b2c3d4e5f67890123456789012345678a', 'span3456789012', NULL, '{"service_name": "inventario-service", "path": "/stock/1", "method": "GET", "status_code": 200, "duration_ms": 23}')
ON CONFLICT DO NOTHING;

-- =====================================================
-- Verificación final
-- =====================================================
SELECT '✅ Base de datos traceflow_db inicializada correctamente' AS mensaje;
SELECT '   - Tabla traces: ' || (SELECT COUNT(*) FROM traces) || ' registros' AS info;
SELECT '   - Tabla users:  ' || (SELECT COUNT(*) FROM users) || ' registros' AS info;