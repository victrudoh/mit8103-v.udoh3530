#!/usr/bin/env python3
"""Run and preserve the NexaCart Portfolio 4 MongoDB document-model evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import List


ROOT = Path(__file__).resolve().parents[2]
PORTFOLIO = ROOT / "portfolio-4-nosql"
MONGODB = PORTFOLIO / "mongodb"
EVIDENCE = PORTFOLIO / "evidence"
POSTGRES_DATABASE = "nexacart_portfolio1"


class PortfolioError(RuntimeError):
    pass


def run_command(command: List[str], input_text: str = "") -> str:
    result = subprocess.run(
        command,
        cwd=ROOT,
        input=input_text,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if result.returncode:
        raise PortfolioError(result.stderr.strip() or "Command failed: {}".format(" ".join(command)))
    return result.stdout


def run_mongosh(script: Path) -> str:
    return run_command(
        ["docker", "compose", "exec", "-T", "mongo", "mongosh", "--quiet", "--file", "/dev/stdin"],
        script.read_text(encoding="utf-8"),
    )


def public_digest() -> str:
    dump = run_command([
        "docker", "compose", "exec", "-T", "postgres", "pg_dump", "-U", "nexacart_user",
        "-d", POSTGRES_DATABASE, "--schema=public", "--data-only", "--no-owner", "--no-privileges",
    ])
    stable_lines = [
        line for line in dump.splitlines()
        if not line.startswith("\\restrict ") and not line.startswith("\\unrestrict ")
    ]
    return hashlib.sha256("\n".join(stable_lines).encode("utf-8")).hexdigest()


def mongo_version() -> str:
    return run_command([
        "docker", "compose", "exec", "-T", "mongo", "mongosh", "--quiet", "--eval", "db.version()",
    ]).strip()


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

    before = public_digest()
    seed = run_mongosh(MONGODB / "01-seed-document-model.js")
    queries = run_mongosh(MONGODB / "02-query-document-model.js")
    validation = run_mongosh(MONGODB / "03-validate-document-model.js")
    explain = run_mongosh(MONGODB / "04-explain-query-plan.js")
    after = public_digest()
    if before != after:
        raise PortfolioError("PostgreSQL public data or sequence state changed during the MongoDB run")
    if "VALIDATION COMPLETE" not in validation or "FAIL:" in validation:
        raise PortfolioError("MongoDB validation did not complete successfully")
    if "EXPLAIN COMPLETE" not in explain or "FAIL:" in explain:
        raise PortfolioError("MongoDB explain checks did not complete successfully")

    write(output / "01-seed-document-model.txt", seed)
    write(output / "02-query-document-model.txt", queries)
    write(output / "03-validation.txt", validation)
    write(output / "04-explain-query-plan.txt", explain)
    write(output / "05-verification.txt", "\n".join([
        "PORTFOLIO 4 VERIFICATION",
        "PASS: MongoDB document model seeded and queried successfully.",
        "PASS: collection validators and required indexes were verified.",
        "PASS: explain() plans confirmed index use for the category-price and tag queries.",
        "PASS: PostgreSQL public data and sequence state were unchanged.",
        "PostgreSQL public state SHA-256: {}".format(after),
        "",
    ]))
    write(output / "environment.json", json.dumps({
        "mongo_version": mongo_version(),
        "image": "mongo:8.0.30-noble",
        "database": "nexacart_portfolio4",
        "recorded_at": datetime.now(timezone.utc).isoformat(),
    }, indent=2))
    print("Portfolio 4 evidence written to {}".format(output.relative_to(ROOT)))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except PortfolioError as error:
        print("Portfolio 4 failed: {}".format(error), file=sys.stderr)
        raise SystemExit(1)
