"""Tests for trigger-probe detection in scripts/run_eval.py.

The probe must score a real skill invocation as a trigger. It currently
plants a uuid-suffixed slash command and matches that uuid, so a genuine
`Skill` call naming the real skill scores False.
"""

import os
import stat
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from scripts.run_eval import detect_skill_trigger, run_single_query  # noqa: E402


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


def write_fake_claude(
    bin_dir: Path, events: list[dict], snapshot_path: Path
) -> Path:
    """Write a fake `claude` that snapshots its cwd and prints events."""
    import json

    events_json = "\n".join(json.dumps(e) for e in events)
    script = bin_dir / "claude"
    script.write_text(
        FAKE_CLAUDE_TEMPLATE.format(
            events_json=events_json,
            snapshot_path=str(snapshot_path),
        )
    )
    script.chmod(script.stat().st_mode | stat.S_IEXEC)
    return script


def skill_tool_events(skill_name: str) -> list[dict]:
    """Stream events for a Skill tool_use naming skill_name."""
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


def bash_then_skill_events(skill_name: str) -> list[dict]:
    """Stream events: Bash tool first, then Skill tool_use naming skill_name."""
    return [
        {
            "type": "stream_event",
            "event": {
                "type": "content_block_start",
                "content_block": {"type": "tool_use", "name": "Bash", "id": "t0"},
            },
        },
        {
            "type": "stream_event",
            "event": {
                "type": "content_block_delta",
                "delta": {"type": "input_json_delta", "partial_json": '{"command": "ls"}'},
            },
        },
        {"type": "stream_event", "event": {"type": "content_block_stop"}},
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


class FakeClaudeCase(unittest.TestCase):
    """Base: temp project + fake claude on PATH for run_single_query."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory(prefix="trigtest-")
        self.root = Path(self._tmp.name)
        self.bin_dir = self.root / "bin"
        self.bin_dir.mkdir()
        self.project_root = self.root / "project"
        (self.project_root / ".claude").mkdir(parents=True)
        self._old_path = os.environ.get("PATH", "")
        os.environ["PATH"] = f"{self.bin_dir}{os.pathsep}{self._old_path}"

    def tearDown(self):
        os.environ["PATH"] = self._old_path
        self._tmp.cleanup()

    def run_probe(self, skill_name: str, events: list[dict]) -> tuple[bool, str]:
        snapshot_path = self.root / "snapshot.txt"
        write_fake_claude(self.bin_dir, events, snapshot_path)
        result = run_single_query(
            query="do the thing",
            skill_name=skill_name,
            skill_description="a skill that does the thing",
            timeout=10,
            project_root=str(self.project_root),
        )
        snapshot = snapshot_path.read_text() if snapshot_path.exists() else ""
        return result, snapshot


class TestRunSingleQuery(FakeClaudeCase):
    def test_real_skill_invocation_scores_true(self):
        """A Skill call naming the real skill must count as triggered."""
        result, _ = self.run_probe("my-skill", skill_tool_events("my-skill"))
        self.assertTrue(result, "real Skill invocation was scored as no-trigger")

    def test_unrelated_tool_before_skill_still_detects(self):
        """Bash before Skill must not abort the search."""
        result, _ = self.run_probe("my-skill", bash_then_skill_events("my-skill"))
        self.assertTrue(result, "Skill after an unrelated tool was scored as no-trigger")

    def test_wrong_skill_name_scores_false(self):
        """A Skill call naming some other skill must not count."""
        result, _ = self.run_probe("my-skill", skill_tool_events("other-skill"))
        self.assertFalse(result)

    def test_stages_real_skill_not_uuid_command(self):
        """Probe must stage .claude/skills/<name>/SKILL.md, not a uuid slash command."""
        _, snapshot = self.run_probe("my-skill", skill_tool_events("my-skill"))
        self.assertIn(
            ".claude/skills/my-skill/SKILL.md",
            snapshot,
            "skill under test was not staged at .claude/skills/<name>/SKILL.md",
        )
        command_files = [
            line
            for line in snapshot.splitlines()
            if line.startswith(".claude/commands/") and line.endswith(".md")
        ]
        self.assertEqual(
            command_files,
            [],
            "uuid slash-command stand-in should not be planted: %s" % command_files,
        )


class TestDetectSkillTrigger(unittest.TestCase):
    """Pure detection over parsed events."""

    def test_matches_real_name_in_skill_tool(self):
        events = [
            {
                "type": "assistant",
                "message": {
                    "content": [
                        {"type": "tool_use", "name": "Skill", "input": {"skill": "my-skill"}}
                    ]
                },
            }
        ]
        self.assertTrue(detect_skill_trigger(events, "my-skill"))

    def test_matches_real_name_in_read_tool(self):
        events = [
            {
                "type": "assistant",
                "message": {
                    "content": [
                        {
                            "type": "tool_use",
                            "name": "Read",
                            "input": {"file_path": "/x/.claude/skills/my-skill/SKILL.md"},
                        }
                    ]
                },
            }
        ]
        self.assertTrue(detect_skill_trigger(events, "my-skill"))

    def test_ignores_unrelated_tools_before_skill(self):
        events = [
            {
                "type": "assistant",
                "message": {
                    "content": [
                        {"type": "tool_use", "name": "Bash", "input": {"command": "ls"}},
                        {"type": "tool_use", "name": "Skill", "input": {"skill": "my-skill"}},
                    ]
                },
            }
        ]
        self.assertTrue(detect_skill_trigger(events, "my-skill"))

    def test_uuid_stand_in_is_not_the_skill(self):
        """Matching must use the real name, never a uuid-suffixed stand-in."""
        events = [
            {
                "type": "assistant",
                "message": {
                    "content": [
                        {
                            "type": "tool_use",
                            "name": "Skill",
                            "input": {"skill": "my-skill-skill-a1b2c3d4"},
                        }
                    ]
                },
            }
        ]
        self.assertFalse(detect_skill_trigger(events, "my-skill"))

    def test_no_tool_call_is_false(self):
        events = [
            {
                "type": "assistant",
                "message": {"content": [{"type": "text", "text": "just an answer"}]},
            }
        ]
        self.assertFalse(detect_skill_trigger(events, "my-skill"))


if __name__ == "__main__":
    unittest.main()
