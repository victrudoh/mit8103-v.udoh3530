\set ON_ERROR_STOP on

BEGIN;

CREATE SCHEMA IF NOT EXISTS p3_concurrency;

CREATE TABLE IF NOT EXISTS p3_concurrency.stock_control (
    product_id BIGINT PRIMARY KEY
        REFERENCES public.products(product_id),
    available_quantity INTEGER NOT NULL
        CHECK (available_quantity >= 0),
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS p3_concurrency.reservation_events (
    reservation_id BIGSERIAL PRIMARY KEY,
    request_reference VARCHAR(100) NOT NULL UNIQUE,
    product_id BIGINT NOT NULL
        REFERENCES p3_concurrency.stock_control(product_id),
    quantity INTEGER NOT NULL CHECK (quantity > 0),
    outcome VARCHAR(30) NOT NULL
        CHECK (outcome IN ('committed', 'rolled_back')),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- This is a private lab copy of product 3's stock, not the operational inventory.
TRUNCATE TABLE p3_concurrency.reservation_events,
               p3_concurrency.stock_control
RESTART IDENTITY;

INSERT INTO p3_concurrency.stock_control (product_id, available_quantity)
VALUES (3, 12);

COMMIT;

SELECT product_id, available_quantity
FROM p3_concurrency.stock_control;
