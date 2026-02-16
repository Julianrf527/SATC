# ====================================
# App Docs - Dockerfile
# ====================================

FROM python:3.11-slim

# Configurar timezone a Colombia (Caso 10: Timezone consistente)
ENV TZ=America/Bogota \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Instalar dependencias del sistema
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    tzdata \
    postgresql-client \
    libmagic1 \
    && ln -snf /usr/share/zoneinfo/$TZ /etc/localtime \
    && echo $TZ > /etc/timezone \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Crear usuario no-root
RUN groupadd -r appdocs && useradd -r -g appdocs appdocs

# Directorio de trabajo
WORKDIR /app

# Copiar requirements y instalar dependencias
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código fuente
COPY . .

# Crear directorio para uploads seguros (Caso 8: Seguridad archivos)
RUN mkdir -p /app/secure-uploads && \
    chown -R appdocs:appdocs /app

# Cambiar a usuario no-root
USER appdocs

# Health check (Caso 3: Alta Disponibilidad)
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import httpx; httpx.get('http://localhost:8003/health', timeout=5.0)" || exit 1

# Exponer puerto
EXPOSE 8003

# Comando de inicio con Gunicorn + Uvicorn workers (producción)
CMD ["gunicorn", "main:app", \
    "--workers", "1", \
    "--worker-class", "uvicorn.workers.UvicornWorker", \
    "--bind", "0.0.0.0:8003", \
    "--timeout", "120", \
    "--graceful-timeout", "30", \
    "--keep-alive", "5", \
    "--access-logfile", "-", \
    "--error-logfile", "-"]
