\set ON_ERROR_STOP on
DO $$
BEGIN
    IF obj_description('p2_benchmark'::regnamespace, 'pg_namespace')
        IS DISTINCT FROM 'NexaCart Portfolio 2 benchmark v1' THEN
        RAISE EXCEPTION 'Unrecognised benchmark schema; inspect it before proceeding';
    END IF;
    IF (SELECT COUNT(*) FROM p2_benchmark.customers) <> 10000
       OR (SELECT COUNT(*) FROM p2_benchmark.addresses) <> 10000
       OR (SELECT COUNT(*) FROM p2_benchmark.categories) <> 6
       OR (SELECT COUNT(*) FROM p2_benchmark.products) <> 18
       OR (SELECT COUNT(*) FROM p2_benchmark.orders) <> 200000
       OR (SELECT COUNT(*) FROM p2_benchmark.order_items) <> 600000 THEN
        RAISE EXCEPTION 'Benchmark row counts differ from the documented dataset';
    END IF;
    IF EXISTS (SELECT customer_id FROM p2_benchmark.orders
               GROUP BY customer_id HAVING COUNT(*) <> 20) THEN
        RAISE EXCEPTION 'Expected 20 orders per customer';
    END IF;
    IF EXISTS (
        SELECT o.order_id FROM p2_benchmark.orders o
        LEFT JOIN p2_benchmark.order_items oi ON oi.order_id = o.order_id
        GROUP BY o.order_id, o.total_amount
        HAVING COUNT(oi.order_item_id) <> 3
            OR SUM(oi.quantity * oi.unit_price) IS DISTINCT FROM o.total_amount
    ) THEN
        RAISE EXCEPTION 'Benchmark item counts or order totals are inconsistent';
    END IF;
    IF EXISTS (SELECT 1 FROM p2_benchmark.orders o
               JOIN p2_benchmark.addresses a ON a.address_id = o.shipping_address_id
               WHERE a.customer_id <> o.customer_id) THEN
        RAISE EXCEPTION 'Benchmark delivery address does not belong to customer';
    END IF;
END;
$$;
SELECT 'PASS: counts, 20 orders/customer, 3 items/order, totals, address ownership' AS validation;
