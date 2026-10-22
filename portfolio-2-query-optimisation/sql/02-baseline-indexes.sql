-- Remove only the two experimental indexes. Retain every PK/UNIQUE index.
DROP INDEX IF EXISTS p2_benchmark.p2_orders_customer_created_idx;
DROP INDEX IF EXISTS p2_benchmark.p2_orders_fulfilled_created_idx;
