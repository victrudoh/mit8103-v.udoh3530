\set ON_ERROR_STOP on
\pset pager off
\echo Creating isolated NexaCart benchmark data
BEGIN;

-- Fail if this schema exists. Never replace the user's existing benchmark.
CREATE SCHEMA p2_benchmark;
COMMENT ON SCHEMA p2_benchmark IS 'NexaCart Portfolio 2 benchmark v1';

-- Copy types, NOT NULL/CHECK constraints and PK/UNIQUE indexes, but not defaults:
-- BIGSERIAL defaults would otherwise refer to the original public sequences.
CREATE TABLE p2_benchmark.customers
    (LIKE public.customers INCLUDING CONSTRAINTS INCLUDING INDEXES);
CREATE TABLE p2_benchmark.addresses
    (LIKE public.addresses INCLUDING CONSTRAINTS INCLUDING INDEXES);
CREATE TABLE p2_benchmark.categories
    (LIKE public.categories INCLUDING CONSTRAINTS INCLUDING INDEXES);
CREATE TABLE p2_benchmark.products
    (LIKE public.products INCLUDING CONSTRAINTS INCLUDING INDEXES);
CREATE TABLE p2_benchmark.orders
    (LIKE public.orders INCLUDING CONSTRAINTS INCLUDING INDEXES);
CREATE TABLE p2_benchmark.order_items
    (LIKE public.order_items INCLUDING CONSTRAINTS INCLUDING INDEXES);

-- LIKE does not copy foreign keys. Keep all relationships within this schema.
ALTER TABLE p2_benchmark.addresses ADD FOREIGN KEY (customer_id)
    REFERENCES p2_benchmark.customers (customer_id);
ALTER TABLE p2_benchmark.products ADD FOREIGN KEY (category_id)
    REFERENCES p2_benchmark.categories (category_id);
ALTER TABLE p2_benchmark.orders ADD FOREIGN KEY (customer_id)
    REFERENCES p2_benchmark.customers (customer_id);
ALTER TABLE p2_benchmark.orders ADD FOREIGN KEY (shipping_address_id)
    REFERENCES p2_benchmark.addresses (address_id);
ALTER TABLE p2_benchmark.order_items ADD FOREIGN KEY (order_id)
    REFERENCES p2_benchmark.orders (order_id);
ALTER TABLE p2_benchmark.order_items ADD FOREIGN KEY (product_id)
    REFERENCES p2_benchmark.products (product_id);

INSERT INTO p2_benchmark.categories SELECT * FROM public.categories;
INSERT INTO p2_benchmark.products SELECT * FROM public.products;

DO $$
BEGIN
    IF (SELECT COUNT(*) FROM p2_benchmark.categories) <> 6
       OR (SELECT COUNT(*) FROM p2_benchmark.products) <> 18
       OR (SELECT MIN(product_id) FROM p2_benchmark.products) <> 1
       OR (SELECT MAX(product_id) FROM p2_benchmark.products) <> 18 THEN
        RAISE EXCEPTION 'Benchmark requires the Portfolio 1 catalogue (6 categories, product IDs 1-18)';
    END IF;
END;
$$;

INSERT INTO p2_benchmark.customers
    (customer_id, first_name, last_name, email, phone, created_at)
SELECT g, 'Benchmark', 'Customer ' || g,
       'customer' || g || '@benchmark.nexacart.example', NULL,
       TIMESTAMP '2025-12-01 00:00:00'
FROM generate_series(1, 10000) g;

INSERT INTO p2_benchmark.addresses
    (address_id, customer_id, street, city, state, country)
SELECT g, g, 'Synthetic address ' || g, 'Test City', 'Test State', 'Nigeria'
FROM generate_series(1, 10000) g;

INSERT INTO p2_benchmark.orders
    (order_id, customer_id, shipping_address_id, total_amount, status, created_at)
SELECT g, 1 + (g - 1) % 10000, 1 + (g - 1) % 10000, 0,
       (ARRAY['pending', 'confirmed', 'processing', 'shipped', 'delivered',
              'delivered', 'delivered', 'delivered', 'cancelled', 'delivered'])[
                  1 + (g * 17 + g / 1000) % 10],
       TIMESTAMP '2026-01-01 00:00:00' + (g - 1) * INTERVAL '1 minute'
FROM generate_series(1, 200000) g;

INSERT INTO p2_benchmark.order_items
    (order_item_id, order_id, product_id, quantity, unit_price)
SELECT (o.order_id - 1) * 3 + line, o.order_id, p.product_id,
       1 + (o.order_id + line) % 3, p.price
FROM p2_benchmark.orders o
CROSS JOIN generate_series(1, 3) line
JOIN p2_benchmark.products p ON p.product_id = 1 + (o.order_id * 7 + line - 1) % 18;

UPDATE p2_benchmark.orders o SET total_amount = items.amount
FROM (SELECT order_id, SUM(quantity * unit_price) AS amount
      FROM p2_benchmark.order_items GROUP BY order_id) items
WHERE items.order_id = o.order_id;

COMMIT;

-- Establish the same clean, analysed state before either measurement phase.
VACUUM (ANALYZE) p2_benchmark.customers;
VACUUM (ANALYZE) p2_benchmark.addresses;
VACUUM (ANALYZE) p2_benchmark.categories;
VACUUM (ANALYZE) p2_benchmark.products;
VACUUM (ANALYZE) p2_benchmark.orders;
VACUUM (ANALYZE) p2_benchmark.order_items;

SELECT 'customers' AS table_name, COUNT(*) AS rows FROM p2_benchmark.customers
UNION ALL SELECT 'addresses', COUNT(*) FROM p2_benchmark.addresses
UNION ALL SELECT 'categories', COUNT(*) FROM p2_benchmark.categories
UNION ALL SELECT 'products', COUNT(*) FROM p2_benchmark.products
UNION ALL SELECT 'orders', COUNT(*) FROM p2_benchmark.orders
UNION ALL SELECT 'order_items', COUNT(*) FROM p2_benchmark.order_items;
