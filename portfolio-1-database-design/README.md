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

## Local PostgreSQL Setup

This portfolio uses PostgreSQL for the relational database implementation. The local database can be started with Docker or OrbStack from the repository root:

```bash
docker compose up -d
```

The schema can be applied with:

```bash
docker compose exec -T postgres psql -U nexacart_user -d nexacart_portfolio1 -f /sql/01-create-schema.sql
```

Seed data can be loaded with:

```bash
docker compose exec -T postgres psql -U nexacart_user -d nexacart_portfolio1 -f /sql/02-seed-data.sql
```

To list the created tables:

```bash
docker compose exec -T postgres psql -U nexacart_user -d nexacart_portfolio1 -c "\\dt"
```

The local PostgreSQL port is exposed as `55432` for optional database GUI tools.
