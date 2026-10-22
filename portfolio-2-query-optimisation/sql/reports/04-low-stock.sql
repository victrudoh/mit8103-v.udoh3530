-- The Portfolio 1 seed has no low-stock products. An empty result is correct.
SELECT p.product_id, p.name, i.quantity_in_stock, i.reorder_level
FROM public.products p
JOIN public.inventory i ON i.product_id = p.product_id
WHERE p.is_active AND i.quantity_in_stock <= i.reorder_level
ORDER BY i.quantity_in_stock, p.product_id;
