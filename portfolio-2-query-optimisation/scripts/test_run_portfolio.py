"""Regression checks for result validation and EXPLAIN buffer accounting."""

import csv
import io
import unittest

from run_portfolio import PORTFOLIO, check_seed_reports, metrics


class EvidenceChecks(unittest.TestCase):
    def setUp(self):
        folder = PORTFOLIO / "evidence" / "run-20261020T170936455423Z" / "reports"
        self.reports = [path.read_text() for path in sorted(folder.glob("*.csv"))]
        self.assertEqual(len(self.reports), 5)

    def test_recorded_seed_results_are_valid(self):
        check_seed_reports(self.reports)

    def test_counting_failed_payment_as_collected_is_rejected(self):
        rows = list(csv.DictReader(io.StringIO(self.reports[4])))
        retry = next(row for row in rows if row["order_id"] == "2")
        retry["successful_amount"] = "157000.00"
        stream = io.StringIO()
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
        self.reports[4] = stream.getvalue()
        with self.assertRaisesRegex(RuntimeError, "Only successful payments"):
            check_seed_reports(self.reports)

    def test_hiding_valid_sales_rows_is_rejected(self):
        self.reports[1] = self.reports[1].splitlines()[0] + "\n"
        with self.assertRaisesRegex(RuntimeError, "six products/seven units"):
            check_seed_reports(self.reports)

    def test_empty_low_stock_is_not_treated_as_failure(self):
        self.assertEqual(len(self.reports[3].strip().splitlines()), 1)
        check_seed_reports(self.reports)

    def test_parent_buffers_are_not_added_to_child_buffers(self):
        document = {
            "Planning Time": 0.3, "Execution Time": 1.0,
            "Plan": {
                "Node Type": "Aggregate", "Shared Hit Blocks": 8,
                "Shared Read Blocks": 2,
                "Plans": [{"Node Type": "Seq Scan", "Relation Name": "orders",
                           "Shared Hit Blocks": 8, "Shared Read Blocks": 2}],
            },
        }
        result = metrics(document)
        self.assertEqual(result["shared_hit_blocks"], 8)
        self.assertEqual(result["shared_read_blocks"], 2)
        self.assertEqual(result["access_paths"], "Seq Scan orders")


if __name__ == "__main__":
    unittest.main()
