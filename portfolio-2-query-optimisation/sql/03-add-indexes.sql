-- Equality on customer, followed by the requested date and ID ordering.
CREATE INDEX p2_orders_customer_created_idx
ON p2_benchmark.orders (customer_id, created_at DESC, order_id DESC);

-- Only fulfilled orders are indexed. The query repeats this exact predicate.
-- Included totals permit an index-only plan when visibility permits it.
CREATE INDEX p2_orders_fulfilled_created_idx
ON p2_benchmark.orders (created_at, order_id) INCLUDE (total_amount)
WHERE status IN ('shipped', 'delivered');
