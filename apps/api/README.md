# apps/api — FastAPI

API REST bajo `/api/v1`.

## Variables requeridas

- `DATABASE_URL`
- `API_JWT_SECRET`
- `JWT_EXPIRATION_MINUTES` (default `30`)
- `AUTH_URL` (usado para construir enlace de recuperación)
- `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_FROM`
- `RESET_TOKEN_TTL_SECONDS` (default `3600`)