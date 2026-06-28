-- 0002_auth.sql

CREATE TABLE IF NOT EXISTS token_recuperacion (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    usuario_id BIGINT NOT NULL REFERENCES usuario (id) ON DELETE CASCADE,
    token_hash CHAR(64) NOT NULL UNIQUE,
    expira_en TIMESTAMPTZ NOT NULL,
    usado BOOLEAN NOT NULL DEFAULT false,
    fecha_creacion TIMESTAMPTZ NOT NULL DEFAULT now(),
    fecha_uso TIMESTAMPTZ NULL
);

CREATE INDEX IF NOT EXISTS ix_token_recuperacion_usuario_id
    ON token_recuperacion (usuario_id);

CREATE INDEX IF NOT EXISTS ix_token_recuperacion_expira_en
    ON token_recuperacion (expira_en);
