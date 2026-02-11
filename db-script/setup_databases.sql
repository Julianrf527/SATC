-- Script para crear/recrear las 3 bases de datos del sistema SATC
-- Este script debe ejecutarse con un usuario con privilegios suficientes (ej: postgres)

-- Desconectar usuarios activos y eliminar bases de datos si existen
SELECT pg_terminate_backend(pg_stat_activity.pid)
FROM pg_stat_activity
WHERE pg_stat_activity.datname IN ('user_db', 'expedientes_db', 'documentos_db')
  AND pid <> pg_backend_pid();

DROP DATABASE IF EXISTS user_db;
DROP DATABASE IF EXISTS expedientes_db;
DROP DATABASE IF EXISTS documentos_db;

-- Crear las bases de datos
CREATE DATABASE user_db
    WITH 
    OWNER = postgres
    ENCODING = 'UTF8'
    TABLESPACE = pg_default
    CONNECTION LIMIT = -1;

CREATE DATABASE expedientes_db
    WITH 
    OWNER = postgres
    ENCODING = 'UTF8'
    TABLESPACE = pg_default
    CONNECTION LIMIT = -1;

CREATE DATABASE documentos_db
    WITH 
    OWNER = postgres
    ENCODING = 'UTF8'
    TABLESPACE = pg_default
    CONNECTION LIMIT = -1;
