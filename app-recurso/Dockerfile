# ====================================
# App Recurso (Concesiones de Aguas) - Dockerfile
# ====================================

FROM python:3.11-slim

# Configurar timezone a Colombia
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
    && ln -snf /usr/share/zoneinfo/$TZ /etc/localtime \
    && echo $TZ > /etc/timezone \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Crear usuario no-root
RUN groupadd -r recurso && useradd -r -g recurso -d /home/recurso -m recurso

# Directorio de trabajo
WORKDIR /app

# Copiar requirements y instalar dependencias
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Paquete compartido satc_shared (service JWT, clientes inter-servicio, proceso
# de revisión). Viene del contexto adicional "shared": docker-compose lo define
# en additional_contexts; con docker build directo usar
#   --build-context shared=./shared
COPY --from=shared . /shared
RUN pip install --no-cache-dir /shared && rm -rf /shared

# Copiar código fuente
COPY . .

# Cambiar permisos
RUN mkdir -p /home/recurso && chown -R recurso:recurso /app /home/recurso

ENV HOME=/home/recurso

# Cambiar a usuario no-root
USER recurso

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import httpx; httpx.get('http://localhost:8006/health', timeout=5.0)" || exit 1

# Exponer puerto
EXPOSE 8006

# Comando de inicio con Gunicorn + Uvicorn workers (producción)
# 4 workers = equivalente a 2 réplicas × 2 workers, con --preload para copy-on-write RAM
CMD ["gunicorn", "main:app", \
    "--workers", "4", \
    "--worker-class", "uvicorn.workers.UvicornWorker", \
    "--bind", "0.0.0.0:8006", \
    "--timeout", "120", \
    "--graceful-timeout", "30", \
    "--keep-alive", "5", \
    "--preload", \
    "--access-logfile", "-", \
    "--error-logfile", "-"]
