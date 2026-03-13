# ====================================
# App Users - Dockerfile
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
    curl \
    && ln -snf /usr/share/zoneinfo/$TZ /etc/localtime \
    && echo $TZ > /etc/timezone \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Crear usuario no-root
RUN groupadd -r appusers && useradd -r -g appusers appusers

# Directorio de trabajo
WORKDIR /app

# Copiar requirements y instalar dependencias
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código fuente
COPY . .

# Crear directorio de scripts si no existe
RUN mkdir -p scripts

# Cambiar ownership
RUN chown -R appusers:appusers /app

# Cambiar a usuario no-root
USER appusers

# Health check (Caso 3: Alta Disponibilidad)
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import httpx; httpx.get('http://localhost:8001/health', timeout=5.0)" || exit 1

# Exponer puerto
EXPOSE 8001

# Comando de inicio con Gunicorn + Uvicorn workers (producción)
# 4 workers = equivalente a 2 réplicas × 2 workers, con --preload para copy-on-write RAM
CMD ["gunicorn", "main:app", \
    "--workers", "4", \
    "--worker-class", "uvicorn.workers.UvicornWorker", \
    "--bind", "0.0.0.0:8001", \
    "--timeout", "120", \
    "--graceful-timeout", "30", \
    "--keep-alive", "5", \
    "--preload", \
    "--access-logfile", "-", \
    "--error-logfile", "-"]

