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

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
