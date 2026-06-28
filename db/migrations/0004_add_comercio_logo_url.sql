-- 0004_add_comercio_logo_url.sql

ALTER TABLE IF EXISTS comercio
    ADD COLUMN IF NOT EXISTS logo_url VARCHAR(500) NULL;
