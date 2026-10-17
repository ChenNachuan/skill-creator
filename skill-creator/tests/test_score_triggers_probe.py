"""Tests for the live trigger probe in scripts/score_triggers.py.

`run_trigger_query` must score a real skill invocation as a trigger. It
currently writes a stand-in into a tempfile that claude cannot discover,
then greps stdout for that stand-in's stem — so live mode is essentially
always False.
"""

import json
import os
import stat
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from scripts.score_triggers import run_trigger_query  # noqa: E402


FAKE_CLAUDE_TEMPLATE = r'''#!/usr/bin/env python3
import sys
from pathlib import Path

root = Path.cwd()
snapshot = []
if root.exists():
    for p in sorted(root.rglob("*")):
        snapshot.append(str(p.relative_to(root)))
Path({snapshot_path!r}).write_text("\n".join(snapshot))
sys.stdout.write({events_json!r} + "\n")
'''


def write_fake_claude(bin_dir: Path, events: list[dict], snapshot_path: Path) -> Path:
    events_json = "\n".join(json.dumps(e) for e in events)
    script = bin_dir / "claude"
    script.write_text(
        FAKE_CLAUDE_TEMPLATE.format(
            events_json=events_json, snapshot_path=str(snapshot_path)
        )
    )
    script.chmod(script.stat().st_mode | stat.S_IEXEC)
    return script


def skill_tool_events(skill_name: str) -> list[dict]:
    return [
        {
            "type": "stream_event",
            "event": {
                "type": "content_block_start",
                "content_block": {"type": "tool_use", "name": "Skill", "id": "t1"},
            },
        },
        {
            "type": "stream_event",
            "event": {
                "type": "content_block_delta",
                "delta": {
                    "type": "input_json_delta",
                    "partial_json": '{"skill": "%s"}' % skill_name,
                },
            },
        },
        {"type": "stream_event", "event": {"type": "content_block_stop"}},
    ]


class TestRunTriggerQuery(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory(prefix="sttrig-")
        self.root = Path(self._tmp.name)
        self.bin_dir = self.root / "bin"
        self.bin_dir.mkdir()
        self._old_path = os.environ.get("PATH", "")
        os.environ["PATH"] = f"{self.bin_dir}{os.pathsep}{self._old_path}"

    def tearDown(self):
        os.environ["PATH"] = self._old_path
        self._tmp.cleanup()

    def run_probe(self, skill_name: str, events: list[dict]) -> tuple[bool, str]:
        snapshot_path = self.root / "snapshot.txt"
        write_fake_claude(self.bin_dir, events, snapshot_path)
        result = run_trigger_query(
            query="do the thing",
            description="a skill that does the thing",
            skill_name=skill_name,
        )
        snapshot = snapshot_path.read_text() if snapshot_path.exists() else ""
        return result, snapshot

    def test_real_skill_invocation_scores_true(self):
        result, _ = self.run_probe("my-skill", skill_tool_events("my-skill"))
        self.assertTrue(result, "real Skill invocation was scored as no-trigger")

    def test_wrong_skill_name_scores_false(self):
        result, _ = self.run_probe("my-skill", skill_tool_events("other-skill"))
        self.assertFalse(result)

    def test_stages_real_skill_not_tempfile_standin(self):
        _, snapshot = self.run_probe("my-skill", skill_tool_events("my-skill"))
        self.assertIn(
            ".claude/skills/my-skill/SKILL.md",
            snapshot,
            "skill under test was not staged at .claude/skills/<name>/SKILL.md",
        )
        standins = [
            line
            for line in snapshot.splitlines()
            if line.endswith("-trigger.md") or "trigger.md" in line
        ]
        self.assertEqual(
            standins,
            [],
            "tempfile stand-in should not be planted: %s" % standins,
        )


if __name__ == "__main__":
    unittest.main()
