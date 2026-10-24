#!/usr/bin/env python3
"""Run and preserve the NexaCart Portfolio 3 transaction demonstrations."""

from __future__ import annotations

import argparse
import hashlib
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional


ROOT = Path(__file__).resolve().parents[2]
PORTFOLIO = ROOT / "portfolio-3-transactions-concurrency"
SQL = PORTFOLIO / "sql"
EVIDENCE = PORTFOLIO / "evidence"
DATABASE = "nexacart_portfolio1"


class PortfolioError(RuntimeError):
    pass


def psql_command(database: str, tuples_only: bool = False) -> List[str]:
    command = [
        "docker", "compose", "exec", "-T", "postgres", "psql", "-X", "-q",
        "-v", "ON_ERROR_STOP=1", "-P", "pager=off", "-U", "nexacart_user",
        "-d", database,
    ]
    if tuples_only:
        command.extend(["-A", "-t", "-F", "|"])
    return command


def run_psql(sql: str, database: str = DATABASE, tuples_only: bool = False) -> str:
    result = subprocess.run(
        psql_command(database, tuples_only),
        input=sql,
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if result.returncode:
        raise PortfolioError(result.stderr.strip() or "psql command failed")
    return result.stdout


def run_sql_file(path: Path, database: str = DATABASE) -> str:
    return run_psql(path.read_text(encoding="utf-8"), database)


def scalar(sql: str, database: str = DATABASE) -> str:
    rows = [line for line in run_psql(sql, database, tuples_only=True).splitlines() if line]
    if len(rows) != 1:
        raise PortfolioError("Expected one scalar result, got: {!r}".format(rows))
    return rows[0]


def public_digest(database: str) -> str:
    result = subprocess.run(
        [
            "docker", "compose", "exec", "-T", "postgres", "pg_dump", "-U",
            "nexacart_user", "-d", database, "--schema=public", "--data-only",
            "--no-owner", "--no-privileges",
        ],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if result.returncode:
        raise PortfolioError(result.stderr.strip() or "pg_dump command failed")
    # PostgreSQL 16 emits random pg_dump guard commands; they are not data state.
    stable_lines = [
        line for line in result.stdout.splitlines()
        if not line.startswith("\\restrict ") and not line.startswith("\\unrestrict ")
    ]
    return hashlib.sha256("\n".join(stable_lines).encode("utf-8")).hexdigest()


class PsqlSession:
    """A small interactive psql wrapper for deterministic two-session examples."""

    def __init__(self, database: str) -> None:
        self.process = subprocess.Popen(
            psql_command(database, tuples_only=True),
            cwd=ROOT,
            text=True,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            bufsize=1,
        )
        self.marker_number = 0

    def send(self, sql: str) -> str:
        if self.process.stdin is None or self.process.stdout is None:
            raise PortfolioError("psql session pipes are unavailable")
        self.marker_number += 1
        marker = "__P3_COMPLETE_{}__".format(self.marker_number)
        self.process.stdin.write(sql.rstrip() + "\n\\echo {}\n".format(marker))
        self.process.stdin.flush()
        return marker

    def collect(self, marker: str) -> List[str]:
        if self.process.stdout is None:
            raise PortfolioError("psql session output is unavailable")
        rows: List[str] = []
        while True:
            line = self.process.stdout.readline()
            if not line:
                stderr = self.process.stderr.read() if self.process.stderr else ""
                raise PortfolioError("psql session ended unexpectedly: {}".format(stderr.strip()))
            value = line.rstrip("\n")
            if value == marker:
                return rows
            if value:
                rows.append(value)

    def execute(self, sql: str) -> List[str]:
        return self.collect(self.send(sql))

    def close(self) -> None:
        if self.process.poll() is None and self.process.stdin is not None:
            self.process.stdin.write("\\q\n")
            self.process.stdin.flush()
        try:
            self.process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            self.process.kill()
            self.process.wait(timeout=5)


def require(actual: str, expected: str, description: str) -> None:
    if actual != expected:
        raise PortfolioError("{}: expected {}, got {}".format(description, expected, actual))


def run_repeatable_read(database: str) -> str:
    reader = PsqlSession(database)
    writer = PsqlSession(database)
    try:
        initial = reader.execute(
            "BEGIN ISOLATION LEVEL REPEATABLE READ;\n"
            "SELECT available_quantity FROM p3_concurrency.stock_control WHERE product_id = 3;"
        )
        require(initial[-1], "10", "repeatable-read initial quantity")
        writer.execute(
            "BEGIN;\n"
            "UPDATE p3_concurrency.stock_control SET available_quantity = available_quantity + 1, "
            "updated_at = CURRENT_TIMESTAMP WHERE product_id = 3 RETURNING available_quantity;\n"
            "COMMIT;"
        )
        repeat_read = reader.execute(
            "SELECT available_quantity FROM p3_concurrency.stock_control WHERE product_id = 3;\nCOMMIT;"
        )
        require(repeat_read[0], "10", "repeatable-read snapshot quantity")
        fresh_read = scalar(
            "SELECT available_quantity FROM p3_concurrency.stock_control WHERE product_id = 3;", database
        )
        require(fresh_read, "11", "post-commit fresh quantity")
        return "\n".join([
            "REPEATABLE READ ISOLATION DEMONSTRATION",
            "Session A began at REPEATABLE READ and read stock: {}".format(initial[-1]),
            "Session B replenished one unit and committed stock: 11",
            "Session A read again before ending its transaction: {}".format(repeat_read[0]),
            "A fresh transaction after Session A committed read stock: {}".format(fresh_read),
            "PASS: Session A retained its transaction snapshot; a new transaction saw the committed change.",
            "",
        ])
    finally:
        reader.close()
        writer.close()


def wait_for_lock(backend_pid: str, database: str) -> str:
    for _ in range(30):
        wait_event = scalar(
            "SELECT COALESCE(wait_event_type, '') || '|' || COALESCE(wait_event, '') "
            "FROM pg_stat_activity WHERE pid = {};".format(backend_pid),
            database,
        )
        if wait_event.startswith("Lock|"):
            return wait_event
        time.sleep(0.1)
    raise PortfolioError("Second reservation did not enter the expected lock wait")


def run_concurrent_reservation(database: str) -> str:
    run_psql(
        "BEGIN;\n"
        "TRUNCATE TABLE p3_concurrency.reservation_events RESTART IDENTITY;\n"
        "UPDATE p3_concurrency.stock_control SET available_quantity = 1, updated_at = CURRENT_TIMESTAMP "
        "WHERE product_id = 3;\nCOMMIT;",
        database,
    )
    session_a = PsqlSession(database)
    session_b = PsqlSession(database)
    try:
        session_a.execute("BEGIN;")
        reserved_by_a = session_a.execute(
            "WITH reserved_stock AS ("
            " UPDATE p3_concurrency.stock_control SET available_quantity = available_quantity - 1, "
            " updated_at = CURRENT_TIMESTAMP WHERE product_id = 3 AND available_quantity >= 1 "
            " RETURNING product_id, available_quantity"
            ") INSERT INTO p3_concurrency.reservation_events "
            "(request_reference, product_id, quantity, outcome) "
            "SELECT 'P3-CONCURRENT-A', product_id, 1, 'committed' FROM reserved_stock "
            "RETURNING request_reference;"
        )
        require(reserved_by_a[-1], "P3-CONCURRENT-A", "first guarded reservation")

        backend_pid = session_b.execute("SELECT pg_backend_pid();")[-1]
        session_b.execute("BEGIN; SET LOCAL lock_timeout = '10s';")
        pending = session_b.send(
            "WITH reserved_stock AS ("
            " UPDATE p3_concurrency.stock_control SET available_quantity = available_quantity - 1, "
            " updated_at = CURRENT_TIMESTAMP WHERE product_id = 3 AND available_quantity >= 1 "
            " RETURNING product_id, available_quantity"
            ") INSERT INTO p3_concurrency.reservation_events "
            "(request_reference, product_id, quantity, outcome) "
            "SELECT 'P3-CONCURRENT-B', product_id, 1, 'committed' FROM reserved_stock "
            "RETURNING request_reference;"
        )
        wait_event = wait_for_lock(backend_pid, database)
        session_a.execute("COMMIT;")
        reserved_by_b = session_b.collect(pending)
        require("|".join(reserved_by_b), "", "second guarded reservation")
        session_b.execute("COMMIT;")

        final_stock = scalar(
            "SELECT available_quantity FROM p3_concurrency.stock_control WHERE product_id = 3;", database
        )
        final_events = scalar(
            "SELECT COUNT(*) FROM p3_concurrency.reservation_events WHERE product_id = 3;", database
        )
        require(final_stock, "0", "final concurrent stock")
        require(final_events, "1", "committed concurrent reservations")
        return "\n".join([
            "CONCURRENT STOCK RESERVATION CONTROL",
            "Lab stock was reset to 1 unit before the two sessions began.",
            "Session A guarded reservation result: P3-CONCURRENT-A; stock became 0.",
            "Session B wait event while A held the row lock: {}".format(wait_event),
            "Session A committed its reservation.",
            "Session B guarded reservation result after the lock released: no row returned (UPDATE 0).",
            "Final stock: {}; committed reservation rows: {}".format(final_stock, final_events),
            "PASS: the atomic quantity predicate and PostgreSQL row lock prevented an oversell.",
            "",
        ])
    finally:
        session_a.close()
        session_b.close()


def write(path: Path, content: str) -> None:
    path.write_text(content.rstrip() + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", default=DATABASE)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    output = args.output or EVIDENCE / ("run-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ"))
    output = output.resolve()
    if ROOT not in output.parents or output.exists():
        raise PortfolioError("Output must be a new directory inside this repository")
    output.mkdir(parents=True)

    before_digest = public_digest(args.database)
    write(output / "00-setup.txt", run_sql_file(SQL / "01-create-transaction-lab.sql", args.database))
    commit_output = run_sql_file(SQL / "02-commit-reservation.sql", args.database)
    require(scalar("SELECT available_quantity FROM p3_concurrency.stock_control WHERE product_id = 3;", args.database), "10", "committed stock")
    require(scalar("SELECT COUNT(*) FROM p3_concurrency.reservation_events WHERE request_reference = 'P3-COMMIT-RESERVATION';", args.database), "1", "committed event")
    write(output / "01-commit-reservation.txt", commit_output + "\nPASS: committed reservation and stock decrement persisted.\n")

    rollback_output = run_sql_file(SQL / "03-rollback-reservation.sql", args.database)
    require(scalar("SELECT available_quantity FROM p3_concurrency.stock_control WHERE product_id = 3;", args.database), "10", "rolled-back stock")
    require(scalar("SELECT COUNT(*) FROM p3_concurrency.reservation_events WHERE request_reference = 'P3-ROLLBACK-RESERVATION';", args.database), "0", "rolled-back event")
    write(output / "02-rollback-reservation.txt", rollback_output + "\nPASS: rollback restored stock and removed the uncommitted event.\n")

    write(output / "03-repeatable-read-isolation.txt", run_repeatable_read(args.database))
    write(output / "04-concurrent-reservation-control.txt", run_concurrent_reservation(args.database))

    after_digest = public_digest(args.database)
    require(after_digest, before_digest, "public data and sequence state")
    write(output / "05-verification.txt", "\n".join([
        "PORTFOLIO 3 VERIFICATION",
        "PASS: commit demonstration persisted exactly one reservation and decremented lab stock.",
        "PASS: rollback demonstration left no reservation and restored lab stock.",
        "PASS: repeatable-read transaction kept its snapshot while a fresh transaction saw the committed change.",
        "PASS: guarded concurrent reservation left stock at zero with one committed reservation.",
        "PASS: public schema data and sequence state were unchanged.",
        "Public state SHA-256: {}".format(after_digest),
        "",
    ]))
    print("Portfolio 3 evidence written to {}".format(output.relative_to(ROOT)))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except PortfolioError as error:
        print("Portfolio 3 failed: {}".format(error), file=sys.stderr)
        raise SystemExit(1)
