"""Shared utilities for skill-creator scripts."""

import json
from pathlib import Path


def load_eval_cases(path: Path) -> list:
    """Load trigger eval cases from either documented shape.

    Tiered (references/schemas.md):
        {skill_name, positive[], near_miss[], holdout[]}
        each entry: {id, query, should_trigger, rationale}

    Flat (legacy run_eval/run_loop):
        [{query, should_trigger}, ...]

    Returns one flat list of case dicts. Tiered entries get `class` and,
    for the holdout tier, `is_holdout` injected — matching what
    score_triggers.load_eval_set produces.
    """
    data = json.loads(Path(path).read_text())

    if isinstance(data, list):
        for item in data:
            if "query" not in item or "should_trigger" not in item:
                raise ValueError(
                    f"flat eval-set entries need 'query' and 'should_trigger', got {sorted(item)}"
                )
        return data

    if not isinstance(data, dict):
        raise ValueError(f"eval-set must be a list or a tiered object, got {type(data).__name__}")

    cases = []
    for tier in ("positive", "near_miss", "holdout"):
        for item in data.get(tier, []):
            if "id" not in item:
                raise ValueError(f"tiered eval-set entries need 'id' (used for hashing), got {sorted(item)}")
            if "query" not in item or "should_trigger" not in item:
                raise ValueError(
                    f"tiered eval-set entries need 'query' and 'should_trigger', got {sorted(item)}"
                )
            entry = dict(item)
            entry["class"] = tier if tier != "holdout" else (
                "positive" if entry.get("should_trigger") else "negative"
            )
            if tier == "holdout":
                entry["is_holdout"] = True
            cases.append(entry)

    return cases


def parse_skill_md(skill_path: Path) -> tuple[str, str, str]:
    """Parse a SKILL.md file, returning (name, description, full_content)."""
    content = (skill_path / "SKILL.md").read_text()
    lines = content.split("\n")

    if lines[0].strip() != "---":
        raise ValueError("SKILL.md missing frontmatter (no opening ---)")

    end_idx = None
    for i, line in enumerate(lines[1:], start=1):
        if line.strip() == "---":
            end_idx = i
            break

    if end_idx is None:
        raise ValueError("SKILL.md missing frontmatter (no closing ---)")

    name = ""
    description = ""
    frontmatter_lines = lines[1:end_idx]
    i = 0
    while i < len(frontmatter_lines):
        line = frontmatter_lines[i]
        if line.startswith("name:"):
            name = line[len("name:"):].strip().strip('"').strip("'")
        elif line.startswith("description:"):
            value = line[len("description:"):].strip()
            # Handle YAML multiline indicators (>, |, >-, |-)
            if value in (">", "|", ">-", "|-"):
                continuation_lines: list[str] = []
                i += 1
                while i < len(frontmatter_lines) and (frontmatter_lines[i].startswith("  ") or frontmatter_lines[i].startswith("\t")):
                    continuation_lines.append(frontmatter_lines[i].strip())
                    i += 1
                description = " ".join(continuation_lines)
                continue
            else:
                description = value.strip('"').strip("'")
        i += 1

    return name, description, content
