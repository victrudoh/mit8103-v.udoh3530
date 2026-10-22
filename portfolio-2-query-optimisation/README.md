# Portfolio 2 - Query Processing and Optimisation

## Purpose

This portfolio uses the same NexaCart case study as Portfolio 1. It demonstrates
SQL reports, execution plans, index selection and measured performance analysis.
The operational reports use the original `public` tables. Larger generated data
and experimental indexes live only in the separate `p2_benchmark` schema.

## Business Reports

| SQL | Question | Verified Portfolio 1 seed result |
| --- | --- | --- |
| [Customer history](sql/reports/01-customer-history.sql) | What has customer 1 ordered? | Orders 7 and 1, newest first; 4 and 2 product lines. |
| [Product sales](sql/reports/02-product-sales.sql) | Which products sold on fulfilled orders? | 6 products, 7 units, NGN 185000.00 merchandise value. |
| [Category sales](sql/reports/03-category-sales.sql) | How does fulfilled merchandise value split by category? | 4 categories, totalling NGN 185000.00. |
| [Low stock](sql/reports/04-low-stock.sql) | Which active products are at or below their reorder level? | No rows; every original inventory quantity is above its threshold. |
| [Payment summary](sql/reports/05-payment-summary.sql) | How many attempts succeeded for each order? | 8 orders, 9 attempts, NGN 696500.00 successful payments. Order 2 has two attempts but one success. |

For the sales reports, "fulfilled" means `shipped` or `delivered`. Values use
`order_items.unit_price`, not the current catalogue price. These are merchandise
values, not net profit or settled cash. Successful payments are reported
separately. Joining payment attempts directly to item lines would multiply rows
and inflate sums, so these reports deliberately aggregate at the appropriate
level. Order counts across categories cannot be added to get distinct total orders.

The report runner checks these results against the original Portfolio 1 seed.
If operational data has changed, it stops for inspection rather than replacing
that data. An empty low-stock result is valid and is retained as evidence.

## Benchmark Dataset

[The setup script](sql/01-create-benchmark.sql) creates the schema once and fails
if it already exists. The runner reuses an existing, recognised benchmark after
checking its counts and relationships. It does not drop or reload the data.

| Table | Rows | Construction |
| --- | ---: | --- |
| `customers` | 10000 | Synthetic names and `.example` email addresses. |
| `addresses` | 10000 | One synthetic address per customer. |
| `categories` | 6 | Copied from the original catalogue. |
| `products` | 18 | Copied from the original catalogue. |
| `orders` | 200000 | Twenty per customer, one timestamp per minute from 2026-01-01. |
| `order_items` | 600000 | Three distinct products per order, quantities 1-3 and catalogue-based prices. |

The six tables retain the corresponding Portfolio 1 column types, required
values, checks, primary keys and unique indexes. Foreign keys are explicitly
recreated within the benchmark schema. Defaults are not copied, preventing
benchmark IDs from advancing the public tables' sequences. The schema is a
reporting subset: inventory, payments, reviews and shipments are not needed for
these benchmarks and are not copied.

Generation is deterministic given the original catalogue. Order totals are
calculated from items; the [dataset checks](sql/04-check-benchmark.sql) verify
counts, 20 orders/customer, 3 items/order, totals and address ownership. The
dataset has regular distributions and a small catalogue; it does not model real
customer skew, promotions or seasonal demand. The 600000 items establish
consistent orders but are not scanned by the three timed queries.

## Benchmark Queries and Indexes

| Query | Workload | Index hypothesis |
| --- | --- | --- |
| [Customer history](sql/benchmark/01-customer-history.sql) | Join customers and orders; find customer 42's latest 20 orders. | `(customer_id, created_at DESC, order_id DESC)` narrows the customer lookup and can support ordering. |
| [Daily fulfilled sales](sql/benchmark/02-daily-fulfilled-sales.sql) | Count and total fulfilled orders on 2026-03-01; 864 orders qualify. | A partial `(created_at, order_id) INCLUDE (total_amount)` index covering only shipped/delivered orders can avoid unrelated rows and heap reads. |
| [Order status summary](sql/benchmark/03-order-status-summary.sql) | Group all 200000 orders into six statuses. | Broad-scan control: neither targeted index covers all the work this query needs. |

The history benchmark isolates customer filtering and ordering; the business
history report additionally aggregates item counts. The daily benchmark uses
stored order totals whose agreement with item totals is checked before timing.
Date predicates use an inclusive start and exclusive end without applying a
function to the indexed column.

[Index creation](sql/03-add-indexes.sql) changes only `p2_benchmark.orders`.
The baseline retains its primary-key index and every other table's original
primary/unique indexes. "Before" does not mean a database with no indexes.
[The baseline script](sql/02-baseline-indexes.sql) removes only the two named
experimental indexes when repeating the comparison.

## Measurement Method

The [Python runner](scripts/run_portfolio.py) uses only the standard library and
the container's `psql` client. For each query in each phase it:

1. Saves the actual query result as CSV, with deterministic ordering.
2. Executes one warm-up and five measured `EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON)` runs.
3. Retains all six plans, including the excluded warm-up, and calculates medians from the five measured executions.
4. Checks that the before/after CSV results are identical.

It measures PostgreSQL's `Execution Time`, not Docker/client latency. Planning
times are saved separately. Every invocation uses the same session settings:
parallel workers disabled, JIT off, `work_mem = 16MB`, timezone UTC and a 120-second
statement timeout. Sequential, index, bitmap and index-only scans remain enabled;
the planner chooses the plan. Each invocation opens a new connection, while the
database buffer cache is shared. There are no prepared statements.

Setup runs `VACUUM (ANALYZE)` before the baseline. Index creation occurs outside
the timed queries; neither data nor statistics are deliberately changed between
phases. Baseline runs precede indexed runs. Results are local, warm-cache,
single-user observations, not randomised trials or production throughput tests.
Root-plan buffer counts are used because summing parent and child counts would
double-count accesses. Complete JSON plans are retained for inspection.

## Recorded Results

The verified run used PostgreSQL 16.15 in OrbStack on ARM64, with 128 MB shared
buffers. The recorded settings and index definitions are in
[environment.json](evidence/run-20261020T170936455423Z/environment.json).

| Query | Before median | After median | Interpretation |
| --- | ---: | ---: | --- |
| Customer history | 7.931 ms | 0.140 ms | About 56.65x faster for this lookup. |
| Daily fulfilled sales | 17.119 ms | 0.159 ms | About 107.67x faster for this date range. |
| All-order status summary | 41.241 ms | 41.446 ms | Essentially unchanged; the small slowdown does not establish a meaningful regression. |

For customer history, the orders scan changes from a sequential scan that
rejects 199980 rows to a bitmap index/heap scan finding 20 rows. Root buffer hits
fall from 3909 to 35. **The sort remains:** PostgreSQL chooses a bitmap access
path, so this run does not demonstrate elimination of sorting by the index.

For daily sales, the sequential scan rejects 199136 rows. The indexed plan uses
an index-only scan for 864 rows, with zero heap fetches in the recorded measured
runs. Root buffer hits fall from 3897 to 8. That result depends on the covered
columns, partial predicate, and visibility state; frequently updated tables may
need heap checks.

The status report still performs a sequential scan over 200000 orders, with 3900
root buffer hits in both phases. These targeted indexes do not improve every
report. All recorded measured queries have zero shared-buffer reads, so the
buffer reductions describe cached accesses, not measured disk-I/O savings.

The two added indexes occupy 8134656 and 4890624 bytes (13025280 bytes combined).
They also impose maintenance work on inserts, deletes and relevant updates.
Write overhead and index-build duration were not benchmarked. Production choices
would need broader date ranges, skewed customers, concurrent writes, repeated
trials and storage/maintenance measurements. No experimental indexes have been
applied to the operational `public` tables.

## How to Run

Prerequisites: the existing Docker Compose/OrbStack setup, Python 3.9 or newer,
and Portfolio 1's schema and original seed data. No Python packages are needed.
From the repository root:

```bash
docker compose up -d --wait
python3 portfolio-2-query-optimisation/scripts/run_portfolio.py
```

The runner creates a new timestamped folder under `evidence/` and prints its path.
It creates benchmark data on the first run, or validates and reuses it on later
runs. Repeated runs drop/recreate only the two experimental indexes; the final
state has both indexes present. Do not run two benchmarks concurrently or modify
the databases during measurement. Public rows and sequence state are compared
before and after; any difference causes a failure.

An explicit new output directory can be selected with `--output`; an existing
directory is refused to preserve prior evidence. If a run fails, its partial
folder is not completed evidence. Investigate the error before rerunning. A
later run does not automatically replace this README's recorded measurements.

Individual SQL files can also be run through standard input, without changing
the existing Docker volume mounts:

```bash
docker compose exec -T postgres psql -X -v ON_ERROR_STOP=1 -P pager=off -U nexacart_user -d nexacart_portfolio1 < portfolio-2-query-optimisation/sql/reports/01-customer-history.sql
```

## Evidence

The checked run is [run-20261020T170936455423Z](evidence/run-20261020T170936455423Z/).
All files below were produced from actual database execution.

| Artifact | Purpose |
| --- | --- |
| [Business reports](evidence/run-20261020T170936455423Z/01-business-reports.txt) | Readable query results and seed checks; individual CSVs are in `reports/`. |
| [Dataset validation](evidence/run-20261020T170936455423Z/02-dataset-validation.txt) | Setup output, six table counts, relationships and totals check. |
| [Plan comparison](evidence/run-20261020T170936455423Z/03-plan-comparison.txt) | Readable extracts from measured run 3 in each phase, not separate fabricated plans. |
| [Benchmark summary](evidence/run-20261020T170936455423Z/04-benchmark-summary.md) | All measured timings, medians, buffer counts and index sizes. |
| [Measurements CSV](evidence/run-20261020T170936455423Z/measurements.csv) | All 36 executions, with warm-ups explicitly marked. |
| [Complete plans](evidence/run-20261020T170936455423Z/explain-plans.json) | Full JSON EXPLAIN documents for all runs. |
| [Query results](evidence/run-20261020T170936455423Z/query-results/) | Identical before/after outputs for all benchmark queries. |

Screenshots are pending student capture; the output files already document the
executed work. Personal capture instructions are kept in the ignored local
`evidence/README.md`. They are not part of the repository submission.

## Reflection and Sources

This experiment shows that index choice depends on the query's filter and the
amount of data required. Two selective reports benefit substantially, while the
all-order summary still needs a broad scan. The history plan also shows why an
index hypothesis must be checked against the actual plan: the composite index
is used, but it does not remove the sort in this run.

Keeping generated data separate preserves the original case-study evidence.
Checking result equality and monetary totals ensures that a faster query still
answers the same question. Small timing changes on a local machine should not
be presented as a proven improvement or regression.

- MIT 8103 original CA brief, section 4: queries, results, plans, indexing evidence and performance analysis.
- [PostgreSQL 16: Using EXPLAIN](https://www.postgresql.org/docs/16/using-explain.html).
- [PostgreSQL 16: Multicolumn Indexes](https://www.postgresql.org/docs/16/indexes-multicolumn.html).
- [PostgreSQL 16: Partial Indexes](https://www.postgresql.org/docs/16/indexes-partial.html).
- [PostgreSQL 16: Index-Only Scans](https://www.postgresql.org/docs/16/indexes-index-only-scans.html).

OpenAI Codex assisted with SQL, synthetic data generation, benchmark automation
and documentation, and executed the recorded verification. The student should
review the scripts and results, capture their own screenshots, and write their
personal learning reflection before final submission. No performance figures or
screenshots have been invented.
