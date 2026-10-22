# Measured Benchmark Results

Run: 2026-10-20T17:09:48.594639+00:00

One warm-up and five measured executions per query per phase. Times below
are PostgreSQL execution times; Docker startup, connection and planning time
are excluded. All samples and complete plans are retained alongside this file.

| Query | Before median ms | After median ms | Before / after |
| --- | ---: | ---: | ---: |
| 01-customer-history | 7.931 | 0.140 | 56.65x |
| 02-daily-fulfilled-sales | 17.119 | 0.159 | 107.67x |
| 03-order-status-summary | 41.241 | 41.446 | 1.00x |

## 01-customer-history

- Before times (ms): 7.603, 7.679, 7.974, 7.931, 8.107.
- Before median root buffer hits: 3909; reads: 0.
- Before run 3 access paths: Index Scan customers via customers_pkey; Seq Scan orders.
- After times (ms): 0.144, 0.146, 0.121, 0.129, 0.140.
- After median root buffer hits: 35; reads: 0.
- After run 3 access paths: Index Scan customers via customers_pkey; Bitmap Heap Scan orders; Bitmap Index Scan  via p2_orders_customer_created_idx.

## 02-daily-fulfilled-sales

- Before times (ms): 17.119, 16.932, 17.177, 17.427, 17.086.
- Before median root buffer hits: 3897; reads: 0.
- Before run 3 access paths: Seq Scan orders.
- After times (ms): 0.163, 0.159, 0.262, 0.157, 0.157.
- After median root buffer hits: 8; reads: 0.
- After run 3 access paths: Index Only Scan orders via p2_orders_fulfilled_created_idx.

## 03-order-status-summary

- Before times (ms): 41.222, 42.081, 41.241, 41.283, 39.948.
- Before median root buffer hits: 3900; reads: 0.
- Before run 3 access paths: Seq Scan orders.
- After times (ms): 46.320, 39.853, 41.616, 41.446, 41.062.
- After median root buffer hits: 3900; reads: 0.
- After run 3 access paths: Seq Scan orders.

## Index Storage

- `p2_orders_customer_created_idx`: 8,134,656 bytes.
- `p2_orders_fulfilled_created_idx`: 4,890,624 bytes.

## Checks

- PASS: business reports match the original seed.
- PASS: benchmark counts, order totals and address ownership.
- PASS: identical ordered results before and after indexing for every benchmark query.
- PASS: existing public data and sequence state unchanged.

Index creation is outside the measured queries. No public indexes were changed.
Run without other database activity; these are warm-cache local measurements,
not a production capacity test or a guarantee of speedup.
