-- Count distinct orders because one order can contain several category items.
SELECT c.category_id, c.name AS category,
       COUNT(DISTINCT o.order_id) AS fulfilled_orders,
       SUM(oi.quantity) AS units_sold,
       SUM(oi.quantity * oi.unit_price) AS merchandise_value
FROM public.categories c
JOIN public.products p ON p.category_id = c.category_id
JOIN public.order_items oi ON oi.product_id = p.product_id
JOIN public.orders o ON o.order_id = oi.order_id
WHERE o.status IN ('shipped', 'delivered')
GROUP BY c.category_id, c.name
ORDER BY merchandise_value DESC, c.category_id;
