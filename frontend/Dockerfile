# ====================================
# Frontend - Dockerfile Multi-Stage
# ====================================
# Stage 1: Build
FROM node:20-alpine AS builder

WORKDIR /app

# Copiar archivos de dependencias
COPY package*.json ./

# Instalar dependencias
RUN npm ci --legacy-peer-deps

# Copiar código fuente
COPY . .

# Argument para la URL del API (se pasa desde docker-compose)
ARG VITE_API_URL
ENV VITE_API_URL=${VITE_API_URL}

# Build para producción
RUN npm run build

# ====================================
# Stage 2: Production con Nginx
# ====================================
FROM nginx:1.25-alpine

# Copiar configuración de Nginx
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Copiar archivos build desde el stage anterior
COPY --from=builder /app/dist /usr/share/nginx/html

# Crear script para inyectar variables de entorno en runtime
COPY docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

# Exponer puerto
EXPOSE 80

# Healthcheck
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
  CMD wget -q -O /dev/null http://127.0.0.1/ || exit 1

# Entrypoint customizado para inyectar env vars
ENTRYPOINT ["/docker-entrypoint.sh"]
CMD ["nginx", "-g", "daemon off;"]
