-- Fulfilled-order sales: shipped/delivered orders only, using sale-time prices.
-- This is merchandise value, not a claim about cash settlement or net profit.
SELECT p.product_id, p.name, SUM(oi.quantity) AS units_sold,
       SUM(oi.quantity * oi.unit_price) AS merchandise_value
FROM public.orders o
JOIN public.order_items oi ON oi.order_id = o.order_id
JOIN public.products p ON p.product_id = oi.product_id
WHERE o.status IN ('shipped', 'delivered')
GROUP BY p.product_id, p.name
ORDER BY units_sold DESC, merchandise_value DESC, p.product_id
LIMIT 10;
