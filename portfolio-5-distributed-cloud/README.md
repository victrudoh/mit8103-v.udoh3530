# Portfolio 5 - Distributed and Cloud Database Exercise

## Purpose

This portfolio takes the NexaCart PostgreSQL database from Portfolio 1 and runs
it as a small distributed system: one **primary** that accepts writes and one
**streaming replica** that serves reads. It then shows, with recorded output,
what replication does to availability and consistency, and what happens when the
primary fails.

It is a local simulation in Docker. No cloud account or managed service was used,
so the cloud material below is a discussion of how the same ideas map to hosted
databases, not deployment evidence.

## Topology

| Node | Container | Host port | Role |
| --- | --- | --- | --- |
| `pg-primary` | `nexacart-p5-primary` | 55433 | Read/write; sends WAL to the replica |
| `pg-replica` | `nexacart-p5-replica` | 55434 | Hot standby; read-only while in recovery |

Both run `postgres:16`. The lab is its own Compose project, `nexacart-p5`, defined
in [docker-compose.yml](docker-compose.yml). It has its own containers, network and
volumes, so it cannot change the Portfolio 1-4 databases, which keep using the
repository-root `docker-compose.yml` and ports 55432 and 27017.

How the pair is built:

1. [primary-init.sh](docker/primary-init.sh) runs once on the primary. It creates a
   `replicator` role with the `REPLICATION` privilege and adds a `pg_hba.conf`
   rule. The default rules never match replication connections from other
   containers, because `all` in the database column excludes them.
2. [replica-entrypoint.sh](docker/replica-entrypoint.sh) takes a `pg_basebackup`
   of the primary on first start. `--write-recovery-conf` creates
   `standby.signal` and the connection settings, `--wal-method=stream` copies WAL
   during the backup, and `--create-slot` creates a physical replication slot so
   the primary retains WAL the replica has not yet received.
3. The replica connects with `application_name=replica1`, which is how the
   primary identifies it in `pg_stat_replication` and in
   `synchronous_standby_names`.

The primary is started with `wal_level=replica`, `max_wal_senders=5` and
`max_replication_slots=5`.

## What Was Demonstrated

The runner [run_portfolio.py](scripts/run_portfolio.py) rebuilds the lab from
scratch and records one text file per demonstration. Data is written only on the
primary, so anything found on the replica arrived through replication.

| Demonstration | Distributed concept | Result recorded |
| --- | --- | --- |
| Topology | Primary/standby roles | `pg_is_in_recovery()` is `f` on the primary, `t` on the replica; `replica1` is `streaming`, slot `replica_slot_1` is active. |
| Data replication | Replication | The Portfolio 1 schema and seed were loaded on the primary only. All ten tables have identical row counts on the replica, the order-status report matches, and the SHA-256 of the `public` data is identical on both nodes. |
| Read-only replica | Read scaling, safety | `INSERT` on the replica fails with `cannot execute INSERT in a read-only transaction`. |
| Paused replay | Eventual consistency | With replay paused on the replica, a row committed on the primary is returned by the primary but not by the replica (a stale read). After resuming, the replica converges. |
| Replica outage, async | Availability | With the replica stopped, the primary still commits. The replica catches up through its slot after restart. |
| Replica outage, sync | Consistency over availability | With `synchronous_standby_names = 'replica1'`, a commit made while the replica is down shows `wait_event = SyncRep` and is not acknowledged to the client until the replica returns. |
| Failover | High availability | The primary was killed. The replica kept serving reads, rejected writes, and was promoted with `pg_promote()`. Its `public` data hash equalled the original primary's, and it then accepted a new write. |

The ten NexaCart tables are never modified by the experiments. Probe rows go into
a separate `p5_distributed.replication_probe` table, created by
[01-create-probe.sql](sql/01-create-probe.sql), so the replicated `public` data
stays identical to Portfolio 1.

## Consistency and Availability Trade-offs

| Mode | Behaviour with the replica down | Behaviour with a replica that lags | Fits |
| --- | --- | --- | --- |
| Asynchronous (default) | Writes keep committing | Replica reads can be stale; committed data could be lost if the primary fails before the replica receives it | Reporting, catalogue browsing, order-history reads |
| Synchronous | Commits wait for the standby | The standby has the WAL when the client is acknowledged | Payments or stock changes that must not be lost |

In CAP terms, the synchronous setup behaves like a consistency-first (CP) system
during a partition or standby outage, since writes stall rather than diverge. The
asynchronous setup behaves like an availability-first (AP) system, since writes
continue and the replica becomes temporarily stale. The more useful everyday
framing is PACELC: even with no failure there is a latency-versus-consistency
choice, because waiting for a standby makes each commit slower.

The measured propagation time in the recorded run (about 123 ms) is a single
local sample on one machine. It shows that replication is quick on a local
network, not what to expect in production.

### Suitable NexaCart workloads

- **Replica reads:** catalogue browsing, order history and the Portfolio 2
  reports can run on the replica and take load off the primary, accepting that a
  result may be slightly behind.
- **Primary only:** placing an order, reducing stock, and the Portfolio 3
  reservation logic need the latest committed state and row locks, so they stay on
  the primary. Reading stock from an asynchronous replica to decide whether to
  sell the last item would reintroduce the oversell that Portfolio 3 prevents.

## Failover Limits

The failover here is manual. A real deployment needs something to detect the
failure, choose a new primary and redirect clients, which this lab does not
include. Two limits are worth stating:

- The old primary is deliberately left stopped. If it restarted and accepted
  writes while the promoted replica did too, the two would diverge (split-brain).
  It would need `pg_rewind` or a fresh base backup to rejoin as a standby.
- With asynchronous replication, a primary that crashes could have committed
  transactions the replica never received. This run lost nothing because the
  replica had caught up first, and that check is part of the script. The run does
  not show data loss, and that outcome should not be assumed in general.

## Sharding (Discussion Only)

Sharding was not implemented; replication copies the whole database to every
node, while sharding splits it. If NexaCart outgrew one primary, the main design
question would be the shard key:

- **`orders` and `payments` by `customer_id`** (hashed) would keep one customer's
  history on one shard, which suits the customer order-history query.
- **`products` and `inventory` by `product_id`** would keep a product and its stock
  together.
- An order contains products from many shards. The foreign keys and the atomic
  stock reservation from Portfolio 3 rely on a single node's row locks and
  transactions. Across shards they would need distributed transactions or a
  redesign such as reserving stock through a saga, which is much more complex.
- For the Portfolio 4 MongoDB catalogue, hashing `source.postgres_product_id`
  would spread documents evenly, whereas sharding on `category.id` could place
  most traffic on a popular category. MongoDB supports sharded clusters natively,
  but that was not run here.

## Cloud Mapping (Discussion Only)

Managed relational services generally package the pieces built by hand here:
a primary with one or more read replicas, an optional synchronous standby in
another availability zone for automatic failover, and automated backups with
point-in-time recovery. Managed MongoDB offerings similarly run replica sets and
optionally sharded clusters. What the provider takes over is the failure
detection, promotion and client redirection that this lab does manually. What
stays with the application owner is the read/write split, tolerance for stale
reads and the choice of sync versus async. Exact feature names and guarantees
differ by provider and should be checked against current provider documentation
before relying on them. No cloud service was used for this portfolio.

## How to Run

From the repository root, with Docker running:

```bash
python3 portfolio-5-distributed-cloud/scripts/run_portfolio.py
```

The runner starts by deleting and recreating the `nexacart-p5` project's
containers and volumes (`down -v`) and then builds them with `up -d --wait`, so
each run starts clean. It affects nothing
outside that project. It needs only the Python standard library, and a run takes
about half a minute. It writes a new timestamped directory under `evidence/`, and
it ends with the primary stopped and the replica promoted.

After the run, the old primary is stopped and the promoted replica is the only
live node. To inspect it by hand:

```bash
docker compose -f portfolio-5-distributed-cloud/docker-compose.yml ps -a
docker compose -f portfolio-5-distributed-cloud/docker-compose.yml exec pg-replica psql -U nexacart_user -d nexacart_portfolio1 -c "SELECT pg_is_in_recovery();" -c "SELECT COUNT(*) FROM customers;"
```

To remove the lab completely:

```bash
docker compose -f portfolio-5-distributed-cloud/docker-compose.yml down -v
```

The database credentials are disposable local values in the Compose file. The
replica has no authentication hardening and the ports are published only for
local development; do not expose this configuration unchanged.

## Evidence

The recorded run is in
[run-20261027T104044054148Z](evidence/run-20261027T104044054148Z/).

| File | Evidence |
| --- | --- |
| `01-topology.txt` | Container health, recovery state of each node, `pg_stat_replication`, replication slot. |
| `02-data-replication.txt` | Row counts, an order report and a data hash compared across both nodes. |
| `03-read-only-replica.txt` | Write rejected on the replica. |
| `04-eventual-consistency.txt` | Normal propagation, stale read while replay is paused, and convergence. |
| `05-availability-and-synchronous-commit.txt` | Async write during an outage, then a synchronous commit held at `SyncRep`. |
| `06-failover-promotion.txt` | Primary crash, replica reads and rejected writes, promotion, matching data hash. |
| `07-verification.txt` | Summary of every check and the final data hash. |
| `environment.json` | PostgreSQL image and server version. |

I captured screenshots of each output from the recorded run in the
[evidence folder](evidence/): `01-topology.png`, `02-data-replication.png`,
`03-read-only-replica.png`, `04-eventual-consistency.png`,
`05-availability-and-synchronous-commit.png`, `06-failover-promotion.png` and
`07-verification.png`. `08-lab-state.png` shows `docker compose ps -a` after the
run, with the primary exited and the promoted replica running. My capture
instructions are in the ignored `evidence/README.md`, which is intentionally not
part of the submission.

## Limitations

- Two nodes on one machine share the same host, so a real network partition,
  clock difference or data-centre failure is not tested.
- There is one replica and no automatic failover manager, no connection pooler and
  no load balancer, so the read/write split is something the application would
  have to implement.
- Sharding and cloud deployment are discussed, not implemented.

## Sources

- MIT 8103 original CA brief, Portfolio 5: a distributed or cloud database
  discussion or setup based on the same case study, including replication,
  sharding, availability, consistency or deployment evidence.
- [PostgreSQL 16: High Availability, Load Balancing, and Replication](https://www.postgresql.org/docs/16/high-availability.html)
- [PostgreSQL 16: Log-Shipping Standby Servers](https://www.postgresql.org/docs/16/warm-standby.html) (streaming replication, replication slots, synchronous replication)
- [PostgreSQL 16: Hot Standby](https://www.postgresql.org/docs/16/hot-standby.html)
- [PostgreSQL 16: pg_basebackup](https://www.postgresql.org/docs/16/app-pgbasebackup.html)
- [PostgreSQL 16: Recovery Control Functions](https://www.postgresql.org/docs/16/functions-admin.html#FUNCTIONS-RECOVERY-CONTROL) (`pg_wal_replay_pause`, `pg_promote`)
- [PostgreSQL 16: pg_rewind](https://www.postgresql.org/docs/16/app-pgrewind.html)
- [MongoDB: Sharding](https://www.mongodb.com/docs/manual/sharding/)

## AI Use Declaration

- **Tool used:** Cursor's AI coding assistant.
- **What it was used for:** designing the primary/replica lab, writing the Compose
  file, the primary and replica start-up scripts, the probe SQL, the evidence
  runner, and this documentation including the sharding and cloud discussion.
- **How the output was verified:** the runner executed every demonstration against
  real PostgreSQL 16 containers. Each step checks its own outcome and stops with
  an error otherwise: replica row counts and the SHA-256 of the `public` data
  against the primary, the rejected writes, the stale read while replay is paused,
  the `SyncRep` wait during a synchronous commit, and the data hash after
  promotion. The hash is the same value Portfolio 4 recorded for the main
  database, which shows the replicated data is the Portfolio 1 data. No output or
  screenshot is invented.

AI assistance and automated checks do not establish my understanding. I remain
responsible for reviewing, running and explaining the submitted work, and I will
write my own reflection for the final submission.
