"""Tests for loading trigger eval sets in either documented shape.

`references/schemas.md` documents a tiered triggers.json
({skill_name, positive[], near_miss[], holdout[]}), which is what
score_triggers.py and run_skill_evals.py read. run_eval.py and run_loop.py
historically required a flat [{query, should_trigger}] list and crashed on
the tiered shape. One filename, two shapes — both must load.
"""

import json
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from scripts.utils import load_eval_cases  # noqa: E402


TIERED = {
    "skill_name": "example-skill",
    "positive": [
        {
            "id": "pos-01",
            "query": "Create a skill that formats CSV files",
            "should_trigger": True,
            "rationale": "core capability",
        }
    ],
    "near_miss": [
        {
            "id": "nm-01",
            "query": "Help me write a Python script to parse JSON",
            "should_trigger": False,
            "rationale": "programming task",
        }
    ],
    "holdout": [
        {
            "id": "ho-01",
            "query": "Build a reusable workflow for data processing",
            "should_trigger": True,
            "rationale": "holdout",
        }
    ],
}

FLAT = [
    {"query": "Create a skill that formats CSV files", "should_trigger": True},
    {"query": "Help me write a Python script to parse JSON", "should_trigger": False},
]


class TestLoadEvalCases(unittest.TestCase):
    def write_tmp(self, data) -> Path:
        tmp = tempfile.NamedTemporaryFile(
            "w", suffix=".json", delete=False, encoding="utf-8"
        )
        json.dump(data, tmp)
        tmp.close()
        self.addCleanup(Path(tmp.name).unlink)
        return Path(tmp.name)

    def test_tiered_shape_loads_to_flat_case_list(self):
        cases = load_eval_cases(self.write_tmp(TIERED))
        self.assertEqual(len(cases), 3)
        queries = {c["query"] for c in cases}
        self.assertEqual(
            queries,
            {
                "Create a skill that formats CSV files",
                "Help me write a Python script to parse JSON",
                "Build a reusable workflow for data processing",
            },
        )

    def test_tiered_shape_preserves_should_trigger(self):
        cases = load_eval_cases(self.write_tmp(TIERED))
        by_query = {c["query"]: c["should_trigger"] for c in cases}
        self.assertTrue(by_query["Create a skill that formats CSV files"])
        self.assertFalse(by_query["Help me write a Python script to parse JSON"])
        self.assertTrue(by_query["Build a reusable workflow for data processing"])

    def test_flat_shape_still_loads(self):
        cases = load_eval_cases(self.write_tmp(FLAT))
        self.assertEqual(len(cases), 2)
        self.assertTrue(all("query" in c and "should_trigger" in c for c in cases))

    def test_tiered_holdout_is_flagged(self):
        cases = load_eval_cases(self.write_tmp(TIERED))
        holdout = [c for c in cases if c.get("is_holdout")]
        self.assertEqual(len(holdout), 1)
        self.assertEqual(holdout[0]["id"], "ho-01")

    def test_missing_id_in_tiered_raises(self):
        broken = {
            "positive": [{"query": "q", "should_trigger": True}],
        }
        with self.assertRaises(ValueError):
            load_eval_cases(self.write_tmp(broken))


if __name__ == "__main__":
    unittest.main()
