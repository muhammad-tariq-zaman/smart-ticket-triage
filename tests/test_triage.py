"""Tests for smart-ticket-triage. No third-party dependencies needed.
Run:  python3 -m unittest discover -s tests -t . -v
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from smart_ticket_triage import classify, priority, sla_due, triage_csv


class TestTriage(unittest.TestCase):
    def test_classify_account(self):
        self.assertEqual(classify("user locked out, password reset needed"), "account")

    def test_classify_connectivity(self):
        self.assertEqual(classify("office wifi keeps dropping, dns fails"), "connectivity")

    def test_classify_device(self):
        self.assertEqual(classify("laptop battery swollen, screen flickers"), "device")

    def test_classify_general_fallback(self):
        self.assertEqual(classify("please help with something vague"), "general")

    def test_priority_matrix(self):
        self.assertEqual(priority("high", "high"), "P1")
        self.assertEqual(priority("high", "low"), "P2")
        self.assertEqual(priority("medium", "medium"), "P3")
        self.assertEqual(priority("low", "low"), "P4")

    def test_priority_rejects_bad_input(self):
        with self.assertRaises(ValueError):
            priority("critical", "high")

    def test_sla_due_p1_is_4_hours(self):
        self.assertEqual(sla_due("2026-10-25 09:00", "P1"), "2026-10-25T13:00")

    def test_triage_csv_sorts_p1_first_and_counts(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            src = Path(d) / "in.csv"
            src.write_text(
                "id,title,description,impact,urgency,created_at\n"
                "T1,Printer jam,printer jammed on floor 2,low,low,2026-10-25 09:00\n"
                "T2,WiFi down,wifi down for whole floor,high,high,2026-10-25 09:00\n"
            )
            out = Path(d) / "out.csv"
            summary = triage_csv(str(src), str(out))
            rows = out.read_text().splitlines()
            self.assertIn("T2", rows[1])
            self.assertIn("P1", rows[1])
            self.assertEqual(summary["total"], 2)
            self.assertEqual(summary["by_prio"]["P1"], 1)


if __name__ == "__main__":
    unittest.main()
