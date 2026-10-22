#!/usr/bin/env python3
"""Run NexaCart Portfolio 2 through the existing Docker Compose PostgreSQL service."""

import argparse
import csv
import hashlib
import io
import json
import statistics
import subprocess
import sys
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path


PORTFOLIO = Path(__file__).resolve().parents[1]
ROOT = PORTFOLIO.parent
SQL = PORTFOLIO / "sql"
SETTINGS = """
SET max_parallel_workers_per_gather = 0;
SET jit = off;
SET work_mem = '16MB';
SET timezone = 'UTC';
SET statement_timeout = '120s';
SET enable_seqscan = on;
SET enable_indexscan = on;
SET enable_indexonlyscan = on;
SET enable_bitmapscan = on;
"""
INDEX_NAMES = ("p2_orders_customer_created_idx", "p2_orders_fulfilled_created_idx")


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def command(args, stdin=None):
    result = subprocess.run(args, input=stdin, text=True, capture_output=True,
                            cwd=ROOT, timeout=300)
    if result.returncode:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip())
    return result.stdout


def psql(database, statement, mode="text"):
    args = ["docker", "compose", "exec", "-T", "postgres", "psql", "-X", "-q",
            "-v", "ON_ERROR_STOP=1",
            "-P", "pager=off", "-U", "nexacart_user", "-d", database]
    if mode == "raw":
        args += ["-A", "-t"]
    elif mode == "csv":
        args += ["--csv"]
    return command(args, SETTINGS + statement)


def public_snapshot(database):
    dump = command(["docker", "compose", "exec", "-T", "postgres", "pg_dump",
                    "-U", "nexacart_user", "-d", database,
                    "--schema=public", "--data-only"])
    # pg_dump emits a random guard token unrelated to data in newer patch releases.
    stable = "\n".join(line for line in dump.splitlines()
                       if not line.startswith(("\\restrict ", "\\unrestrict ")))
    return hashlib.sha256(stable.encode()).hexdigest()


def csv_rows(text):
    return list(csv.DictReader(io.StringIO(text)))


def check_seed_reports(reports):
    history, products, categories, low_stock, payments = map(csv_rows, reports)
    require([r["order_id"] for r in history] == ["7", "1"],
            "Customer history differs from the Portfolio 1 seed; inspect the data")
    require([r["product_lines"] for r in history] == ["4", "2"],
            "Customer history must contain one row per order with the right item counts")
    require(len(products) == 6 and sum(int(r["units_sold"]) for r in products) == 7,
            "Fulfilled product sales differ from the seed's six products/seven units")
    for rows in (products, categories):
        require(sum(Decimal(r["merchandise_value"]) for r in rows) == Decimal("185000"),
                "Fulfilled merchandise value should total 185000.00 for the original seed")
    require(len(categories) == 4 and low_stock == [],
            "Expected four selling categories and no low-stock products in the original seed")
    require(len(payments) == 8 and sum(int(r["attempts"]) for r in payments) == 9,
            "Payment attempts must not be multiplied by order items")
    require(sum(Decimal(r["successful_amount"]) for r in payments) == Decimal("696500"),
            "Only successful payments should contribute to collected amounts")
    retry = next(r for r in payments if r["order_id"] == "2")
    require(retry["attempts"] == "2" and retry["successes"] == "1",
            "Order 2 must retain its failed attempt without double-counting its payment")


def nodes(plan):
    yield plan
    for child in plan.get("Plans", []):
        yield from nodes(child)


def access_paths(plan):
    return "; ".join(dict.fromkeys(
        node["Node Type"] + " " + node.get("Relation Name", "")
        + (" via " + node["Index Name"] if "Index Name" in node else "")
        for node in nodes(plan) if "Scan" in node["Node Type"]))


def metrics(document):
    plan = document["Plan"]
    # Root buffer counts include descendants. Summing the tree would double-count.
    return {
        "planning_ms": document["Planning Time"],
        "execution_ms": document["Execution Time"],
        "shared_hit_blocks": plan.get("Shared Hit Blocks", 0),
        "shared_read_blocks": plan.get("Shared Read Blocks", 0),
        "temp_read_blocks": plan.get("Temp Read Blocks", 0),
        "temp_written_blocks": plan.get("Temp Written Blocks", 0),
        "access_paths": access_paths(plan),
    }


def plan_text(plan, depth=0):
    indent = "  " * depth
    title = plan["Node Type"] + " " + plan.get("Relation Name", "")
    if "Index Name" in plan:
        title += " using " + plan["Index Name"]
    lines = [f"{indent}{title.strip()}: estimated rows={plan['Plan Rows']}, "
             f"actual rows={plan['Actual Rows']}, loops={plan['Actual Loops']}"]
    for key in ("Index Cond", "Filter", "Rows Removed by Filter", "Sort Key",
                "Sort Method", "Heap Fetches", "Shared Hit Blocks", "Shared Read Blocks"):
        if key in plan:
            lines.append(f"{indent}  {key}: {plan[key]}")
    for child in plan.get("Plans", []):
        lines.extend(plan_text(child, depth + 1))
    return lines


def index_catalog(database):
    return json.loads(psql(database, """
        SELECT COALESCE(json_agg(x ORDER BY indexname), '[]'::json)
        FROM (SELECT indexname, indexdef,
                     pg_relation_size(quote_ident(schemaname) || '.' || quote_ident(indexname)) AS bytes
              FROM pg_indexes WHERE schemaname = 'p2_benchmark' AND tablename = 'orders') x;
    """, "raw"))


def run(database, output):
    before_public = public_snapshot(database)
    output.mkdir(parents=True, exist_ok=False)
    (output / "reports").mkdir()
    (output / "query-results").mkdir()
    print(f"Evidence directory: {output.relative_to(ROOT)}", flush=True)

    report_csv = []
    report_text = []
    for file in sorted((SQL / "reports").glob("*.sql")):
        statement = file.read_text()
        result = psql(database, statement, "csv")
        report_csv.append(result)
        (output / "reports" / (file.stem + ".csv")).write_text(result)
        report_text += [file.stem, psql(database, statement)]
    check_seed_reports(report_csv)
    report_text += ["PASS: seed report totals, row counts, failed payment retry, empty low-stock result."]
    (output / "01-business-reports.txt").write_text("\n".join(report_text) + "\n")
    print("PASS: five business reports checked against the Portfolio 1 seed.", flush=True)

    exists = psql(database, "SELECT COUNT(*) FROM pg_namespace WHERE nspname = 'p2_benchmark';", "raw")
    if exists.strip() == "0":
        print("Creating 200,000 benchmark orders and 600,000 items...", flush=True)
        setup = psql(database, (SQL / "01-create-benchmark.sql").read_text())
    else:
        setup = "Reusing existing p2_benchmark; no data was replaced.\n"
    setup += psql(database, (SQL / "04-check-benchmark.sql").read_text())
    (output / "02-dataset-validation.txt").write_text(setup)
    print("PASS: benchmark row counts, relationships and order totals.", flush=True)

    environment = json.loads(psql(database, """
        SELECT json_build_object(
            'version', version(), 'database', current_database(),
            'max_parallel_workers_per_gather', current_setting('max_parallel_workers_per_gather'),
            'jit', current_setting('jit'), 'work_mem', current_setting('work_mem'),
            'shared_buffers', current_setting('shared_buffers'),
            'random_page_cost', current_setting('random_page_cost'),
            'effective_cache_size', current_setting('effective_cache_size'),
            'enable_seqscan', current_setting('enable_seqscan'),
            'enable_indexscan', current_setting('enable_indexscan'),
            'enable_indexonlyscan', current_setting('enable_indexonlyscan'),
            'enable_bitmapscan', current_setting('enable_bitmapscan'));
    """, "raw"))
    environment.update({"started_utc": datetime.now(timezone.utc).isoformat(),
                        "warmups_per_query_phase": 1, "measured_runs_per_query_phase": 5})
    queries = sorted((SQL / "benchmark").glob("*.sql"))
    baseline_results = {}
    records = []
    plan_sections = []
    for phase, index_file in (("before", "02-baseline-indexes.sql"),
                              ("after", "03-add-indexes.sql")):
        psql(database, (SQL / index_file).read_text())
        indexes = index_catalog(database)
        environment[phase + "_order_indexes"] = indexes
        if phase == "before":
            require(len(indexes) == 1 and "UNIQUE INDEX" in indexes[0]["indexdef"],
                    "Baseline orders must have only their copied primary-key index")
        else:
            require(len(indexes) == 3 and set(INDEX_NAMES).issubset(
                {index["indexname"] for index in indexes}), "Experimental indexes are missing")
        for file in queries:
            name = file.stem
            statement = file.read_text()
            results = psql(database, statement, "csv")
            (output / "query-results" / f"{phase}-{name}.csv").write_text(results)
            if phase == "before":
                baseline_results[name] = results
                require(len(csv_rows(results)) > 0, f"Empty benchmark query: {name}")
            else:
                require(results == baseline_results[name], f"Query results changed after indexing: {name}")
            for sample in range(6):
                document = json.loads(psql(database,
                    "EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON)\n" + statement, "raw"))[0]
                record = {"phase": phase, "query": name, "sample": sample,
                          "warmup": sample == 0, **metrics(document), "explain": document}
                records.append(record)
                if sample == 3:
                    plan_sections += [f"{phase.upper()} / {name} / measured run 3",
                                      f"Execution: {record['execution_ms']:.3f} ms; "
                                      f"Planning: {record['planning_ms']:.3f} ms",
                                      *plan_text(document["Plan"]), ""]
            times = [r["execution_ms"] for r in records
                     if r["phase"] == phase and r["query"] == name and not r["warmup"]]
            print(f"{phase:6} {name}: median {statistics.median(times):.3f} ms", flush=True)

    require(public_snapshot(database) == before_public,
            "Public data/sequence snapshot changed during the run; investigate concurrent writes")
    environment["public_data_and_sequences_unchanged"] = True
    environment["identical_before_after_results"] = True
    environment["public_snapshot_sha256"] = before_public
    (output / "environment.json").write_text(json.dumps(environment, indent=2) + "\n")
    (output / "explain-plans.json").write_text(json.dumps(records, indent=2) + "\n")
    (output / "03-plan-comparison.txt").write_text("\n".join(plan_sections) + "\n")
    with (output / "measurements.csv").open("w", newline="") as stream:
        fields = [key for key in records[0] if key != "explain"]
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(records)

    summary = ["# Measured Benchmark Results", "", f"Run: {environment['started_utc']}", "",
               "One warm-up and five measured executions per query per phase. Times below",
               "are PostgreSQL execution times; Docker startup, connection and planning time",
               "are excluded. All samples and complete plans are retained alongside this file.", "",
               "| Query | Before median ms | After median ms | Before / after |",
               "| --- | ---: | ---: | ---: |"]
    for file in queries:
        phases = [[r for r in records if r["query"] == file.stem
                   and r["phase"] == phase and not r["warmup"]] for phase in ("before", "after")]
        medians = [statistics.median(r["execution_ms"] for r in group) for group in phases]
        summary.append(f"| {file.stem} | {medians[0]:.3f} | {medians[1]:.3f} | "
                       f"{medians[0] / medians[1]:.2f}x |")
    for file in queries:
        summary += ["", "## " + file.stem, ""]
        for phase in ("before", "after"):
            group = [r for r in records if r["query"] == file.stem
                     and r["phase"] == phase and not r["warmup"]]
            summary += [f"- {phase.title()} times (ms): " + ", ".join(
                f"{r['execution_ms']:.3f}" for r in group) + ".",
                f"- {phase.title()} median root buffer hits: "
                f"{statistics.median(r['shared_hit_blocks'] for r in group):g}; reads: "
                f"{statistics.median(r['shared_read_blocks'] for r in group):g}.",
                f"- {phase.title()} run 3 access paths: {group[2]['access_paths']}."]
    summary += ["", "## Index Storage", ""]
    for index in environment["after_order_indexes"]:
        if index["indexname"] in INDEX_NAMES:
            summary.append(f"- `{index['indexname']}`: {index['bytes']:,} bytes.")
    summary += ["", "## Checks", "", "- PASS: business reports match the original seed.",
                "- PASS: benchmark counts, order totals and address ownership.",
                "- PASS: identical ordered results before and after indexing for every benchmark query.",
                "- PASS: existing public data and sequence state unchanged.",
                "", "Index creation is outside the measured queries. No public indexes were changed.",
                "Run without other database activity; these are warm-cache local measurements,",
                "not a production capacity test or a guarantee of speedup."]
    (output / "04-benchmark-summary.md").write_text("\n".join(summary) + "\n")
    print("PASS: identical query results; public data and sequences unchanged.", flush=True)
    print(f"Complete. Read {output.relative_to(ROOT)}/04-benchmark-summary.md", flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", default="nexacart_portfolio1")
    parser.add_argument("--output", type=Path, help="New evidence directory; must not already exist")
    args = parser.parse_args()
    stamp = datetime.now(timezone.utc).strftime("run-%Y%m%dT%H%M%S%fZ")
    output = args.output.resolve() if args.output else PORTFOLIO / "evidence" / stamp
    try:
        require(output.is_relative_to(ROOT), "Evidence output must be inside this repository")
        run(args.database, output)
    except (RuntimeError, subprocess.TimeoutExpired, OSError, ValueError) as error:
        print(f"FAILED: {error}", file=sys.stderr)
        print("Do not treat a partial evidence directory as a completed run.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
