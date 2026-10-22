-- Broad-scan control: all orders are needed, with no customer or date filter.
-- Totals include pending/cancelled orders and are NOT cash revenue.
SELECT status, COUNT(*) AS orders, SUM(total_amount) AS order_value
FROM p2_benchmark.orders
GROUP BY status
ORDER BY status;
