# ====================================
# API Gateway - Dockerfile
# ====================================

FROM python:3.11-slim

# Configurar timezone a Colombia (Caso 10: Timezone consistente)
ENV TZ=America/Bogota \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Instalar timezone data
RUN apt-get update && \
    apt-get install -y --no-install-recommends tzdata curl && \
    ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && \
    echo $TZ > /etc/timezone && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Crear usuario no-root para seguridad
RUN groupadd -r apigateway && useradd -r -g apigateway apigateway

# Directorio de trabajo
WORKDIR /app

# Copiar requirements y instalar dependencias
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código fuente
COPY . .

# Cambiar ownership
RUN chown -R apigateway:apigateway /app

# Cambiar a usuario no-root
USER apigateway

# Health check (Caso 3: Alta Disponibilidad)
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import httpx; httpx.get('http://localhost:8000/health', timeout=5.0)" || exit 1

# Exponer puerto
EXPOSE 8000

# Comando de inicio con Gunicorn + Uvicorn workers (producción)
# 6 workers = equivalente a 3 réplicas × 2 workers, con --preload para copy-on-write RAM
CMD ["gunicorn", "main:app", \
    "--workers", "6", \
    "--worker-class", "uvicorn.workers.UvicornWorker", \
    "--bind", "0.0.0.0:8000", \
    "--timeout", "120", \
    "--graceful-timeout", "30", \
    "--keep-alive", "5", \
    "--preload", \
    "--access-logfile", "-", \
    "--error-logfile", "-", \
    "--forwarded-allow-ips", "*", \
    "--proxy-protocol"]

