#!/usr/bin/env python3
"""Run trigger evaluation for a skill description.

Tests whether a skill's description causes Claude to trigger (read the skill)
for a set of queries. Outputs results as JSON.
"""

import argparse
import json
import os
import re
import select
import subprocess
import sys
import tempfile
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

from scripts.utils import parse_skill_md


def find_project_root() -> Path:
    """Find the project root by walking up from cwd looking for .claude/.

    Mimics how Claude Code discovers its project root, so the command file
    we create ends up where claude -p will look for it.
    """
    current = Path.cwd()
    for parent in [current, *current.parents]:
        if (parent / ".claude").is_dir():
            return parent
    return current


def _input_names_target(tool_name: str, tool_input: dict, target_name: str) -> bool:
    """True when a Skill/Read tool input names target_name exactly."""
    if tool_name == "Skill":
        return tool_input.get("skill") == target_name
    if tool_name == "Read":
        parts = Path(tool_input.get("file_path", "")).parts
        return "skills" in parts and target_name in parts
    return False


def _json_blob_names_target(tool_name: str, blob: str, target_name: str) -> bool:
    """True when a tool-input JSON blob names target_name exactly.

    Falls back to a strict key/value probe when the blob is still partial JSON.
    """
    try:
        data = json.loads(blob)
    except json.JSONDecodeError:
        if tool_name == "Skill":
            return re.search(r'"skill"\s*:\s*"%s"' % re.escape(target_name), blob) is not None
        return False
    if not isinstance(data, dict):
        return False
    return _input_names_target(tool_name, data, target_name)


def detect_skill_trigger(events, target_name: str) -> bool:
    """Return True if any Skill/Read tool_use names target_name.

    Unrelated tools are ignored — a Bash call before Skill does not abort
    detection. Matching is against the real skill name, never a stand-in
    identifier, and never a substring of a different name.
    """
    pending_tool = None
    accumulated = ""

    for event in events:
        etype = event.get("type")

        if etype == "stream_event":
            se = event.get("event", {})
            se_type = se.get("type", "")

            if se_type == "content_block_start":
                cb = se.get("content_block", {})
                if cb.get("type") == "tool_use":
                    tool_name = cb.get("name", "")
                    pending_tool = tool_name if tool_name in ("Skill", "Read") else None
                    accumulated = ""

            elif se_type == "content_block_delta" and pending_tool:
                delta = se.get("delta", {})
                if delta.get("type") == "input_json_delta":
                    accumulated += delta.get("partial_json", "")
                    if _json_blob_names_target(pending_tool, accumulated, target_name):
                        return True

            elif se_type in ("content_block_stop", "message_stop"):
                if pending_tool and _json_blob_names_target(pending_tool, accumulated, target_name):
                    return True
                pending_tool = None
                accumulated = ""

        elif etype == "assistant":
            for item in event.get("message", {}).get("content", []):
                if item.get("type") != "tool_use":
                    continue
                tool_name = item.get("name", "")
                if tool_name not in ("Skill", "Read"):
                    continue
                if _input_names_target(tool_name, item.get("input", {}), target_name):
                    return True

        elif etype == "result":
            return False

    return False


def _iter_process_events(process, timeout: int):
    """Yield parsed JSON events from process stdout until timeout or EOF."""
    start_time = time.time()
    buffer = ""

    while time.time() - start_time < timeout:
        if process.poll() is not None:
            remaining = process.stdout.read()
            if remaining:
                buffer += remaining.decode("utf-8", errors="replace")
            break

        ready, _, _ = select.select([process.stdout], [], [], 1.0)
        if not ready:
            continue

        chunk = os.read(process.stdout.fileno(), 8192)
        if not chunk:
            break
        buffer += chunk.decode("utf-8", errors="replace")

        while "\n" in buffer:
            line, buffer = buffer.split("\n", 1)
            line = line.strip()
            if not line:
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            yield event

    if buffer.strip():
        try:
            yield json.loads(buffer.strip())
        except json.JSONDecodeError:
            pass


def run_single_query(
    query: str,
    skill_name: str,
    skill_description: str,
    timeout: int,
    project_root: str,
    model: str | None = None,
) -> bool:
    """Run a single query and return whether the skill was triggered.

    Stages the skill under test at .claude/skills/<skill_name>/SKILL.md in an
    isolated directory (so parallel workers cannot clobber each other), runs
    `claude -p` from there, and reports whether the model invoked that skill
    by its real name via a Skill or Read tool call.
    """
    staging = tempfile.TemporaryDirectory(prefix="skill-probe-")
    try:
        staging_root = Path(staging.name)
        skill_dir = staging_root / ".claude" / "skills" / skill_name
        skill_dir.mkdir(parents=True)
        # Use YAML block scalar to avoid breaking on quotes in description
        indented_desc = "\n  ".join(skill_description.split("\n"))
        (skill_dir / "SKILL.md").write_text(
            f"---\n"
            f"name: {skill_name}\n"
            f"description: |\n"
            f"  {indented_desc}\n"
            f"---\n\n"
            f"# {skill_name}\n\n"
            f"This skill handles: {skill_description}\n"
        )

        cmd = [
            "claude",
            "-p", query,
            "--output-format", "stream-json",
            "--verbose",
            "--include-partial-messages",
        ]
        if model:
            cmd.extend(["--model", model])

        # Remove CLAUDECODE env var to allow nesting claude -p inside a
        # Claude Code session. The guard is for interactive terminal conflicts;
        # programmatic subprocess usage is safe.
        env = {k: v for k, v in os.environ.items() if k != "CLAUDECODE"}

        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            cwd=str(staging_root),
            env=env,
        )

        try:
            events = _iter_process_events(process, timeout)
            return detect_skill_trigger(events, skill_name)
        finally:
            if process.poll() is None:
                process.kill()
                process.wait()
            if process.stdout:
                process.stdout.close()
    finally:
        staging.cleanup()


def run_eval(
    eval_set: list[dict],
    skill_name: str,
    description: str,
    num_workers: int,
    timeout: int,
    project_root: Path,
    runs_per_query: int = 1,
    trigger_threshold: float = 0.5,
    model: str | None = None,
) -> dict:
    """Run the full eval set and return results."""
    results = []

    with ProcessPoolExecutor(max_workers=num_workers) as executor:
        future_to_info = {}
        for item in eval_set:
            for run_idx in range(runs_per_query):
                future = executor.submit(
                    run_single_query,
                    item["query"],
                    skill_name,
                    description,
                    timeout,
                    str(project_root),
                    model,
                )
                future_to_info[future] = (item, run_idx)

        query_triggers: dict[str, list[bool]] = {}
        query_items: dict[str, dict] = {}
        for future in as_completed(future_to_info):
            item, _ = future_to_info[future]
            query = item["query"]
            query_items[query] = item
            if query not in query_triggers:
                query_triggers[query] = []
            try:
                query_triggers[query].append(future.result())
            except Exception as e:
                print(f"Warning: query failed: {e}", file=sys.stderr)
                query_triggers[query].append(False)

    for query, triggers in query_triggers.items():
        item = query_items[query]
        trigger_rate = sum(triggers) / len(triggers)
        should_trigger = item["should_trigger"]
        if should_trigger:
            did_pass = trigger_rate >= trigger_threshold
        else:
            did_pass = trigger_rate < trigger_threshold
        results.append({
            "query": query,
            "should_trigger": should_trigger,
            "trigger_rate": trigger_rate,
            "triggers": sum(triggers),
            "runs": len(triggers),
            "pass": did_pass,
        })

    passed = sum(1 for r in results if r["pass"])
    total = len(results)

    return {
        "skill_name": skill_name,
        "description": description,
        "results": results,
        "summary": {
            "total": total,
            "passed": passed,
            "failed": total - passed,
        },
    }


def main():
    parser = argparse.ArgumentParser(description="Run trigger evaluation for a skill description")
    parser.add_argument("--eval-set", required=True, help="Path to eval set JSON file")
    parser.add_argument("--skill-path", required=True, help="Path to skill directory")
    parser.add_argument("--description", default=None, help="Override description to test")
    parser.add_argument("--num-workers", type=int, default=10, help="Number of parallel workers")
    parser.add_argument("--timeout", type=int, default=30, help="Timeout per query in seconds")
    parser.add_argument("--runs-per-query", type=int, default=3, help="Number of runs per query")
    parser.add_argument("--trigger-threshold", type=float, default=0.5, help="Trigger rate threshold")
    parser.add_argument("--model", default=None, help="Model to use for claude -p (default: user's configured model)")
    parser.add_argument("--verbose", action="store_true", help="Print progress to stderr")
    args = parser.parse_args()

    eval_set = json.loads(Path(args.eval_set).read_text())
    skill_path = Path(args.skill_path)

    if not (skill_path / "SKILL.md").exists():
        print(f"Error: No SKILL.md found at {skill_path}", file=sys.stderr)
        sys.exit(1)

    name, original_description, content = parse_skill_md(skill_path)
    description = args.description or original_description
    project_root = find_project_root()

    if args.verbose:
        print(f"Evaluating: {description}", file=sys.stderr)

    output = run_eval(
        eval_set=eval_set,
        skill_name=name,
        description=description,
        num_workers=args.num_workers,
        timeout=args.timeout,
        project_root=project_root,
        runs_per_query=args.runs_per_query,
        trigger_threshold=args.trigger_threshold,
        model=args.model,
    )

    if args.verbose:
        summary = output["summary"]
        print(f"Results: {summary['passed']}/{summary['total']} passed", file=sys.stderr)
        for r in output["results"]:
            status = "PASS" if r["pass"] else "FAIL"
            rate_str = f"{r['triggers']}/{r['runs']}"
            print(f"  [{status}] rate={rate_str} expected={r['should_trigger']}: {r['query'][:70]}", file=sys.stderr)

    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
