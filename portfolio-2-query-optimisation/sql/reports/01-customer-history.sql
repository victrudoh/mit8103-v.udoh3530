-- Order history for Amara (customer 1), including pending/cancelled orders.
-- Aggregate items before displaying one row per order; do not join payments.
SELECT o.order_id, c.first_name || ' ' || c.last_name AS customer,
       o.created_at, o.status, COUNT(oi.order_item_id) AS product_lines,
       COALESCE(SUM(oi.quantity), 0) AS units, o.total_amount
FROM public.orders o
JOIN public.customers c ON c.customer_id = o.customer_id
LEFT JOIN public.order_items oi ON oi.order_id = o.order_id
WHERE o.customer_id = 1
GROUP BY o.order_id, c.first_name, c.last_name
ORDER BY o.created_at DESC, o.order_id DESC
LIMIT 20;
