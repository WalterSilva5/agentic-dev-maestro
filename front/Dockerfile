# Stage 1: Build Angular (requires Node 20+)
FROM node:20-slim AS builder
WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci --legacy-peer-deps

COPY . .
RUN npm run build

# Stage 2: Serve with Nginx
FROM nginx:alpine

COPY --from=builder /app/dist/fullstack-template-front/browser /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Gera o config.json a partir de env no start (configurável por ambiente, sem rebuild).
# O entrypoint oficial do nginx executa os scripts de /docker-entrypoint.d/ antes de subir.
COPY docker-config-entrypoint.sh /docker-entrypoint.d/40-maestro-config.sh
RUN chmod +x /docker-entrypoint.d/40-maestro-config.sh

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
