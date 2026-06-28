# syntax=docker/dockerfile:1
FROM node:22-bookworm-slim AS builder

WORKDIR /repo

COPY package.json package-lock.json* ./
COPY apps/web/package.json ./apps/web/package.json
COPY packages/shared/package.json ./packages/shared/package.json

RUN npm install

COPY packages/shared ./packages/shared
COPY apps/web ./apps/web

ARG VITE_API_BASE_URL=http://localhost:8000
ENV VITE_API_BASE_URL=${VITE_API_BASE_URL}

WORKDIR /repo/apps/web
RUN npm run build

FROM nginx:alpine AS production

COPY --from=builder /repo/apps/web/dist /usr/share/nginx/html
COPY apps/web/nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80
