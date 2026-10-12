# Portfolio 1 Evidence Capture Guide

This folder is for genuine screenshots, command outputs, and validation evidence generated from local runs.

## Start a Clean PostgreSQL Database

Run these commands from the repository root:

```bash
docker compose down -v
docker compose up -d
docker compose ps
```

The database is exposed locally on port `55432` for optional GUI tools, while commands in this guide run inside the container.

Screenshot to capture:

- `01-docker-postgres-running.png` showing the `postgres` service running and healthy.

## Run the Schema Script

```bash
docker compose exec -T postgres psql -U nexacart_user -d nexacart_portfolio1 -f /sql/01-create-schema.sql
```

Screenshot to capture:

- `02-schema-created.png` showing the `CREATE TABLE` output for all tables.

## Show the Created Tables

```bash
docker compose exec -T postgres psql -U nexacart_user -d nexacart_portfolio1 -c "\\dt"
```

Screenshot to capture:

- `03-tables-list.png` showing the ten NexaCart tables.

## Show Example Table Structure

```bash
docker compose exec -T postgres psql -U nexacart_user -d nexacart_portfolio1 -c "\\d customers"
docker compose exec -T postgres psql -U nexacart_user -d nexacart_portfolio1 -c "\\d orders"
docker compose exec -T postgres psql -U nexacart_user -d nexacart_portfolio1 -c "\\d order_items"
```

Screenshot to capture:

- `04-table-constraints.png` showing primary keys, foreign keys, unique constraints, defaults, or checks.

## ER Diagram Evidence

Open the GitHub page for `portfolio-1-database-design/diagrams/er-diagram.md` after the branch or PR is pushed.

Screenshot to capture:

- `05-erd-render.png` showing the Mermaid diagram rendered by GitHub.

## Screenshot Notes

- Use `Shift + Cmd + 4` on macOS to capture the relevant part of the terminal or browser.
- Store screenshots in this folder using clear filenames.
- Do not include passwords, personal files, unrelated browser tabs, or sensitive local information.
- Terminal text output may also be saved here when useful, but screenshots should be genuine captures from the local run.
