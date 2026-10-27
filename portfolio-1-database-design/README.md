# Portfolio 1 - Database Design and Modelling

## Case Study

NexaCart is a simulated e-commerce platform that supports online retail activity from product browsing through order fulfilment. Customers use the system to register accounts, maintain delivery addresses, browse product categories, place orders, make payments, submit reviews, and track deliveries. Administrators use the system to manage the product catalogue, organise categories, monitor inventory, and support order fulfilment.

## Purpose

The database design supports the core operational data needed by an e-commerce platform. It records customer details, address information, product catalogue data, stock levels, order transactions, payment attempts, shipment tracking, and product reviews. The same case study is structured so later portfolio work can examine query optimisation, transactions, concurrency, NoSQL modelling, and distributed or cloud database concepts.

## Primary Users

- Customers who browse products, place orders, pay for purchases, review products, and track deliveries.
- Administrators who manage categories, products, inventory levels, order status, payments, and fulfilment activity.

## Major Data Areas

- Customers and delivery addresses
- Product categories and products
- Inventory records
- Orders and order items
- Payments and payment statuses
- Shipments and tracking details
- Product reviews and ratings

## Key Database Operations

- Register and maintain customer records.
- Store one or more delivery addresses for each customer.
- Create and manage product categories and product listings.
- Track inventory quantity and reorder levels for products.
- Record customer orders and the products included in each order.
- Store payment attempts and payment outcomes for orders.
- Track shipment status and delivery information.
- Store customer reviews for purchased or reviewed products.

## Database Technology

The implementation uses PostgreSQL 16 in the `postgres:16` Docker image, managed
with Docker Compose and OrbStack on macOS. Verification used PostgreSQL 16.15
on ARM64 and Docker Compose v5.5.0. SQL runs through the container's `psql` client;
no host PostgreSQL installation or database GUI is required. The image tag tracks
the PostgreSQL 16 release series, so later pulls can have a newer patch version.

## Relational Schema

The [schema script](sql/01-create-schema.sql) defines ten tables. The
[Mermaid ER diagram](diagrams/er-diagram.md) and its
[rendered export](diagrams/er-diagram.png) show all eleven foreign-key relationships.
Every table has a single `BIGSERIAL` primary key; foreign keys use `BIGINT`.
Money fields use `NUMERIC(12,2)`, interpreted as Nigerian naira for this dataset.
Timestamps are `TIMESTAMP WITHOUT TIME ZONE`.

| Table | Primary key | Foreign keys | Other attributes |
| --- | --- | --- | --- |
| `customers` | `customer_id` | None | `first_name`, `last_name`, `email`, `phone`, `created_at` |
| `addresses` | `address_id` | `customer_id -> customers` | `street`, `city`, `state`, `country` |
| `categories` | `category_id` | None | `name`, `description` |
| `products` | `product_id` | `category_id -> categories` | `name`, `description`, `price`, `is_active`, `created_at` |
| `inventory` | `inventory_id` | `product_id -> products` | `quantity_in_stock`, `reorder_level`, `updated_at` |
| `orders` | `order_id` | `customer_id -> customers`; `shipping_address_id -> addresses` | `total_amount`, `status`, `created_at` |
| `order_items` | `order_item_id` | `order_id -> orders`; `product_id -> products` | `quantity`, `unit_price` |
| `payments` | `payment_id` | `order_id -> orders` | `amount`, `payment_method`, `payment_status`, `transaction_reference`, `paid_at` |
| `shipments` | `shipment_id` | `order_id -> orders` | `tracking_number`, `status`, `shipped_at`, `delivered_at` |
| `reviews` | `review_id` | `customer_id -> customers`; `product_id -> products` | `rating`, `comment`, `created_at` |

All foreign keys reference the named parent's primary key and are required.
Phone numbers, descriptions, review comments, payment references/payment dates,
and shipment tracking numbers/dates can be null. Other columns are required.
The SQL script is the authoritative definition of lengths, precision and nullability.

## Relationships and Design Decisions

| Parent to child | Cardinality enforced by SQL | Design reason |
| --- | --- | --- |
| Customer to addresses, orders, reviews | One to zero or many | Each customer can maintain addresses, place orders and write reviews. |
| Address to orders | One to zero or many | Multiple orders can use the same delivery address. |
| Category to products | One to zero or many | Each product belongs to one category. |
| Product to inventory | One to zero or one | `inventory.product_id` is unique. |
| Product to order items, reviews | One to zero or many | Products occur in different orders and receive different customers' reviews. |
| Order to order items, payments | One to zero or many | An order has separate lines and can have multiple payment attempts. |
| Order to shipments | One to zero or one | The initial model allows one shipment per order, not split deliveries. |

In each relationship, a child references exactly one parent. The business intends
stocked products to have inventory and placed orders to have one or more items.
SQL currently permits products without inventory and orders without items; the
ERD records that distinction instead of implying those minimums are enforced.

### Resolving the Many-to-Many Relationship

An order can contain multiple products, and a product can appear in multiple
orders. `order_items` resolves this many-to-many relationship into two one-to-many
relationships. `UNIQUE (order_id, product_id)` prevents duplicate lines for the
same product; `quantity` records multiple units. For example, seeded order 1 has
one smartphone at 380000.00 and two earbuds at 42000.00, totalling 464000.00.

`unit_price` is the sale price recorded for that order line. It is intentionally
separate from the current catalogue `products.price`, so changing a product's
price need not rewrite historical orders. `reviews` similarly associates a
customer with a product and limits the pair to one review.

Payments are separate records rather than one status field on an order. Seeded
order 2 demonstrates a failed attempt followed by a successful retry. Shipment
data remains optional until fulfilment begins. Products use `is_active` to support
catalogue withdrawal while retaining order references.

## Keys and Constraints

The schema contains 10 primary keys, 11 foreign keys, 8 additional unique
constraints and 11 check constraints. `NOT NULL` and defaults supplement them.

| Constraint | Implementation |
| --- | --- |
| Primary keys | Each table's ID identifies one row. |
| Foreign keys | All eleven links in the schema table require existing parent records. |
| Unique values | Customer email; category name; inventory product; shipment order; payment reference; shipment tracking number. |
| Composite unique values | `(order_id, product_id)` in `order_items`; `(customer_id, product_id)` in `reviews`. |
| Required values | Names, email, foreign keys, amounts, quantities and statuses cannot be null. |
| Nonnegative values | Product price, order total, item unit price, inventory quantity and reorder level. |
| Positive values | Order item quantity and payment amount must be greater than zero. |
| Rating range | Reviews allow integers 1 through 5. |
| Order status | `pending`, `confirmed`, `processing`, `shipped`, `delivered`, `cancelled`. |
| Payment status | `pending`, `successful`, `failed`, `refunded`. |
| Shipment status | `pending`, `shipped`, `in_transit`, `delivered`, `failed`. |
| Defaults | Country `Nigeria`; active product `true`; stock `0`; reorder level `5`; order/payment/shipment status `pending`; creation/update timestamps `CURRENT_TIMESTAMP`. |

Nullable unique payment references and tracking numbers can be absent in multiple
rows. `NOT NULL` is needed alongside checks because a check alone does not reject
null. Default timestamps apply at insertion; `inventory.updated_at` does not
automatically change on later updates. These behaviours follow PostgreSQL's
[constraint rules](https://www.postgresql.org/docs/16/ddl-constraints.html) and
[default-value rules](https://www.postgresql.org/docs/16/ddl-default.html).

Deleting a customer cascades to addresses and reviews; deleting a product cascades
to inventory and reviews; deleting an order cascades to its items. All other
foreign keys use the default `NO ACTION`. Existing order, item, payment or shipment
references can therefore block a parent deletion, including a deletion that
would otherwise cascade. No automatic deletion of financial history is assumed.

## Normalisation

### First Normal Form (1NF)

Each column holds one value of its declared type and each row has a primary key.
An order does not contain repeating columns such as `product_1`, `product_2`, or a
comma-separated product list. Its products are separate `order_items` rows.
Customers' multiple addresses are also separate rows.

### Second Normal Form (2NF)

Non-key attributes depend on the whole candidate key, not part of a composite
key. In `order_items`, the candidate key `(order_id, product_id)` determines
`quantity` and the historical `unit_price`. Neither depends on only `order_id` or
only `product_id`. Product names and current catalogue prices belong to
`products`, while order dates belong to `orders`. For reviews, the customer-product
pair determines the rating and comment. Surrogate IDs provide convenient primary
keys, but do not replace the need to examine these composite dependencies.

### Third Normal Form (3NF)

The core entity tables separate attributes by functional dependency. For example:

- `customer_id -> first_name, last_name, email, phone, created_at`.
- `category_id -> name, description` in `categories`.
- `product_id -> category_id, name, description, price, is_active, created_at` in `products`.
- `(order_id, product_id) -> quantity, unit_price` in `order_items`.

Category name and description are not copied into `products`; that avoids the
transitive dependency `product_id -> category_id -> category_name` within one
table. Customer names are not copied into `orders`, and product names are not
copied into `order_items`. Under the stated entity dependencies, these tables
follow 3NF: a non-key attribute does not determine another non-key attribute.
Free-text city/state/country fields are treated as address components rather
than authoritative geographic identifiers.

This separation reduces update anomalies (renaming a category in many products),
insertion anomalies (needing an order before storing a product), and deletion
anomalies (losing product information when its last order line is removed).

### Stored Totals and Ownership Assumptions

`orders.total_amount` is a stored aggregate that duplicates information derivable
from order items in this simple pricing model. It is a deliberate redundancy in
the supplied design, not evidence that every derived value has been eliminated.
Within `orders` it depends on the order key, but maintaining consistency with
items requires additional logic. The seed totals match; SQL does not enforce that
equality when items change.

`orders.customer_id` identifies the purchaser; `shipping_address_id` identifies
the destination record. The current schema does not require that record's owner
to be the purchaser. If an own-address-only rule is adopted, the destination
would determine the purchaser and these two columns would introduce a transitive
dependency. That rule would require revisiting the design or explicitly accepting
and enforcing the redundancy. This qualification matters when claiming 3NF for
the whole system rather than only its core entity decomposition.

## Local PostgreSQL Setup

Prerequisites: Git, a running Docker engine (OrbStack was used), Docker Compose
with `--wait` support, and host port `55432` available. Run commands from the
repository root after cloning the repository with authorised access.

### First Run

Start PostgreSQL and wait for its health check:

```bash
docker compose up -d --wait
docker compose ps
```

On an empty `nexacart_portfolio1` database, create the schema, load sample data,
then run the validation suite in this order:

```bash
docker compose exec -T postgres psql -X -v ON_ERROR_STOP=1 --single-transaction -U nexacart_user -d nexacart_portfolio1 -f /sql/01-create-schema.sql
docker compose exec -T postgres psql -X -v ON_ERROR_STOP=1 -U nexacart_user -d nexacart_portfolio1 -f /sql/02-seed-data.sql
docker compose exec -T postgres psql -X -v ON_ERROR_STOP=1 -U nexacart_user -d nexacart_portfolio1 -f /sql/03-validate-constraints.sql
```

The schema command is atomic and expects no existing NexaCart tables. The seed
script has its own transaction and **truncates all ten tables and resets their ID
sequences** before loading its dataset. Only rerun it when replacing that data is
intended. Validation uses its own transaction and rolls back its test records.
`-X` ignores local `psql` settings; `ON_ERROR_STOP` makes errors stop the command.

Inspect the implementation:

```bash
docker compose exec -T postgres psql -X -U nexacart_user -d nexacart_portfolio1 -c '\dt'
docker compose exec -T postgres psql -X -U nexacart_user -d nexacart_portfolio1 -c '\d order_items'
docker compose exec -T postgres psql -X -U nexacart_user -d nexacart_portfolio1 -c 'SHOW server_version;'
```

The seed dataset is simulated, not customer data collected from a real business.

| Table | Seed rows | Table | Seed rows |
| --- | ---: | --- | ---: |
| `customers` | 6 | `orders` | 8 |
| `addresses` | 9 | `order_items` | 18 |
| `categories` | 6 | `payments` | 9 |
| `products` | 18 | `shipments` | 4 |
| `inventory` | 18 | `reviews` | 7 |

### Existing Database and Fresh Verification

For normal use, `docker compose up -d --wait` starts the existing database; run
only validation when the schema and seeds are already present. To reproduce the
full setup without replacing that data, use a separate database in the container:

```bash
docker compose exec -T postgres createdb -U nexacart_user nexacart_portfolio1_verify
docker compose exec -T postgres psql -X -v ON_ERROR_STOP=1 --single-transaction -U nexacart_user -d nexacart_portfolio1_verify -f /sql/01-create-schema.sql
docker compose exec -T postgres psql -X -v ON_ERROR_STOP=1 -U nexacart_user -d nexacart_portfolio1_verify -f /sql/02-seed-data.sql
docker compose exec -T postgres psql -X -v ON_ERROR_STOP=1 -U nexacart_user -d nexacart_portfolio1_verify -f /sql/03-validate-constraints.sql
```

`createdb` must succeed before continuing. If that name already exists, choose a
new verification database name and substitute it in all four commands. After
inspection, remove only the verification database created for this run:

```bash
docker compose exec -T postgres dropdb -U nexacart_user nexacart_portfolio1_verify
```

`docker compose stop` stops PostgreSQL while keeping its named volume. Avoid
`docker compose down -v` unless intentionally deleting the database volume and
all databases it contains.

Optional GUI connection: host `localhost`, port `55432`, database
`nexacart_portfolio1`, user `nexacart_user`, password `nexacart_password`.
These are disposable coursework credentials from [docker-compose.yml](../docker-compose.yml),
not production secrets. The current port mapping binds on all host interfaces;
this configuration is intended for a local development machine.

## Constraint and Relationship Validation

After creating the schema, run the Step 6 tests from the repository root:

```bash
docker compose exec -T postgres psql -X -v ON_ERROR_STOP=1 -U nexacart_user -d nexacart_portfolio1 -f /sql/03-validate-constraints.sql
```

The script tests seven valid cases and sixteen invalid inserts, covering primary
keys, foreign keys, unique constraints, check constraints, and required values.
Valid cases include a multi-product order and a failed payment followed by a
successful retry. Each negative test checks the actual PostgreSQL SQLSTATE and
constraint name (or column for NOT NULL), so an unrelated error cannot pass the
test. An unexpected result stops the script with a nonzero exit code.

Tests use their own records with reserved negative IDs and finish with `ROLLBACK`.
They can run with or without seed data and do not advance application ID sequences.
A collision with a test ID or unique value stops the run. Run the file through the
command above so the connection closes and rolls back on an unexpected error.

The expected summary is **23 tests passed: 7 valid cases and 16 expected
rejections**. Genuine terminal output is stored in
[`evidence/08-constraint-validation.txt`](evidence/08-constraint-validation.txt).

Step 7 verification reproduced schema creation, seeding and all 23 tests in a
fresh `nexacart_portfolio1_verify` database. The ten row counts above matched,
and all eight seeded order totals equalled their item totals. The temporary
verification database was then removed. A before/after data dump comparison
confirmed the existing portfolio database and its sequence state were unchanged.

These tests establish the constraints exercised by the script. The schema does
not enforce that every product has inventory, every order has items, an order's
shipping address belongs to its customer, or its total equals the sum of its
items. The positive order test verifies the total for its test records; it does
not establish a database constraint for that rule. The 23 cases demonstrate the
listed behaviours, not an exhaustive test of every constraint or workflow.

## Scope and Limitations

The schema is a relational foundation, not a complete checkout application.
Stock is not automatically reduced when items are inserted, and payment status
does not automatically advance an order or shipment. Timestamp ordering and
review eligibility are not enforced. Seed reviews include products on orders
that are not marked delivered, and failed seed payments have `paid_at` values;
these demonstrate stored records, not a validated fulfilment or payment lifecycle.
A later workflow should distinguish payment-attempt times from settlement times.

Addresses are mutable references, not immutable snapshots of shipping details.
Editing an address would change the address shown for older orders. Multiple
currencies, variants, split shipments, tax, delivery charges and discounts are
outside this initial model. These boundaries leave concrete transaction and
modelling questions for later portfolios without claiming they are solved here.

## Evidence Index

Evidence numbers identify both screenshots and text logs. File 08 is a text log,
so no screenshot numbered 08 is missing. The capture-instructions README in the
local evidence directory is intentionally excluded from Git.

| Evidence | What it demonstrates |
| --- | --- |
| [01 - PostgreSQL running](evidence/01-docker-postgres-running.png) | Healthy container. |
| [02 - Schema creation](evidence/02-schema-created.png) | Successful table creation. |
| [03 - Table list](evidence/03-tables-list.png) | Ten relational tables. |
| [04 - Constraints](evidence/04-table-constraints.png) | Table definitions and key/check constraints. |
| [05 - Initial ERD](evidence/05-erd-render.png) | Earlier GitHub-rendered ER model, before Step 7 corrections. |
| [06 - Seed data](evidence/06-seed-data-loaded.png) | Loaded sample records and counts. |
| [07 - Related data](evidence/07-seeded-order-relationships.png) | Customer, order, item and product joins. |
| [08 - Validation log](evidence/08-constraint-validation.txt) | Actual output of the 23-case suite. |
| [09 - Valid relationships](evidence/09-valid-relationships.png) | Seven successful positive tests. |
| [10 - Invalid data rejected](evidence/10-rejected-invalid-data.png) | Sixteen rejected inserts, SQLSTATEs, constraints and error messages. |
| [11 - Validation summary](evidence/11-validation-summary.png) | 23 passes and final rollback. |
| [Current ERD export](diagrams/er-diagram.png) | Locally rendered Mermaid model matching the implemented foreign keys and cardinalities; not a screenshot. |

The current ERD adds the address-to-order link, unique-key labels, and optional
child participation permitted by SQL. It supersedes image 05 for the final model
while preserving that screenshot as evidence of progressive work. These are
documentation corrections; the table definitions have not changed.

## Technical Reflection

Separating order lines from products keeps catalogue changes independent of
historical sale prices. Separating payment attempts preserves the failed attempt
as well as the successful retry, which a single payment field would lose.

Validation revealed an important distinction between a business rule and a
constraint: a unique foreign key prevents a second inventory row but cannot
require the first one to exist. Reviewing the ERD against the SQL made that
distinction explicit. Negative tests check the specific error rather than treating
any rejection as success; a missing price check was deliberately tested in a
disposable database and caused the validation script to fail as intended.

Repeatable testing also requires careful cleanup. Test records use explicit IDs
because rolling back a transaction does not roll back sequence increments. The
suite leaves existing data and ID sequences unchanged, while the seed loader is
explicitly documented as a dataset replacement operation. These choices make
the evidence reproducible and identify the remaining work for transaction logic.

This reflection describes observed implementation decisions. My individual
reflection across all five portfolios is in the
[final documentation reflection](../final-documentation/reflection.md).

## Sources and AI Use

- MIT 8103 Advanced Database Systems CA, September Cohort 2026, sections 2, 4-8
  and 11: case study, Portfolio 1 deliverables, evidence and AI declaration requirements.
- `MIT8103_NexaCart_Portfolio1_Codex_Guide.pdf`, Steps 1-7: initial NexaCart
  schema, ER model, validation cases and normalisation outline. The schema and
  initial ERD are adapted from that supplied guide.
- [PostgreSQL 16 constraints](https://www.postgresql.org/docs/16/ddl-constraints.html):
  key, check, nullability and referential-action semantics.
- [PostgreSQL 16 defaults](https://www.postgresql.org/docs/16/ddl-default.html):
  insertion defaults.
- [PostgreSQL 16 sequence functions](https://www.postgresql.org/docs/16/functions-sequence.html):
  sequence behaviour during rollback.
- [Mermaid ER diagrams](https://mermaid.js.org/syntax/entityRelationshipDiagram.html):
  cardinalities, relationship notation and key labels.

OpenAI Codex assisted with implementation, simulated seed data, SQL validation,
Docker setup, ERD corrections and documentation. Verification included actual
PostgreSQL runs, expected-error checks, a disposable-database failure test, and
comparison of data and sequence state before and after validation. I ran the
evidence commands and captured the terminal and ERD screenshots. AI assistance
and automated tests do not establish my understanding; I remain responsible for
reviewing and explaining the submitted work.
