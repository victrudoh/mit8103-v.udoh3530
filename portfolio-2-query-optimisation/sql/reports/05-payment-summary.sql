-- Separate successful collections from merchandise sales and failed retries.
-- One row per order prevents payment attempts from multiplying item amounts.
SELECT o.order_id, o.status AS order_status, COUNT(p.payment_id) AS attempts,
       COUNT(p.payment_id) FILTER (WHERE p.payment_status = 'successful') AS successes,
       COALESCE(SUM(p.amount) FILTER (
           WHERE p.payment_status = 'successful'), 0) AS successful_amount
FROM public.orders o
LEFT JOIN public.payments p ON p.order_id = o.order_id
GROUP BY o.order_id, o.status
ORDER BY o.order_id;
