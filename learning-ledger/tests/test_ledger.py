import csv
import contextlib
import io
import json
import sys
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import ledger


FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "study.synthetic.json"


class LedgerTests(unittest.TestCase):
    def setUp(self):
        self.data = ledger.read_json(FIXTURE)
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_fixture_valid_and_marked_synthetic(self):
        self.assertEqual([], ledger.validate_ledger(self.data))
        self.assertEqual("synthetic_only", self.data["fixture_status"])

    def test_fixed_pool_checks_ids_hashes_and_fixed_k(self):
        broken = deepcopy(self.data)
        broken["modes"]["fixed_pool"]["arms"][1]["candidates"][0]["text"] += " changed"
        broken["modes"]["fixed_pool"]["arms"][0]["candidates"][0]["selected"] = False
        errors = " ".join(ledger.validate_ledger(broken))
        self.assertIn("content hash mismatch", errors)
        self.assertIn("selects 1", errors)

    def test_fixed_pool_rejects_different_candidate_ids_and_journal_tier_reward(self):
        broken = deepcopy(self.data)
        broken["modes"]["fixed_pool"]["arms"][1]["candidates"][0]["candidate_id"] = "OTHER-ID"
        broken["modes"]["fixed_pool"]["external_outcome_source"] = "source_journal_tier"
        errors = " ".join(ledger.validate_ledger(broken))
        self.assertIn("candidate IDs differ", errors)
        self.assertIn("cannot be the reward proof", errors)

    def test_iterative_search_enforces_budget_ceilings(self):
        broken = deepcopy(self.data)
        broken["modes"]["iterative_search"]["arms"][0]["revisions"][0]["tokens"] = 13000
        errors = " ".join(ledger.validate_ledger(broken))
        self.assertIn("exceeds token ceiling", errors)

    def test_blind_export_hides_condition_and_taste_label_in_review_file(self):
        review, key = self.root / "review.csv", self.root / "private-key.csv"
        ledger.export_blind(self.data, review, key)
        review_text = review.read_text()
        self.assertIn("candidate_text", review_text)
        self.assertNotIn("taste_label", review_text)
        self.assertNotIn("taste_guided", review_text)
        self.assertIn("taste_label", key.read_text())
        with review.open(newline="", encoding="utf-8") as f:
            self.assertEqual(4, len(list(csv.DictReader(f))))

    def make_ratings(self, path, *, duplicate=False, missing=False, out_of_range=False):
        review, key = self.root / "review.csv", self.root / "key.csv"
        ledger.export_blind(self.data, review, key)
        with review.open(newline="", encoding="utf-8") as f:
            ids = [r["blind_id"] for r in csv.DictReader(f)]
        rows = []
        for bid in ids:
            for dim in ledger.DIMENSIONS:
                rows.append({"blind_id": bid, "reviewer_code": "SYN-R1", "dimension": dim,
                             "rating": "9" if out_of_range else "5"})
        if missing:
            rows.pop()
        if duplicate:
            rows.append(dict(rows[0]))
        with path.open("w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=["blind_id", "reviewer_code", "dimension", "rating"])
            writer.writeheader()
            writer.writerows(rows)
        return review

    def test_ratings_require_complete_nonduplicate_bounded_values(self):
        for options, expected in [({"missing": True}, "missing external ratings"),
                                  ({"duplicate": True}, "duplicate rating"),
                                  ({"out_of_range": True}, "integer from 1 to 7")]:
            ratings = self.root / "ratings.csv"
            review = self.make_ratings(ratings, **options)
            with self.assertRaisesRegex(ledger.LedgerError, expected):
                ledger.import_ratings(self.data, review, ratings, self.root / "out.json")

    def test_import_and_summary_are_descriptive_by_dimension(self):
        ratings = self.root / "ratings.csv"
        review = self.make_ratings(ratings)
        out = self.root / "imported.json"
        ledger.import_ratings(self.data, review, ratings, out)
        imported = json.loads(out.read_text())
        rows = ledger.summarize(imported, self.root / "key.csv")
        self.assertEqual(9, len(rows))
        self.assertEqual({"taste_guided", "baseline", "random"}, {r["condition"] for r in rows})
        self.assertEqual({"novelty", "value", "feasibility"}, {r["dimension"] for r in rows})
        self.assertTrue(all("descriptive only" in r["interpretation"] for r in rows))
        self.assertEqual(18, sum(r["n_ratings"] for r in rows))
        self.assertTrue(all(r["n_items"] == 2 for r in rows))
        self.assertTrue(all(r["pooled_rating_mean"] == r["mean_rating"] for r in rows))

    def test_summary_weights_items_equally_when_rater_counts_differ(self):
        review, key = self.root / "review.csv", self.root / "key.csv"
        ledger.export_blind(self.data, review, key)
        ratings_path = self.root / "unequal-ratings.csv"
        with ratings_path.open("w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=["blind_id", "reviewer_code", "dimension", "rating"])
            writer.writeheader()
            for bid in ("B0001", "B0002", "B0003", "B0004"):
                values = ["1", "1", "1"] if bid == "B0001" else (["7"] if bid == "B0004" else ["4"])
                for dim in ledger.DIMENSIONS:
                    for i, value in enumerate(values, 1):
                        writer.writerow({"blind_id": bid, "reviewer_code": f"SYN-R{i}", "dimension": dim, "rating": value})
        out = self.root / "rated.json"
        ledger.import_ratings(self.data, review, ratings_path, out)
        imported = json.loads(out.read_text())
        selected_row = next(r for r in ledger.summarize(imported, key)
                            if r["arm_id"] == "FP-T" and r["dimension"] == "novelty")
        self.assertEqual(2, selected_row["n_items"])
        self.assertEqual(4, selected_row["n_ratings"])
        self.assertEqual(4, selected_row["mean_rating"])
        self.assertEqual(2.5, selected_row["pooled_rating_mean"])
        unlinked = next(r for r in ledger.summarize(imported) if r["dimension"] == "novelty")
        self.assertEqual(4, unlinked["n_items"])
        self.assertEqual(6, unlinked["n_ratings"])
        self.assertEqual(4, unlinked["mean_rating"])
        self.assertEqual(3.0, unlinked["pooled_rating_mean"])

    def test_validate_reports_actual_status_without_approval_claim(self):
        governed = deepcopy(self.data)
        governed["fixture_status"] = "governed_human_study"
        governed["governance"] = {"status": "approved_or_determined", "protocol_reference": "synthetic-test-reference"}
        path = self.root / "governed.json"
        path.write_text(json.dumps(governed))
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            rc = ledger.main(["validate", str(path)])
        self.assertEqual(0, rc)
        self.assertIn("governed_human_study", output.getvalue())
        self.assertIn("does not prove study approval", output.getvalue())

    def test_transfer_import_keeps_unaided_condition_and_history(self):
        responses = self.root / "transfer.csv"
        responses.write_text("task_id,subject_code,response_text,timestamp\nUT-01,SYN-99,Invented response,2026-10-17T00:00:00Z\n")
        out = self.root / "transfer.json"
        ledger.import_transfer(self.data, responses, out)
        saved = json.loads(out.read_text())
        self.assertEqual("unaided", saved["modes"]["unaided_transfer"]["responses"][-1]["condition"])
        self.assertEqual(len(self.data["events"]) + 1, len(saved["events"]))
        self.assertEqual(2, len(self.data["events"]))

    def test_candidate_taste_is_ordinal_label_not_probability(self):
        broken = deepcopy(self.data)
        broken["modes"]["fixed_pool"]["arms"][0]["candidates"][0]["taste_label"] = 0.9
        self.assertTrue(any("taste_label must be one of" in e for e in ledger.validate_ledger(broken)))

    def test_unique_arm_ids_selected_boolean_and_task_ids(self):
        broken = deepcopy(self.data)
        broken["modes"]["fixed_pool"]["arms"][1]["arm_id"] = broken["modes"]["fixed_pool"]["arms"][0]["arm_id"]
        broken["modes"]["fixed_pool"]["arms"][0]["candidates"][0]["selected"] = "true"
        broken["modes"]["unaided_transfer"]["tasks"][1]["task_id"] = "UT-01"
        errors = " ".join(ledger.validate_ledger(broken))
        self.assertIn("arm_id must be unique", errors)
        self.assertIn("selected must be boolean", errors)
        self.assertIn("duplicate unaided transfer task_id", errors)

    def test_revision_parent_order_hash_and_invalid_budget_types(self):
        broken = deepcopy(self.data)
        first, second = broken["modes"]["iterative_search"]["arms"][0]["revisions"]
        second["parent_revision_id"] = "missing"
        second["text"] += " changed"
        broken["modes"]["iterative_search"]["budget_ceiling"]["tokens"] = "12000"
        errors = " ".join(ledger.validate_ledger(broken))
        self.assertIn("budget_ceiling requires positive integer", errors)
        self.assertIn("parent must refer to an earlier revision", errors)
        self.assertIn("content hash mismatch", errors)

    def test_import_binds_blind_export_to_current_pool(self):
        ratings = self.root / "ratings.csv"
        review = self.make_ratings(ratings)
        with review.open(newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        rows[0]["candidate_text"] += " altered"
        with review.open("w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=rows[0].keys())
            writer.writeheader()
            writer.writerows(rows)
        with self.assertRaisesRegex(ledger.LedgerError, "does not match this ledger"):
            ledger.import_ratings(self.data, review, ratings, self.root / "out.json")

    def test_summary_rejects_tampered_or_wrong_key_map(self):
        ratings = self.root / "ratings.csv"
        review = self.make_ratings(ratings)
        out = self.root / "imported.json"
        ledger.import_ratings(self.data, review, ratings, out)
        key_path = self.root / "key.csv"
        with key_path.open(newline="", encoding="utf-8") as f:
            key_rows = list(csv.DictReader(f))
        key_rows[0]["condition"] = "swapped"
        with key_path.open("w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=key_rows[0].keys())
            writer.writeheader()
            writer.writerows(key_rows)
        with self.assertRaisesRegex(ledger.LedgerError, "does not exactly match"):
            ledger.summarize(json.loads(out.read_text()), key_path)

    def test_cli_refuses_to_overwrite_input_ledger(self):
        with contextlib.redirect_stderr(io.StringIO()):
            rc = ledger.main(["import-transfer", str(FIXTURE), "--responses",
                              str(Path(__file__).resolve().parents[1] / "fixtures" / "transfer-responses.synthetic.csv"),
                              "--out", str(FIXTURE)])
        self.assertEqual(2, rc)


if __name__ == "__main__":
    unittest.main()
