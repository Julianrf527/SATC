@echo off
REM Script Batch para recrear todas las bases de datos del sistema SATC
REM Asegúrate de tener psql en tu PATH o ajusta la ruta completa

setlocal

REM Configuración
set PG_HOST=localhost
set PG_PORT=5432
set PG_USER=postgres
set SCRIPT_DIR=%~dp0

echo ========================================
echo SATC - Recreacion de Bases de Datos
echo ========================================
echo.

REM Solicitar contraseña
set /p PGPASSWORD="Ingrese la contraseña de PostgreSQL para el usuario '%PG_USER%': "
echo.

echo Paso 1: Eliminando y recreando bases de datos...
psql -h %PG_HOST% -p %PG_PORT% -U %PG_USER% -d postgres -f "%SCRIPT_DIR%setup_databases.sql"
if errorlevel 1 (
    echo ERROR al crear las bases de datos
    set PGPASSWORD=
    exit /b 1
)
echo [OK] Bases de datos creadas exitosamente
echo.

echo Paso 2: Restaurando user_db...
psql -h %PG_HOST% -p %PG_PORT% -U %PG_USER% -d user_db -f "%SCRIPT_DIR%user_db.sql"
if errorlevel 1 (
    echo ERROR al restaurar user_db
    set PGPASSWORD=
    exit /b 1
)
echo [OK] user_db restaurada exitosamente
echo.

echo Paso 3: Restaurando expedientes_db...
psql -h %PG_HOST% -p %PG_PORT% -U %PG_USER% -d expedientes_db -f "%SCRIPT_DIR%expedientes_db.sql"
if errorlevel 1 (
    echo ERROR al restaurar expedientes_db
    set PGPASSWORD=
    exit /b 1
)
echo [OK] expedientes_db restaurada exitosamente
echo.

echo Paso 4: Restaurando documentos_db...
psql -h %PG_HOST% -p %PG_PORT% -U %PG_USER% -d documentos_db -f "%SCRIPT_DIR%documentos_db.sql"
if errorlevel 1 (
    echo ERROR al restaurar documentos_db
    set PGPASSWORD=
    exit /b 1
)
echo [OK] documentos_db restaurada exitosamente
echo.

REM Limpiar contraseña
set PGPASSWORD=

echo ========================================
echo PROCESO COMPLETADO EXITOSAMENTE
echo ========================================
echo.
echo Las 3 bases de datos han sido recreadas:
echo   - user_db
echo   - expedientes_db
echo   - documentos_db
echo.

pause
endlocal
