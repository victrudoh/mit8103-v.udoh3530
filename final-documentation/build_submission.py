#!/usr/bin/env python3
"""Build the MIT 8103 LMS submission package.

Produces, under the git-ignored `submission/` directory:

    Surname_Firstname_README.txt          (uploaded separately on the form)
    Surname_Firstname_StudentID.zip       (the zipped folder, below)
        Surname_Firstname_StudentID/
            Surname_Firstname_Documentation.pdf
            Surname_Firstname_Repository.zip

The name and student ID are arguments so they are not stored in the repository.
The PDF is printed by Google Chrome in headless mode; no Python packages are
required.
"""

from __future__ import annotations

import argparse
import html
import re
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HERE = ROOT / "final-documentation"
OUTPUT = ROOT / "submission"
CHROME = Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")
GITHUB_URL = "https://github.com/victrudoh/mit8103-v.udoh3530"
NAME_PATTERN = re.compile(r"^[A-Za-z]+$")
ID_PATTERN = re.compile(r"^[A-Za-z0-9]+$")

FIGURES = [
    ("portfolio-1-database-design/evidence/11-validation-summary.png",
     "P1: validation suite, 23 passes"),
    ("portfolio-2-query-optimisation/evidence/06-benchmark-summary.png",
     "P2: before/after benchmark"),
    ("portfolio-3-transactions-concurrency/evidence/04-concurrent-reservation-control.png",
     "P3: lock wait, no oversell"),
    ("portfolio-4-nosql/evidence/04-explain-query-plan.png",
     "P4: IXSCAN vs COLLSCAN"),
    ("portfolio-5-distributed-cloud/evidence/06-failover-promotion.png",
     "P5: failover, matching hash"),
]

ROWS = [
    ("1. Database design",
     "Ten-table PostgreSQL 16 schema in 3NF with PK, FK, UNIQUE, NOT NULL, DEFAULT and CHECK constraints. "
     "<code>order_items</code> resolves the orders/products many-to-many link; payments are 1:M. "
     "Realistic seed data and an ER diagram.",
     "23-case validation suite: 7 valid inserts accepted and 16 invalid ones rejected with the expected "
     "constraint and SQLSTATE."),
    ("2. Query optimisation",
     "Five business reports on the original data, plus a separate generated benchmark "
     "(10,000 customers, 200,000 orders, 600,000 items). Two targeted indexes were compared using "
     "<code>EXPLAIN (ANALYZE, BUFFERS)</code>, five measured runs each.",
     "Customer history 7.931 to 0.140 ms; daily sales 17.119 to 0.159 ms; the all-order summary was "
     "unchanged (41.2 vs 41.4 ms). The sort stayed in the history plan."),
    ("3. Transactions and concurrency",
     "Stock-reservation lab in its own schema: a committed transaction, a rollback, a "
     "<code>REPEATABLE READ</code> snapshot, and a guarded atomic <code>UPDATE</code> with a row-lock wait.",
     "Two sessions competing for the last unit ended with stock 0 and one reservation; the "
     "second waited on the lock and updated no row."),
    ("4. NoSQL",
     "MongoDB 8.0.30 document model: <code>catalogue_items</code> (category-specific attributes, bounded "
     "review snippets) and <code>customer_profiles</code>, with JSON Schema validators and indexes. "
     "PostgreSQL remains authoritative.",
     "7 catalogue documents, 2 profiles, schema rejection of an incomplete document, "
     "<code>explain()</code> showing 3 vs 7 documents examined."),
    ("5. Distributed and cloud",
     "Separate Docker lab with a PostgreSQL primary and streaming replica (replication slot, "
     "<code>pg_basebackup</code>). Sharding and cloud mapping are discussed, not implemented.",
     "Replica data hash identical to the primary; stale read while replay paused; synchronous commit "
     "held at <code>SyncRep</code>; replica promoted after a simulated primary crash."),
]

AI_DECLARATION = [
    ("AI tools used",
     "OpenAI Codex (Portfolios 1 to 4) and Cursor's AI coding assistant (Portfolio 4 revisions, Portfolio 5, "
     "and the final documentation). The Portfolio 1 schema and ER model were adapted from a supplied "
     "implementation guide."),
    ("What they were used for",
     "Schema and seed SQL, validation and benchmark scripts, Docker setup, the MongoDB model and scripts, the "
     "replication lab, evidence runners and README text. The wording of the reflection above was drafted with "
     "AI assistance from the repository's recorded results."),
    ("How the output was verified",
     "Every script was run against real PostgreSQL 16.15 and MongoDB 8.0.30 containers and its output saved. "
     "Runners check their own results and fail on a mismatch. Screenshots are my own captures of that saved "
     "output. I reviewed the work, and I remain responsible for explaining it."),
]

REFERENCES = [
    "MIT 8103 CA brief, September Cohort 2026.",
    "PostgreSQL 16 documentation: constraints, EXPLAIN, indexes, transaction isolation, explicit locking, "
    "high availability and replication, pg_basebackup.",
    "MongoDB documentation: embedded and referenced data models, schema validation, sharding, replication.",
    "Mermaid ER diagram syntax. Full source links are in each portfolio README.",
]


class BuildError(RuntimeError):
    pass


def inline(text: str) -> str:
    escaped = html.escape(text, quote=False)
    escaped = re.sub(r"`([^`]+)`", r"<code>\1</code>", escaped)
    escaped = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", escaped)
    return re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"<em>\1</em>", escaped)


def reflection_html() -> str:
    paragraphs = (HERE / "reflection.md").read_text(encoding="utf-8").strip().split("\n\n")
    return "\n".join("<p>{}</p>".format(inline(p.replace("\n", " "))) for p in paragraphs)


def document_html(full_name: str, student_id: str) -> str:
    rows = "\n".join(
        "<tr><th>{}</th><td>{}</td><td>{}</td></tr>".format(name, built, result)
        for name, built, result in ROWS
    )
    figures = "\n".join(
        '<figure><img src="{}"><figcaption>{}</figcaption></figure>'.format((ROOT / path).as_uri(), caption)
        for path, caption in FIGURES
    )
    declaration = "\n".join(
        "<p><strong>{}:</strong> {}</p>".format(label, text) for label, text in AI_DECLARATION
    )
    references = "".join("<li>{}</li>".format(html.escape(item)) for item in REFERENCES)
    return """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>MIT 8103 Portfolio Documentation</title>
<style>
@page {{ size: A4; margin: 11mm 13mm; }}
body {{ font: 9.2pt/1.32 -apple-system, "Helvetica Neue", Arial, sans-serif; color: #1a1a1a; margin: 0; }}
h1 {{ font-size: 15pt; margin: 0 0 1mm; }}
h2 {{ font-size: 10.5pt; margin: 3.2mm 0 1mm; border-bottom: 0.4pt solid #888; padding-bottom: 0.4mm; }}
p {{ margin: 0 0 1.6mm; }}
.meta {{ margin: 0 0 1mm; color: #333; }}
code {{ font: 8.4pt Menlo, monospace; background: #f1f1f1; padding: 0 1px; }}
table {{ width: 100%; border-collapse: collapse; margin-top: 1mm; }}
th, td {{ border: 0.4pt solid #999; padding: 1mm 1.4mm; vertical-align: top; text-align: left; }}
thead th {{ background: #e9eef4; }}
tbody th {{ width: 19%; background: #f7f7f7; }}
td:nth-child(2) {{ width: 44%; }}
.figs {{ display: grid; grid-template-columns: 1fr 1fr; gap: 2mm 3mm; margin-top: 1mm; }}
figure {{ margin: 0; break-inside: avoid; }}
figure img {{ width: 100%; border: 0.4pt solid #999; }}
figcaption {{ font-size: 7.4pt; color: #444; margin-top: 0.5mm; }}
ul {{ margin: 0; padding-left: 4.5mm; }}
.small {{ font-size: 8.4pt; }}
</style></head><body>
<h1>MIT 8103 Advanced Database Systems: Individual Practical Database Portfolio</h1>
<p class="meta"><strong>{name}</strong> | Student ID: {sid} | MIT, 2026/2027 First Semester CA<br>
GitHub repository (private): <strong>{url}</strong></p>

<h2>Selected case study: NexaCart</h2>
<p>NexaCart is a simulated e-commerce platform. <strong>Users:</strong> customers, who browse, order, pay, review
and track deliveries, and administrators, who manage products, categories, stock and fulfilment.
<strong>Major data:</strong> customers, addresses, categories, products, inventory, orders, order items, payments,
shipments and reviews. <strong>Key operations:</strong> register customers, manage the catalogue, place orders,
update stock, process payments, view order history and track delivery. All five portfolios use this same case
study and the same Portfolio 1 data.</p>

<h2>The five portfolio activities</h2>
<table><thead><tr><th>Portfolio</th><th>What was built</th><th>Result evidenced</th></tr></thead>
<tbody>
{rows}
</tbody></table>

<h2>Selected evidence (one screenshot per portfolio)</h2>
<p class="small">All screenshots are in each portfolio's <code>evidence/</code> folder, next to the saved text output they capture.</p>
<div class="figs">
{figures}
</div>

<h2>Individual technical reflection</h2>
{reflection}

<h2>AI use declaration</h2>
{declaration}

<h2>References</h2>
<ul class="small">{references}</ul>
</body></html>
""".format(
        name=html.escape(full_name), sid=html.escape(student_id), url=GITHUB_URL, rows=rows,
        figures=figures, reflection=reflection_html(), declaration=declaration, references=references,
    )


def render_pdf(source: Path, target: Path) -> None:
    if not CHROME.exists():
        raise BuildError("Google Chrome was not found at {}".format(CHROME))
    result = subprocess.run(
        [str(CHROME), "--headless", "--disable-gpu", "--no-pdf-header-footer",
         "--allow-file-access-from-files", "--print-to-pdf={}".format(target), source.as_uri()],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=False, timeout=120,
    )
    if result.returncode or not target.exists():
        raise BuildError("Chrome could not print the PDF: {}".format(result.stderr.strip()))


def page_count(pdf: Path) -> int:
    return len(re.findall(rb"/Type\s*/Page(?![s\w])", pdf.read_bytes()))


def readme_text(full_name: str, student_id: str, folder: str, surname: str, firstname: str) -> str:
    return """MIT 8103 ADVANCED DATABASE SYSTEMS - CA SEPTEMBER COHORT 2026
Individual Practical Database Portfolio

Student: {name}
Student ID: {sid}
GitHub repository (private; access must be granted to the assessor): {url}

SELECTED CASE STUDY
NexaCart, a simulated e-commerce platform (customers, products, inventory, orders, payments,
shipments, reviews). All five portfolio activities use this one case study.

CONTENTS OF THE SUBMITTED FOLDER ({folder})
- {surname}_{firstname}_Documentation.pdf : the 3-page summary with selected evidence, the individual
  technical reflection, the AI use declaration and references.
- {surname}_{firstname}_Repository.zip : a snapshot of the GitHub repository (tracked files only),
  included in case the link is not accessible. It contains all SQL scripts, MongoDB scripts, Docker
  Compose files, evidence runners, saved outputs and screenshots.

REPOSITORY STRUCTURE
portfolio-1-database-design/        ER diagram, PostgreSQL schema, seed data, 23-case constraint suite
portfolio-2-query-optimisation/     reports, benchmark dataset, indexes, execution plans, timings
portfolio-3-transactions-concurrency/  commit, rollback, isolation, locking control
portfolio-4-nosql/                  MongoDB document model, queries, validators, explain() evidence
portfolio-5-distributed-cloud/      PostgreSQL primary/replica lab, failover evidence
final-documentation/                reflection and the script that builds this package

HOW TO REPRODUCE
Requires Docker with Compose and Python 3.9 or newer (standard library only). Each portfolio folder has
its own README with exact commands. In short, from the repository root:
  docker compose up -d --wait        (PostgreSQL for portfolios 1-3, MongoDB for portfolio 4)
  python3 portfolio-<n>-.../scripts/run_portfolio.py
Portfolio 5 builds its own isolated lab:  python3 portfolio-5-distributed-cloud/scripts/run_portfolio.py

AI USE DECLARATION (summary; full wording in the documentation PDF and each portfolio README)
Tools: OpenAI Codex and Cursor's AI coding assistant. Used for scripts, Docker setup, evidence runners
and documentation text, and to draft the wording of the reflection. All outputs were run against real
PostgreSQL and MongoDB containers and saved; screenshots are my own captures. I remain responsible for
reviewing and explaining the work.
""".format(name=full_name, sid=student_id, url=GITHUB_URL, folder=folder, surname=surname, firstname=firstname)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--surname", required=True)
    parser.add_argument("--firstname", required=True)
    parser.add_argument("--student-id", required=True)
    parser.add_argument("--ref", default="HEAD", help="Git ref to archive for the repository snapshot")
    args = parser.parse_args()

    for label, value, pattern in (
        ("surname", args.surname, NAME_PATTERN), ("first name", args.firstname, NAME_PATTERN),
        ("student ID", args.student_id, ID_PATTERN),
    ):
        if not pattern.match(value):
            raise BuildError("The {} must contain only letters/digits (no spaces or underscores): {!r}".format(label, value))

    folder = "{}_{}_{}".format(args.surname, args.firstname, args.student_id)
    prefix = "{}_{}".format(args.surname, args.firstname)
    if OUTPUT.exists():
        shutil.rmtree(OUTPUT)
    package = OUTPUT / folder
    package.mkdir(parents=True)

    page = OUTPUT / "documentation.html"
    page.write_text(document_html("{} {}".format(args.firstname, args.surname), args.student_id), encoding="utf-8")
    pdf = package / "{}_Documentation.pdf".format(prefix)
    render_pdf(page, pdf)
    pages = page_count(pdf)
    if not 2 <= pages <= 3:
        raise BuildError("The brief asks for 2-3 pages; the PDF has {}".format(pages))
    page.unlink()

    snapshot = package / "{}_Repository.zip".format(prefix)
    subprocess.run(
        ["git", "archive", "--format=zip", "--prefix=nexacart-portfolio/", "-o", str(snapshot), args.ref],
        cwd=ROOT, check=True,
    )
    shutil.make_archive(str(OUTPUT / folder), "zip", root_dir=OUTPUT, base_dir=folder)
    (OUTPUT / "{}_README.txt".format(prefix)).write_text(
        readme_text("{} {}".format(args.firstname, args.surname), args.student_id, folder, args.surname, args.firstname),
        encoding="utf-8",
    )

    print("Built {} page PDF and package in {}:".format(pages, OUTPUT.relative_to(ROOT)))
    for path in sorted(OUTPUT.iterdir()):
        print("  {} ({:.1f} MB)".format(path.name, path.stat().st_size / 1e6))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (BuildError, subprocess.CalledProcessError) as error:
        print("Build failed: {}".format(error), file=sys.stderr)
        raise SystemExit(1)
