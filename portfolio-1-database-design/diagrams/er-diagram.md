# NexaCart ER Diagram

This diagram shows the relationships enforced by the PostgreSQL schema. Each
child row has exactly one referenced parent. A parent need not yet have child
rows. Dotted lines denote non-identifying relationships: foreign keys are not
part of the child's primary key. `PK`, `FK`, and `UK` identify primary, foreign,
and unique keys. Composite unique constraints are listed below the diagram.

```mermaid
erDiagram
    CUSTOMERS ||..o{ ADDRESSES : has
    CUSTOMERS ||..o{ ORDERS : places
    CUSTOMERS ||..o{ REVIEWS : writes
    ADDRESSES ||..o{ ORDERS : ships_to
    CATEGORIES ||..o{ PRODUCTS : contains
    PRODUCTS ||..o| INVENTORY : has
    PRODUCTS ||..o{ ORDER_ITEMS : appears_in
    PRODUCTS ||..o{ REVIEWS : receives
    ORDERS ||..o{ ORDER_ITEMS : contains
    ORDERS ||..o{ PAYMENTS : has
    ORDERS ||..o| SHIPMENTS : has

    CUSTOMERS {
        bigint customer_id PK
        varchar first_name
        varchar last_name
        varchar email UK
        varchar phone
        timestamp created_at
    }

    ADDRESSES {
        bigint address_id PK
        bigint customer_id FK
        varchar street
        varchar city
        varchar state
        varchar country
    }

    CATEGORIES {
        bigint category_id PK
        varchar name UK
        text description
    }

    PRODUCTS {
        bigint product_id PK
        bigint category_id FK
        varchar name
        text description
        decimal price
        boolean is_active
        timestamp created_at
    }

    INVENTORY {
        bigint inventory_id PK
        bigint product_id FK, UK
        int quantity_in_stock
        int reorder_level
        timestamp updated_at
    }

    ORDERS {
        bigint order_id PK
        bigint customer_id FK
        bigint shipping_address_id FK
        decimal total_amount
        varchar status
        timestamp created_at
    }

    ORDER_ITEMS {
        bigint order_item_id PK
        bigint order_id FK
        bigint product_id FK
        int quantity
        decimal unit_price
    }

    PAYMENTS {
        bigint payment_id PK
        bigint order_id FK
        decimal amount
        varchar payment_method
        varchar payment_status
        varchar transaction_reference UK
        timestamp paid_at
    }

    SHIPMENTS {
        bigint shipment_id PK
        bigint order_id FK, UK
        varchar tracking_number UK
        varchar status
        timestamp shipped_at
        timestamp delivered_at
    }

    REVIEWS {
        bigint review_id PK
        bigint customer_id FK
        bigint product_id FK
        int rating
        text comment
        timestamp created_at
    }
```

Composite unique constraints:

- `order_items (order_id, product_id)`: a product appears once per order.
- `reviews (customer_id, product_id)`: a customer reviews a product once.

`transaction_reference` and `tracking_number` are nullable; their unique
constraints apply to non-null values. Other nullability, lengths, numeric
precision, defaults, and checks are specified in
[`01-create-schema.sql`](../sql/01-create-schema.sql).

The business intends each stocked product to have inventory and each placed
order to have at least one item. The foreign keys and unique constraints enforce
at most one inventory record and valid item references, but do not require those
child rows to exist. These minimum-participation rules need transaction or
application logic. The original guide's mandatory cardinalities have therefore
been changed here to reflect what the implemented schema actually enforces.

[Rendered diagram](er-diagram.png) is a local Mermaid export of this source, not
a GitHub screenshot. Evidence image `05-erd-render.png` preserves the earlier
GitHub-rendered model; this source and export include the Step 7 corrections.
