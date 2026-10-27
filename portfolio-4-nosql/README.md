# Portfolio 4 - NoSQL and Advanced Data Models

## Purpose

This portfolio adds a MongoDB document model to the same NexaCart case study.
It is a read-oriented catalogue and customer-profile projection, not a replacement
for the PostgreSQL operational database. PostgreSQL remains authoritative for
customers, orders, payments, shipments, inventory and transactional stock changes.

The CA allows a document, key-value, column or graph example. This implementation
selects the **document model** because catalogue cards and customer account views
often read bounded related information together while product attributes vary by
category.

## MongoDB Model

The MongoDB database is `nexacart_portfolio4` and has two collections:

| Collection | Document design | Reason |
| --- | --- | --- |
| `catalogue_items` | Product identity, category snapshot, price, category-specific `attributes`, tags, and bounded review snippets are embedded together. | A storefront can render a catalogue card in one document read, even though a smartphone, shirt, grocery item and textbook need different attributes. |
| `customer_profiles` | Customer contact, a bounded address array, wishlist identifiers and preferences are embedded. | Account pages commonly load the profile and its addresses together. |

Each `catalogue_items` document contains `source.postgres_product_id`, linking it
back to the matching Portfolio 1 product. Product/category data is copied here as
a deliberately denormalised read model. The seven seed documents cover all six
NexaCart categories and demonstrate flexible fields such as `storage_gb`,
`available_sizes`, `capacity_litres`, `weight_kg` and `subject`. Product names,
prices, categories, customers and addresses come from the Portfolio 1 seed data;
the product-specific `attributes`, tags and the wishlist/preference fields are
illustrative additions because the relational schema has no equivalent columns.

The model uses a boundary rather than blind embedding:

- Embedded review **snippets** are bounded and useful on a product card.
- Full operational reviews and unbounded purchase/payment history stay relational.
- Wishlist values are product identifiers, not duplicated products. The
  validation script checks that every wishlist identifier resolves to a
  `catalogue_items` document.
- Catalogue changes would need an explicit projection-refresh process in a real
  system; this portfolio seeds a reproducible static projection rather than
  claiming live cross-database synchronisation.

Collection validators require the core fields, and indexes enforce unique source
product/customer IDs and support category-price and tag queries.

## Implementation

MongoDB runs in the official `mongo:8.0.30-noble` Docker image as a separate
`mongo` service in [docker-compose.yml](../docker-compose.yml), with its own
`nexacart_mongo_data` volume. It is local development infrastructure for this
portfolio, with no authentication configured; it must not be exposed unchanged in
a production environment.

[The seed script](mongodb/01-seed-document-model.js) recreates the two document
collections, applies JSON Schema validators, inserts the reproducible NexaCart
projection and creates indexes. [The query script](mongodb/02-query-document-model.js)
demonstrates category/price filtering, a query over an optional product-specific
attribute, aggregation over embedded review snippets, and a customer-profile read.
[The validation script](mongodb/03-validate-document-model.js) checks document
counts, embedded fields, wishlist references, indexes and rejection of an
incomplete document. [The explain script](mongodb/04-explain-query-plan.js)
records MongoDB's query plans for the category-price and tag queries.

Run from the repository root:

```bash
docker compose up -d --wait
python3 portfolio-4-nosql/scripts/run_portfolio.py
```

The standard-library runner saves a new timestamped evidence directory on each
run. It compares a data-only dump of PostgreSQL's `public` schema before and
afterward, so a change to the Portfolio 1 database fails the run. MongoDB is reset
only within `nexacart_portfolio4`; do not run two copies of the runner at once.

## Query Plans

`explain("executionStats")` was run against the seeded collection. The
category-price query (Electronics at or above NGN 40,000) uses the
`category_price` compound index (`FETCH -> IXSCAN`) and examines 3 documents to
return 3. The same query forced to a collection scan with `hint({ $natural: 1 })`
examines all 7 documents to return the same 3. The tag lookup uses the `tags`
index and examines 1 document.

The collection has only seven documents, so this proves the index is chosen and
reduces documents examined, not that it is measurably faster. No timing claim is
made; the difference would matter at catalogue scale.

## Suitability

MongoDB is appropriate here for evolving, category-dependent catalogue attributes
and bounded embedded account/profile data. It lets the storefront fetch a product
and its display-oriented data without joining multiple relational tables. MongoDB
documents are limited to 16 MiB, so unbounded review histories or order timelines
should not be continuously embedded.

It is less suitable as the sole store for NexaCart's order workflow. PostgreSQL's
foreign keys, validated monetary constraints, reporting queries and the Portfolio
3 transaction controls fit orders, payments, inventory and shipment relationships.
The hybrid boundary is intentional: document data serves flexible read views;
relational data protects the operational record.

A key-value store would suit simple ephemeral sessions or cache entries, but not
the nested searchable catalogue model. A wide-column store would suit high-volume
query patterns designed around partition keys. A graph model would be more useful
for recommendation traversals such as customer-product-category relationships.
Those are valid alternatives, but are not implemented because the catalogue/profile
access patterns are the primary scope of this portfolio.

## Evidence

The runner produces:

| File | Evidence |
| --- | --- |
| `01-seed-document-model.txt` | Seeded collection counts and indexes. |
| `02-query-document-model.txt` | Four document queries and their output. |
| `03-validation.txt` | Model, wishlist-reference, index and schema-validation checks. |
| `04-explain-query-plan.txt` | Index plan versus forced collection scan, and tag index use. |
| `05-verification.txt` | MongoDB execution and unchanged PostgreSQL public state. |
| `environment.json` | MongoDB image and runtime version. |

I captured screenshots of these outputs from the recorded run:
`01-seed-document-model.png`, `02-query-document-model-a.png`,
`02-query-document-model-b.png`, `03-validation.png`,
`04-explain-query-plan.png` and `05-verification.png` in the
[evidence folder](evidence/), plus `06-mongo-collections.png`, which lists the
collections directly from the running MongoDB container. My capture instructions
are in the ignored `evidence/README.md`, which is intentionally not part of the
submission.

## Sources

- MIT 8103 original CA brief, Portfolio 4: a NoSQL model based on the same case
  study, implementation evidence and suitability explanation.
- [MongoDB: Embedded Data](https://www.mongodb.com/docs/manual/data-modeling/embedding/)
- [MongoDB: Reference Data](https://www.mongodb.com/docs/manual/data-modeling/referencing/)
- [MongoDB: Data Modeling Best Practices](https://www.mongodb.com/docs/manual/data-modeling/best-practices/)
- [MongoDB Docker Official Image](https://hub.docker.com/_/mongo)

## AI Use Declaration

- **Tool used:** OpenAI Codex, followed by Cursor's AI coding assistant.
- **What it was used for:** designing the document model, writing the MongoDB
  seed, query, validation and explain scripts, the Docker Compose `mongo` service,
  the evidence runner and this documentation.
- **How the output was verified:** the runner executed the scripts against a real
  MongoDB 8.0.30 container and saved the output. Seed values were compared with
  the live PostgreSQL data, and a before/after digest confirmed the PostgreSQL
  `public` data was unchanged. The validation script checks counts, wishlist
  references, indexes and schema rejection, and the explain script checks index
  use. I capture the screenshots myself from that saved output; none are
  generated.

AI assistance and automated checks do not establish my understanding. I remain
responsible for reviewing, running and explaining the submitted work, and I will
write my own reflection for the final submission.
