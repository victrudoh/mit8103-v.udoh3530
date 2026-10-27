#!/usr/bin/env python3
"""Run and preserve the NexaCart Portfolio 5 replication and failover evidence.

The script rebuilds the isolated `nexacart-p5` Compose project from scratch,
so it deletes only that project's containers and volumes.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, List, Optional, Tuple


ROOT = Path(__file__).resolve().parents[2]
PORTFOLIO = ROOT / "portfolio-5-distributed-cloud"
SQL = PORTFOLIO / "sql"
EVIDENCE = PORTFOLIO / "evidence"
COMPOSE = ["docker", "compose", "-f", str(PORTFOLIO / "docker-compose.yml")]
DATABASE = "nexacart_portfolio1"
USER = "nexacart_user"
PRIMARY = "pg-primary"
REPLICA = "pg-replica"
TABLES = [
    "customers", "addresses", "categories", "products", "inventory",
    "orders", "order_items", "payments", "shipments", "reviews",
]


class PortfolioError(RuntimeError):
    pass


def run(command: List[str], input_text: str = "", check: bool = True) -> subprocess.CompletedProcess:
    result = subprocess.run(
        command, cwd=ROOT, input=input_text, text=True,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
    )
    if check and result.returncode:
        raise PortfolioError(result.stderr.strip() or "Command failed: {}".format(" ".join(command)))
    return result


def psql_command(node: str, tuples_only: bool) -> List[str]:
    command = COMPOSE + [
        "exec", "-T", node, "psql", "-X", "-q", "-v", "ON_ERROR_STOP=1",
        "-P", "pager=off", "-U", USER, "-d", DATABASE,
    ]
    if tuples_only:
        command += ["-A", "-t", "-F", "|"]
    return command


def show(node: str, sql: str) -> str:
    """Run SQL and return psql's aligned output, for readable evidence."""
    return run(psql_command(node, False), sql).stdout.rstrip()


def value(node: str, sql: str) -> str:
    """Run SQL expected to return exactly one value."""
    rows = [line for line in run(psql_command(node, True), sql).stdout.splitlines() if line]
    if len(rows) != 1:
        raise PortfolioError("Expected one value from {}, got {!r}".format(node, rows))
    return rows[0]


def try_sql(node: str, sql: str) -> subprocess.CompletedProcess:
    return run(psql_command(node, False), sql, check=False)


def wait_for(description: str, condition: Callable[[], bool], timeout: float = 90, interval: float = 0.5) -> float:
    started = time.monotonic()
    while time.monotonic() - started < timeout:
        try:
            if condition():
                return time.monotonic() - started
        except PortfolioError:
            pass
        time.sleep(interval)
    raise PortfolioError("Timed out waiting for: {}".format(description))


def require(actual: str, expected: str, description: str) -> None:
    if actual != expected:
        raise PortfolioError("{}: expected {}, got {}".format(description, expected, actual))


def node_ready(node: str) -> bool:
    return run(COMPOSE + ["exec", "-T", node, "pg_isready", "-U", USER, "-d", DATABASE], check=False).returncode == 0


def replica_caught_up() -> None:
    """Block until the replica has replayed everything the primary has written."""
    lsn = value(PRIMARY, "SELECT pg_current_wal_lsn();")
    wait_for(
        "replica to replay LSN {}".format(lsn),
        lambda: value(REPLICA, "SELECT pg_wal_lsn_diff(pg_last_wal_replay_lsn(), '{}') >= 0;".format(lsn)) == "t",
    )


def public_digest(node: str) -> str:
    result = run(COMPOSE + [
        "exec", "-T", node, "pg_dump", "-U", USER, "-d", DATABASE, "--schema=public",
        "--data-only", "--no-owner", "--no-privileges",
    ])
    # pg_dump 16 adds random guard commands; they are not data state.
    stable = [
        line for line in result.stdout.splitlines()
        if not line.startswith("\\restrict ") and not line.startswith("\\unrestrict ")
    ]
    return hashlib.sha256("\n".join(stable).encode("utf-8")).hexdigest()


def table_counts(node: str) -> str:
    union = "\nUNION ALL\n".join(
        "SELECT '{0}' AS table_name, COUNT(*) AS rows FROM public.{0}".format(table) for table in TABLES
    )
    return show(node, union + "\nORDER BY 1;")


def probe_rows(node: str) -> str:
    return show(node, "SELECT probe_id, note FROM p5_distributed.replication_probe ORDER BY probe_id;")


def probe_count(node: str, note: str) -> str:
    return value(node, "SELECT COUNT(*) FROM p5_distributed.replication_probe WHERE note = '{}';".format(note))


REPLICATION_STATUS = (
    "SELECT application_name, state, sync_state FROM pg_stat_replication;"
)


def reset_stack() -> None:
    run(COMPOSE + ["down", "-v", "--remove-orphans"])
    run(COMPOSE + ["up", "-d", "--wait"])
    wait_for("replica streaming", lambda: value(
        PRIMARY, "SELECT COUNT(*) FROM pg_stat_replication WHERE state = 'streaming';") == "1")


def section_topology() -> str:
    services = run(COMPOSE + ["ps", "--format", "{{.Service}}: {{.State}} ({{.Health}})"]).stdout.strip()
    return "\n".join([
        "PORTFOLIO 5 TOPOLOGY: one primary and one streaming replica",
        "",
        "Containers (isolated Compose project nexacart-p5):",
        "\n".join(sorted(services.splitlines())),
        "",
        "primary: SELECT pg_is_in_recovery() -> {}".format(value(PRIMARY, "SELECT pg_is_in_recovery();")),
        "replica: SELECT pg_is_in_recovery() -> {}".format(value(REPLICA, "SELECT pg_is_in_recovery();")),
        "",
        "Primary view of its standbys (pg_stat_replication):",
        show(PRIMARY, REPLICATION_STATUS),
        "",
        "Replication slot on the primary:",
        show(PRIMARY, "SELECT slot_name, slot_type, active FROM pg_replication_slots;"),
        "",
        "PASS: primary accepts writes; replica is a read-only standby streaming from it.",
        "",
    ])


def section_replication() -> Tuple[str, str]:
    run(COMPOSE + ["exec", "-T", PRIMARY, "psql", "-X", "-q", "-v", "ON_ERROR_STOP=1", "--single-transaction",
                   "-U", USER, "-d", DATABASE, "-f", "/sql/01-create-schema.sql"])
    run(COMPOSE + ["exec", "-T", PRIMARY, "psql", "-X", "-q", "-v", "ON_ERROR_STOP=1",
                   "-U", USER, "-d", DATABASE, "-f", "/sql/02-seed-data.sql"])
    run(psql_command(PRIMARY, False), (SQL / "01-create-probe.sql").read_text(encoding="utf-8"))
    replica_caught_up()

    primary_counts, replica_counts = table_counts(PRIMARY), table_counts(REPLICA)
    require(replica_counts, primary_counts, "replica table counts")
    report = (
        "SELECT status, COUNT(*) AS orders, SUM(total_amount) AS revenue "
        "FROM orders GROUP BY status ORDER BY status;"
    )
    primary_report, replica_report = show(PRIMARY, report), show(REPLICA, report)
    require(replica_report, primary_report, "replica order-status report")
    primary_hash, replica_hash = public_digest(PRIMARY), public_digest(REPLICA)
    require(replica_hash, primary_hash, "public data digest")

    return "\n".join([
        "REPLICATION OF THE NEXACART DATA",
        "The Portfolio 1 schema and seed data were loaded ONLY on the primary.",
        "",
        "Row counts on the primary:",
        primary_counts,
        "",
        "Row counts on the replica (read from the standby):",
        replica_counts,
        "",
        "Order-status report run on the REPLICA (identical to the primary):",
        replica_report,
        "",
        "SHA-256 of public data, primary: {}".format(primary_hash),
        "SHA-256 of public data, replica: {}".format(replica_hash),
        "PASS: all ten NexaCart tables replicated with identical data.",
        "",
    ]), primary_hash


def section_read_only() -> str:
    failed_customer = try_sql(REPLICA, "INSERT INTO customers (first_name, last_name, email) "
                                       "VALUES ('Replica', 'Write', 'replica.write@nexacart.example');")
    failed_probe = try_sql(REPLICA, "INSERT INTO p5_distributed.replication_probe (note) VALUES ('replica-write');")
    for result in (failed_customer, failed_probe):
        if result.returncode == 0 or "read-only transaction" not in result.stderr:
            raise PortfolioError("Replica accepted a write or failed for another reason: {}".format(result.stderr))
    require(value(PRIMARY, "SELECT COUNT(*) FROM public.customers WHERE email = 'replica.write@nexacart.example';"),
            "0", "rejected replica write must not exist on the primary")
    return "\n".join([
        "REPLICA IS READ-ONLY",
        "Attempt: INSERT INTO customers ... on the replica",
        failed_customer.stderr.strip(),
        "",
        "Attempt: INSERT INTO p5_distributed.replication_probe ... on the replica",
        failed_probe.stderr.strip(),
        "",
        "PASS: writes are rejected on the replica and nothing reached the primary.",
        "",
    ])


def section_consistency() -> str:
    lines = ["EVENTUAL CONSISTENCY WITH ASYNCHRONOUS REPLICATION", ""]
    run(psql_command(PRIMARY, False), "INSERT INTO p5_distributed.replication_probe (note) VALUES ('normal-write');")
    started = time.monotonic()
    wait_for("normal write on replica", lambda: probe_count(REPLICA, "normal-write") == "1", timeout=30, interval=0.01)
    elapsed_ms = (time.monotonic() - started) * 1000
    lines += [
        "1. A normal write on the primary became visible on the replica after about "
        "{:.0f} ms (local Docker polling; not a production latency figure).".format(elapsed_ms),
        "",
    ]

    run(psql_command(REPLICA, False), "SELECT pg_wal_replay_pause();")
    wait_for("replay paused", lambda: value(REPLICA, "SELECT pg_is_wal_replay_paused();") == "t", timeout=20, interval=0.1)
    run(psql_command(PRIMARY, False), "INSERT INTO p5_distributed.replication_probe (note) VALUES ('while-replay-paused');")
    primary_sees = probe_count(PRIMARY, "while-replay-paused")
    replica_sees = probe_count(REPLICA, "while-replay-paused")
    require(primary_sees, "1", "primary sees paused-replay write")
    require(replica_sees, "0", "replica must be stale while replay is paused")
    lag = show(PRIMARY,
        "SELECT application_name, state, sync_state, "
        "pg_wal_lsn_diff(sent_lsn, replay_lsn) AS replay_backlog_bytes FROM pg_stat_replication;")
    lines += [
        "2. Replica WAL replay was paused with pg_wal_replay_pause(), then a row was committed on the primary.",
        "   rows named 'while-replay-paused' on the primary: {}".format(primary_sees),
        "   rows named 'while-replay-paused' on the replica: {}   <- stale read".format(replica_sees),
        "   Primary's view of the lag:",
        "\n".join("   " + line for line in lag.splitlines()),
        "",
    ]

    run(COMPOSE + ["exec", "-T", REPLICA, "psql", "-X", "-q", "-U", USER, "-d", DATABASE,
                   "-c", "SELECT pg_wal_replay_resume();"])
    wait_for("replica catch-up after resume", lambda: probe_count(REPLICA, "while-replay-paused") == "1", timeout=30)
    lines += [
        "3. Replay was resumed. The replica caught up and now returns the row: "
        "{}".format(probe_count(REPLICA, "while-replay-paused")),
        "",
        "PASS: reads from an asynchronous replica can be stale, and they converge once WAL is replayed.",
        "",
    ]
    return "\n".join(lines)


def section_availability() -> str:
    lines = ["AVAILABILITY VERSUS CONSISTENCY: replica outage", ""]

    # Asynchronous mode: the primary keeps accepting writes without its standby.
    run(COMPOSE + ["stop", REPLICA])
    standbys = value(PRIMARY, "SELECT COUNT(*) FROM pg_stat_replication;")
    require(standbys, "0", "standbys connected after replica stop")
    run(psql_command(PRIMARY, False), "INSERT INTO p5_distributed.replication_probe (note) VALUES ('async-write-replica-down');")
    lines += [
        "A. Asynchronous mode (default). The replica container was stopped.",
        "   standbys connected to the primary: {}".format(standbys),
        "   INSERT 'async-write-replica-down' on the primary: committed immediately.",
        "",
    ]
    run(COMPOSE + ["start", REPLICA])
    wait_for("replica ready", lambda: node_ready(REPLICA))
    wait_for("replica visible write", lambda: probe_count(REPLICA, "async-write-replica-down") == "1", timeout=60)
    lines += [
        "   The replica was restarted, reconnected through its replication slot and "
        "received the missed write: rows = {}".format(probe_count(REPLICA, "async-write-replica-down")),
        "   -> availability for writes was kept; the replica was temporarily behind.",
        "",
    ]

    # Synchronous mode: a commit waits for the standby, trading availability for durability.
    run(psql_command(PRIMARY, False), "ALTER SYSTEM SET synchronous_standby_names = 'replica1';")
    run(psql_command(PRIMARY, False), "SELECT pg_reload_conf();")
    wait_for("sync standby", lambda: value(
        PRIMARY, "SELECT COUNT(*) FROM pg_stat_replication WHERE sync_state = 'sync';") == "1", timeout=30)
    lines += [
        "B. Synchronous mode: synchronous_standby_names = 'replica1'.",
        show(PRIMARY, REPLICATION_STATUS),
        "",
    ]
    run(COMPOSE + ["stop", REPLICA])
    writer = subprocess.Popen(
        psql_command(PRIMARY, False), cwd=ROOT, text=True,
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    )
    assert writer.stdin is not None
    writer.stdin.write("INSERT INTO p5_distributed.replication_probe (note) VALUES ('sync-write-waiting');\n")
    writer.stdin.close()
    try:
        wait_for("commit waiting for synchronous replication", lambda: value(
            PRIMARY, "SELECT COUNT(*) FROM pg_stat_activity WHERE wait_event = 'SyncRep';") == "1", timeout=30, interval=0.2)
        waiting = show(PRIMARY,
            "SELECT wait_event_type, wait_event, left(query, 80) AS query FROM pg_stat_activity WHERE wait_event = 'SyncRep';")
        still_running = writer.poll() is None
        require(str(still_running), "True", "client commit blocked while replica is down")
        lines += [
            "   The replica was stopped again and the same kind of INSERT was issued.",
            "   The client is NOT acknowledged; the primary reports:",
            "\n".join("   " + line for line in waiting.splitlines()),
            "   (The row is already written on the primary; PostgreSQL only withholds the commit",
            "   acknowledgement from the client until the standby confirms it has the WAL.)",
            "",
        ]
        run(COMPOSE + ["start", REPLICA])
        wait_for("replica ready", lambda: node_ready(REPLICA))
        writer.wait(timeout=60)
        if writer.returncode:
            raise PortfolioError("Blocked write failed: {}".format(writer.stderr.read() if writer.stderr else ""))
    finally:
        if writer.poll() is None:
            writer.kill()
            writer.wait(timeout=10)
    wait_for("replica visible write", lambda: probe_count(REPLICA, "sync-write-waiting") == "1", timeout=60)
    lines += [
        "   Once the replica returned, the commit was acknowledged (exit status 0) and the row is on the replica: "
        "{}".format(probe_count(REPLICA, "sync-write-waiting")),
        "   -> the write waited instead of completing, favouring consistency over availability.",
        "",
    ]
    run(psql_command(PRIMARY, False), "ALTER SYSTEM RESET synchronous_standby_names;")
    run(psql_command(PRIMARY, False), "SELECT pg_reload_conf();")
    wait_for("async mode restored", lambda: value(
        PRIMARY, "SELECT COUNT(*) FROM pg_stat_replication WHERE sync_state = 'async';") == "1", timeout=30)
    lines += [
        "C. synchronous_standby_names was reset; the standby is asynchronous again.",
        show(PRIMARY, REPLICATION_STATUS),
        "",
        "PASS: asynchronous commits stayed available during the outage; synchronous commits waited for the standby.",
        "",
    ]
    return "\n".join(lines)


def section_failover(primary_digest: str) -> str:
    replica_caught_up()
    before_probe = probe_rows(REPLICA)
    lines = ["MANUAL FAILOVER: primary crash and replica promotion", ""]

    run(COMPOSE + ["kill", PRIMARY])
    lines += ["1. The primary container was killed (simulated crash).", ""]

    read_during_outage = value(REPLICA, "SELECT COUNT(*) FROM public.customers;")
    rejected = try_sql(REPLICA, "INSERT INTO p5_distributed.replication_probe (note) VALUES ('write-before-promotion');")
    if rejected.returncode == 0 or "read-only transaction" not in rejected.stderr:
        raise PortfolioError("Replica accepted a write before promotion")
    lines += [
        "2. The replica still serves reads: customers = {}".format(read_during_outage),
        "   but rejects writes before promotion:",
        "   " + rejected.stderr.strip(),
        "",
    ]

    promoted = value(REPLICA, "SELECT pg_promote(wait => true, wait_seconds => 60);")
    require(promoted, "t", "promotion result")
    require(value(REPLICA, "SELECT pg_is_in_recovery();"), "f", "replica recovery state after promotion")
    lines += [
        "3. SELECT pg_promote() on the replica -> {}".format(promoted),
        "   SELECT pg_is_in_recovery() on the promoted node -> f",
        "",
    ]

    after_digest = public_digest(REPLICA)
    require(after_digest, primary_digest, "public data digest after failover")
    require(probe_rows(REPLICA), before_probe, "probe rows after failover")
    run(psql_command(REPLICA, False), "INSERT INTO p5_distributed.replication_probe (note) VALUES ('write-after-promotion');")
    require(probe_count(REPLICA, "write-after-promotion"), "1", "write after promotion")
    lines += [
        "4. NexaCart public data on the promoted node matches the original primary.",
        "   SHA-256 before failure (primary): {}".format(primary_digest),
        "   SHA-256 after promotion (replica): {}".format(after_digest),
        "   A new write on the promoted node succeeded: 'write-after-promotion' = {}".format(
            probe_count(REPLICA, "write-after-promotion")),
        "",
        "PASS: the promoted replica retained all committed data and now accepts writes.",
        "NOTE: the old primary is deliberately not restarted. Bringing it back as a writer would create a",
        "      split-brain; it would need pg_rewind or a fresh base backup to rejoin as a standby.",
        "",
    ]
    return "\n".join(lines)


def write(path: Path, content: str) -> None:
    path.write_text(content.rstrip() + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    output = args.output or EVIDENCE / ("run-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ"))
    output = output.resolve()
    if ROOT not in output.parents or output.exists():
        raise PortfolioError("Output must be a new directory inside this repository")
    output.mkdir(parents=True)

    reset_stack()
    server_version = value(PRIMARY, "SHOW server_version;")
    write(output / "01-topology.txt", section_topology())
    replication_text, primary_digest = section_replication()
    write(output / "02-data-replication.txt", replication_text)
    write(output / "03-read-only-replica.txt", section_read_only())
    write(output / "04-eventual-consistency.txt", section_consistency())
    write(output / "05-availability-and-synchronous-commit.txt", section_availability())
    write(output / "06-failover-promotion.txt", section_failover(primary_digest))
    write(output / "07-verification.txt", "\n".join([
        "PORTFOLIO 5 VERIFICATION",
        "PASS: primary and replica formed a streaming replication pair.",
        "PASS: the Portfolio 1 data replicated to the replica with an identical SHA-256.",
        "PASS: the replica rejected writes while in recovery.",
        "PASS: a paused replica returned a stale read and converged after resuming.",
        "PASS: asynchronous commits succeeded with the replica down; synchronous commits waited for it.",
        "PASS: after a simulated primary crash, the promoted replica kept the data and accepted writes.",
        "Public data SHA-256: {}".format(primary_digest),
        "",
    ]))
    write(output / "environment.json", json.dumps({
        "image": "postgres:16",
        "server_version": server_version,
        "project": "nexacart-p5",
        "ports": {"primary": 55433, "replica": 55434},
        "recorded_at": datetime.now(timezone.utc).isoformat(),
    }, indent=2))
    print("Portfolio 5 evidence written to {}".format(output.relative_to(ROOT)))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except PortfolioError as error:
        print("Portfolio 5 failed: {}".format(error), file=sys.stderr)
        raise SystemExit(1)
