SELECT o.order_id, c.first_name || ' ' || c.last_name AS customer,
       o.created_at, o.status, o.total_amount
FROM p2_benchmark.orders o
JOIN p2_benchmark.customers c ON c.customer_id = o.customer_id
WHERE o.customer_id = 42
ORDER BY o.created_at DESC, o.order_id DESC
LIMIT 20;
