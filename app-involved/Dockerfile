# ====================================
# App Involved - Dockerfile
# ====================================

FROM python:3.11-slim

ENV TZ=America/Bogota \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    tzdata \
    postgresql-client \
    && ln -snf /usr/share/zoneinfo/$TZ /etc/localtime \
    && echo $TZ > /etc/timezone \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

RUN groupadd -r involved && useradd -r -g involved involved

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN chown -R involved:involved /app

USER involved

HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python3 -c "import urllib.request; urllib.request.urlopen('http://localhost:8004/health')" || exit 1

EXPOSE 8004

CMD ["gunicorn", "main:app", \
    "--workers", "4", \
    "--worker-class", "uvicorn.workers.UvicornWorker", \
    "--bind", "0.0.0.0:8004", \
    "--timeout", "120", \
    "--graceful-timeout", "30", \
    "--keep-alive", "5", \
    "--preload", \
    "--access-logfile", "-", \
    "--error-logfile", "-"]
