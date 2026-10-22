-- Half-open date bounds avoid applying a function to the indexed column.
SELECT COUNT(*) AS fulfilled_orders, SUM(total_amount) AS merchandise_value
FROM p2_benchmark.orders
WHERE status IN ('shipped', 'delivered')
  AND created_at >= TIMESTAMP '2026-03-01 00:00:00'
  AND created_at < TIMESTAMP '2026-03-02 00:00:00';
