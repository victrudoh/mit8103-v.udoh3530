\set ON_ERROR_STOP on
\pset pager off
\pset null '(none)'
\echo NexaCart Step 6: constraint and relationship validation

BEGIN;
SET LOCAL search_path = public, pg_temp;
SET LOCAL client_min_messages = warning;

CREATE TEMP TABLE validation_results (
    test_number INTEGER GENERATED ALWAYS AS IDENTITY,
    test_name TEXT NOT NULL,
    result TEXT NOT NULL,
    sqlstate TEXT,
    constraint_name TEXT,
    error_message TEXT
) ON COMMIT DROP;

CREATE FUNCTION pg_temp.assert_valid(test_name TEXT, condition BOOLEAN)
RETURNS VOID LANGUAGE plpgsql AS $$
BEGIN
    IF condition IS DISTINCT FROM TRUE THEN
        RAISE EXCEPTION 'FAIL: %', test_name;
    END IF;
    INSERT INTO validation_results (test_name, result)
    VALUES (test_name, 'PASS');
END;
$$;

-- The exception block rolls back each attempted insert. A different error or
-- an unexpectedly accepted insert fails the script instead of counting as PASS.
CREATE FUNCTION pg_temp.expect_rejection(
    test_name TEXT, statement TEXT, expected_state TEXT,
    expected_constraint TEXT DEFAULT NULL, expected_column TEXT DEFAULT NULL
) RETURNS VOID LANGUAGE plpgsql AS $$
DECLARE
    actual_state TEXT;
    actual_constraint TEXT;
    actual_column TEXT;
    actual_message TEXT;
BEGIN
    BEGIN
        EXECUTE statement;
    EXCEPTION WHEN OTHERS THEN
        GET STACKED DIAGNOSTICS
            actual_state = RETURNED_SQLSTATE,
            actual_constraint = CONSTRAINT_NAME,
            actual_column = COLUMN_NAME,
            actual_message = MESSAGE_TEXT;
    END;
    IF actual_state IS NULL THEN
        RAISE EXCEPTION 'FAIL: % - invalid insert was accepted', test_name;
    END IF;
    IF actual_state <> expected_state
        OR (expected_constraint IS NOT NULL
            AND actual_constraint IS DISTINCT FROM expected_constraint)
        OR (expected_column IS NOT NULL
            AND actual_column IS DISTINCT FROM expected_column) THEN
        RAISE EXCEPTION 'FAIL: % - unexpected error [%] %',
            test_name, actual_state, actual_message;
    END IF;
    INSERT INTO validation_results
        (test_name, result, sqlstate, constraint_name, error_message)
    VALUES (test_name, 'PASS', actual_state,
        NULLIF(actual_constraint, ''), actual_message);
END;
$$;

-- Explicit negative IDs avoid advancing the application's BIGSERIAL sequences:
-- nextval() calls are not undone by ROLLBACK. ID collisions fail the run.
INSERT INTO customers (customer_id, first_name, last_name, email)
VALUES (-8103001, 'Validation', 'Customer', 'step6@nexacart.example');
INSERT INTO addresses (address_id, customer_id, street, city, state)
VALUES (-8103001, -8103001, 'Test Street', 'Test City', 'Test State');

INSERT INTO categories (category_id, name)
VALUES (-8103001, 'Step 6 validation category');
INSERT INTO products (product_id, category_id, name, price) VALUES
    (-8103001, -8103001, 'Validation product A', 100.00),
    (-8103002, -8103001, 'Validation product B', 250.00);
INSERT INTO inventory (inventory_id, product_id, quantity_in_stock) VALUES
    (-8103001, -8103001, 10), (-8103002, -8103002, 0);

INSERT INTO orders (order_id, customer_id, shipping_address_id, total_amount)
VALUES (-8103001, -8103001, -8103001, 450.00);
INSERT INTO order_items (order_item_id, order_id, product_id, quantity, unit_price)
VALUES (-8103001, -8103001, -8103001, 2, 100.00),
       (-8103002, -8103001, -8103002, 1, 250.00);

INSERT INTO payments (payment_id, order_id, amount, payment_method,
                      payment_status, transaction_reference, paid_at)
VALUES (-8103001, -8103001, 450.00, 'card', 'failed', 'STEP6-FAILED', NULL);
INSERT INTO payments (payment_id, order_id, amount, payment_method,
                      payment_status, transaction_reference, paid_at)
VALUES (-8103002, -8103001, 450.00, 'card', 'successful', 'STEP6-RETRY',
        CURRENT_TIMESTAMP);
INSERT INTO shipments (shipment_id, order_id, tracking_number)
VALUES (-8103001, -8103001, 'STEP6-SHIPMENT');
INSERT INTO reviews (review_id, customer_id, product_id, rating)
VALUES (-8103001, -8103001, -8103001, 5);

DO $$
BEGIN
    PERFORM pg_temp.assert_valid('Customer with linked address',
        (SELECT COUNT(*) = 1 FROM customers c JOIN addresses a USING (customer_id)
         WHERE c.customer_id = -8103001 AND a.country = 'Nigeria'));
    PERFORM pg_temp.assert_valid('Category with two products',
        (SELECT COUNT(*) = 2 FROM categories c JOIN products p USING (category_id)
         WHERE c.category_id = -8103001));
    PERFORM pg_temp.assert_valid('Inventory accepts positive and zero stock',
        (SELECT COUNT(*) = 2 AND MIN(quantity_in_stock) = 0
         FROM inventory WHERE product_id IN (-8103001, -8103002)));
    PERFORM pg_temp.assert_valid('Order with two products and matching total',
        (SELECT COUNT(*) = 2 AND SUM(oi.quantity * oi.unit_price) = MAX(o.total_amount)
         FROM orders o JOIN order_items oi USING (order_id)
         WHERE o.order_id = -8103001));
    PERFORM pg_temp.assert_valid('Failed payment followed by successful retry',
        (SELECT COUNT(*) = 2
            AND COUNT(*) FILTER (WHERE payment_status = 'failed') = 1
            AND COUNT(*) FILTER (WHERE payment_status = 'successful') = 1
         FROM payments WHERE order_id = -8103001));
    PERFORM pg_temp.assert_valid('One shipment linked to order',
        (SELECT COUNT(*) = 1 FROM shipments WHERE order_id = -8103001));
    PERFORM pg_temp.assert_valid('Valid customer-product review',
        (SELECT COUNT(*) = 1 FROM reviews
         WHERE customer_id = -8103001 AND product_id = -8103001 AND rating = 5));
END;
$$;

\echo
\echo POSITIVE TESTS: valid inserts and relationships
SELECT test_number AS test, test_name, result
FROM validation_results ORDER BY test_number;

DO $$
BEGIN
    PERFORM pg_temp.expect_rejection('Duplicate customer primary key',
        $q$INSERT INTO customers (customer_id, first_name, last_name, email)
           VALUES (-8103001, 'Test', 'Duplicate', 'step6-other@nexacart.example')$q$,
        '23505', 'customers_pkey');
    PERFORM pg_temp.expect_rejection('Duplicate customer email',
        $q$INSERT INTO customers (customer_id, first_name, last_name, email)
           VALUES (-8103002, 'Test', 'Duplicate', 'step6@nexacart.example')$q$,
        '23505', 'customers_email_key');
    PERFORM pg_temp.expect_rejection('Missing required first name',
        $q$INSERT INTO customers (customer_id, first_name, last_name, email)
           VALUES (-8103002, NULL, 'Test', 'step6-other@nexacart.example')$q$,
        '23502', NULL, 'first_name');
    PERFORM pg_temp.expect_rejection('Negative product price',
        $q$INSERT INTO products (product_id, category_id, name, price)
           VALUES (-8103003, -8103001, 'Invalid price', -1)$q$,
        '23514', 'products_price_check');
    PERFORM pg_temp.expect_rejection('Negative inventory quantity',
        $q$INSERT INTO inventory (inventory_id, product_id, quantity_in_stock)
           VALUES (-8103003, -8103001, -1)$q$,
        '23514', 'inventory_quantity_in_stock_check');
    PERFORM pg_temp.expect_rejection('Negative reorder level',
        $q$INSERT INTO inventory (inventory_id, product_id, reorder_level)
           VALUES (-8103003, -8103001, -1)$q$,
        '23514', 'inventory_reorder_level_check');
    PERFORM pg_temp.expect_rejection('Zero order item quantity',
        $q$INSERT INTO order_items (order_item_id, order_id, product_id, quantity, unit_price)
           VALUES (-8103003, -8103001, -8103001, 0, 100)$q$,
        '23514', 'order_items_quantity_check');
    PERFORM pg_temp.expect_rejection('Negative order item unit price',
        $q$INSERT INTO order_items (order_item_id, order_id, product_id, quantity, unit_price)
           VALUES (-8103003, -8103001, -8103001, 1, -1)$q$,
        '23514', 'order_items_unit_price_check');
    PERFORM pg_temp.expect_rejection('Review rating of six',
        $q$INSERT INTO reviews (review_id, customer_id, product_id, rating)
           VALUES (-8103002, -8103001, -8103002, 6)$q$,
        '23514', 'reviews_rating_check');
    -- Check that the deliberately missing FK target really is absent.
    IF EXISTS (SELECT 1 FROM customers WHERE customer_id = -8103099) THEN
        RAISE EXCEPTION 'Test requires customer -8103099 to be absent';
    END IF;
    PERFORM pg_temp.expect_rejection('Order with nonexistent customer',
        $q$INSERT INTO orders (order_id, customer_id, shipping_address_id, total_amount)
           VALUES (-8103002, -8103099, -8103001, 100)$q$,
        '23503', 'fk_order_customer');
    PERFORM pg_temp.expect_rejection('Second shipment for same order',
        $q$INSERT INTO shipments (shipment_id, order_id, tracking_number)
           VALUES (-8103002, -8103001, 'STEP6-SECOND-SHIPMENT')$q$,
        '23505', 'shipments_order_id_key');
    PERFORM pg_temp.expect_rejection('Second inventory row for same product',
        $q$INSERT INTO inventory (inventory_id, product_id, quantity_in_stock)
           VALUES (-8103003, -8103001, 5)$q$,
        '23505', 'inventory_product_id_key');
    PERFORM pg_temp.expect_rejection('Duplicate product within order',
        $q$INSERT INTO order_items (order_item_id, order_id, product_id, quantity, unit_price)
           VALUES (-8103003, -8103001, -8103001, 1, 100)$q$,
        '23505', 'uq_order_product');
    PERFORM pg_temp.expect_rejection('Duplicate customer-product review',
        $q$INSERT INTO reviews (review_id, customer_id, product_id, rating)
           VALUES (-8103002, -8103001, -8103001, 4)$q$,
        '23505', 'uq_customer_product_review');
    PERFORM pg_temp.expect_rejection('Invalid order status',
        $q$INSERT INTO orders (order_id, customer_id, shipping_address_id, total_amount, status)
           VALUES (-8103002, -8103001, -8103001, 100, 'unknown')$q$,
        '23514', 'orders_status_check');
    PERFORM pg_temp.expect_rejection('Zero payment amount',
        $q$INSERT INTO payments (payment_id, order_id, amount, payment_method)
           VALUES (-8103003, -8103001, 0, 'card')$q$,
        '23514', 'payments_amount_check');
END;
$$;

\echo
\echo NEGATIVE TESTS: PASS means PostgreSQL rejected the insert as expected
SELECT test_number AS test, test_name, result, sqlstate, constraint_name
FROM validation_results WHERE sqlstate IS NOT NULL ORDER BY test_number;

\echo
\echo ACTUAL POSTGRESQL ERROR MESSAGES
SELECT test_number AS test, error_message
FROM validation_results WHERE sqlstate IS NOT NULL ORDER BY test_number;

\echo
\echo VALIDATION SUMMARY
SELECT COUNT(*) AS total_tests,
       COUNT(*) FILTER (WHERE sqlstate IS NULL) AS valid_cases,
       COUNT(*) FILTER (WHERE sqlstate IS NOT NULL) AS expected_rejections,
       COUNT(*) FILTER (WHERE result = 'PASS') AS passed
FROM validation_results;

ROLLBACK;
\echo Test records and temporary helpers rolled back; validation complete.
