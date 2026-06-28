-- 0007_item_no_asignado.sql

CREATE TABLE IF NOT EXISTS item_no_asignado (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    carrito_distribuido_id BIGINT NOT NULL REFERENCES carrito_distribuido (id) ON DELETE CASCADE,
    item_carrito_id BIGINT NOT NULL REFERENCES item_carrito (id),
    producto_id BIGINT NOT NULL,
    nombre_producto VARCHAR(255) NOT NULL,
    cantidad INTEGER NOT NULL CHECK (cantidad >= 1)
);