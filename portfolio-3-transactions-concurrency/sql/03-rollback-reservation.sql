\set ON_ERROR_STOP on
\pset pager off

\echo ROLLBACK DEMONSTRATION: reserve one unit, then cancel the transaction

BEGIN;

WITH reserved_stock AS (
    UPDATE p3_concurrency.stock_control
    SET available_quantity = available_quantity - 1,
        updated_at = CURRENT_TIMESTAMP
    WHERE product_id = 3
      AND available_quantity >= 1
    RETURNING product_id, available_quantity
)
INSERT INTO p3_concurrency.reservation_events
    (request_reference, product_id, quantity, outcome)
SELECT 'P3-ROLLBACK-RESERVATION', product_id, 1, 'rolled_back'
FROM reserved_stock;

SELECT 'inside_transaction' AS checkpoint,
       available_quantity AS stock_after_reservation
FROM p3_concurrency.stock_control
WHERE product_id = 3;

ROLLBACK;

SELECT 'after_rollback' AS checkpoint,
       available_quantity,
       (SELECT COUNT(*)
        FROM p3_concurrency.reservation_events
        WHERE request_reference = 'P3-ROLLBACK-RESERVATION')
           AS rolled_back_event_rows
FROM p3_concurrency.stock_control
WHERE product_id = 3;
