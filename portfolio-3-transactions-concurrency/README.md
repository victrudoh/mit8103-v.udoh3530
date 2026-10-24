# Portfolio 3 - Transactions and Concurrency

## Purpose

This portfolio demonstrates transaction behaviour for the NexaCart e-commerce
case study. It uses a private `p3_concurrency` schema that references the product
catalogue but never writes to the operational `public` tables. The lab models a
stock reservation for product 3, the LiteBook 14 Laptop.

The implementation covers the CA requirements: a committed transaction, a
rollback, an isolation-level example, a concurrency control mechanism, and
saved output evidence.

## Lab Model

| Table | Purpose |
| --- | --- |
| `stock_control` | Private available stock for the reservation demonstrations. It starts at 12 units. |
| `reservation_events` | Audit-style rows created only when a reservation transaction commits. |

`stock_control.product_id` references `public.products(product_id)`, so the lab
uses the real NexaCart product catalogue. It is intentionally separate from
`public.inventory`: demonstrating transactions must not alter Portfolio 1's
seeded inventory or invalidate its earlier evidence.

[Setup SQL](sql/01-create-transaction-lab.sql) creates or resets only the private
lab schema. It loads one row for product 3 with 12 available units.

## Demonstrations

### Commit

[The commit script](sql/02-commit-reservation.sql) starts a transaction, atomically
decrements stock by two only where at least two units exist, inserts a matching
reservation event, and commits. The verified state is 10 units with exactly one
`P3-COMMIT-RESERVATION` event. Both changes persist together, which demonstrates
atomicity and durability for this reservation.

### Rollback

[The rollback script](sql/03-rollback-reservation.sql) temporarily reserves one
unit and writes `P3-ROLLBACK-RESERVATION`, then issues `ROLLBACK`. It shows 9
units inside the transaction, but afterwards stock is again 10 and no event row
exists. This demonstrates that the related stock and audit changes are both
undone; neither partially persists.

### Isolation

The runner opens two separate PostgreSQL sessions. Session A begins at
`REPEATABLE READ` and sees stock 10. Session B replenishes one unit and commits.
Session A still sees 10 until it commits; a new read then sees 11. PostgreSQL's
repeatable-read transaction keeps a consistent snapshot rather than exposing a
non-repeatable read within Session A.

### Concurrency Control

The runner resets only the private lab row to one unit, then opens two more
sessions. Both use the same guarded statement:

```sql
UPDATE p3_concurrency.stock_control
SET available_quantity = available_quantity - 1
WHERE product_id = 3
  AND available_quantity >= 1;
```

Session A updates the row and holds its transaction open. Session B waits on the
row lock. Once A commits, PostgreSQL rechecks B's predicate; because stock is
now zero, B updates no row. The final state is stock zero with one reservation
event. This is a control mechanism for the oversell race: the check and decrement
are one atomic `UPDATE`, rather than a separate application-side read followed by
an unconditional write.

The exercise deliberately shows the controlled outcome rather than attempting to
manufacture an oversell in the shared operational inventory. It does not claim
that row locking alone handles every checkout concern: production code also needs
payment idempotency, timeouts, retry policy, and a clear order lifecycle.

## Run and Verify

Prerequisites are the existing Docker Compose/OrbStack PostgreSQL setup, Python
3.9 or newer, and the Portfolio 1 schema and seed data. No Python packages are
required.

```bash
docker compose up -d --wait
python3 portfolio-3-transactions-concurrency/scripts/run_portfolio.py
```

The runner creates a new timestamped evidence directory and refuses to overwrite
one. It runs the commit and rollback SQL files, coordinates two live `psql`
sessions for the isolation and lock demonstrations, and checks every expected
result. Before and after the work it hashes a data-only dump of `public`,
including sequence state. A mismatch fails the run.

The private lab schema is reset at the beginning of each run. It is safe to rerun
when no other Portfolio 3 session is active. Do not run two copies at once.

## Evidence

The verified [recorded run](evidence/run-20261023T103833386201Z/) contains these
five outputs:

| File | Evidence |
| --- | --- |
| `01-commit-reservation.txt` | Committed stock decrement and audit row. |
| `02-rollback-reservation.txt` | Temporary decrement/event followed by rollback. |
| `03-repeatable-read-isolation.txt` | Snapshot preserved in Session A while Session B commits. |
| `04-concurrent-reservation-control.txt` | Session B's lock wait and the prevented second reservation. |
| `05-verification.txt` | All expected outcomes and unchanged `public` state. |

Student screenshots are pending capture. Personal capture commands for the
recorded run live in the ignored local `evidence/README.md`; the guide itself is
intentionally excluded from the repository.

## Reflection and Sources

Transactions protect a business operation that spans more than one write. The
commit/rollback examples make the connection explicit: a reservation event is
not useful if its inventory decrement disappears, and an inventory decrement is
not acceptable if the corresponding reservation fails. `REPEATABLE READ` gives
an internally consistent view for work that needs multiple reads, while the
guarded `UPDATE` handles a small, high-contention stock allocation safely.

The measured example is local and intentionally narrow. It demonstrates a
PostgreSQL behaviour, not a production load test or a complete order-processing
architecture.

- MIT 8103 original CA brief, Portfolio 3: commit, rollback, isolation,
  concurrency issue/control mechanism, and screenshot/output evidence.
- [PostgreSQL 16: Transaction Isolation](https://www.postgresql.org/docs/16/transaction-iso.html)
- [PostgreSQL 16: Explicit Locking](https://www.postgresql.org/docs/16/explicit-locking.html)

OpenAI Codex assisted with the lab SQL, orchestration script and documentation.
The student should review the transaction flow, capture their own screenshots,
and write their personal learning reflection before final submission.
