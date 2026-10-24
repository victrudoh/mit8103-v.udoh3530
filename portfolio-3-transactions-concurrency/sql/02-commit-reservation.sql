\set ON_ERROR_STOP on
\pset pager off

\echo COMMIT DEMONSTRATION: reserve two LiteBook 14 units

BEGIN;

WITH reserved_stock AS (
    UPDATE p3_concurrency.stock_control
    SET available_quantity = available_quantity - 2,
        updated_at = CURRENT_TIMESTAMP
    WHERE product_id = 3
      AND available_quantity >= 2
    RETURNING product_id, available_quantity
)
INSERT INTO p3_concurrency.reservation_events
    (request_reference, product_id, quantity, outcome)
SELECT 'P3-COMMIT-RESERVATION', product_id, 2, 'committed'
FROM reserved_stock;

SELECT 'inside_transaction' AS checkpoint,
       available_quantity AS stock_after_reservation
FROM p3_concurrency.stock_control
WHERE product_id = 3;

COMMIT;

SELECT 'after_commit' AS checkpoint,
       sc.available_quantity,
       re.request_reference,
       re.quantity,
       re.outcome
FROM p3_concurrency.stock_control sc
JOIN p3_concurrency.reservation_events re USING (product_id)
WHERE sc.product_id = 3
  AND re.request_reference = 'P3-COMMIT-RESERVATION';
