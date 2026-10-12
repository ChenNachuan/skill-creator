#!/usr/bin/env python3
"""
Ecosystem health checks for a skills directory.

Checks: trigger collision, near-duplicate names, stale references,
description lint, token budget, pinned model detection.

Exit codes:
    0  = clean (no findings)
    1  = error (tool failure)
    10 = findings present (with --strict)

Usage:
    python -m scripts.doctor <skills_dir> [--strict]
"""

import argparse
import re
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    yaml = None


def _parse_frontmatter_simple(text):
    """Minimal YAML frontmatter parser for when pyyaml is unavailable."""
    result = {}
    current_parent = None
    block_key = None
    block_lines = []
    for line in text.strip().split('\n'):
        if not line.strip() or line.strip().startswith('#'):
            continue
        indent = len(line) - len(line.lstrip())
        if block_key and indent > 0:
            block_lines.append(line.strip())
            continue
        elif block_key and indent == 0:
            result[block_key] = ' '.join(block_lines)
            block_key = None
            block_lines = []
        if ':' not in line:
            continue
        key, _, value = line.partition(':')
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if indent == 0:
            if value.startswith('>-') or value.startswith('|'):
                block_key = key
                block_lines = []
            elif value == '':
                current_parent = key
                result[key] = {}
            else:
                current_parent = None
                result[key] = value
        elif indent > 0 and current_parent:
            if not isinstance(result.get(current_parent), dict):
                result[current_parent] = {}
            result[current_parent][key] = value
    if block_key:
        result[block_key] = ' '.join(block_lines)
    return result


def extract_frontmatter(skill_md: Path) -> dict | None:
    content = skill_md.read_text()
    match = re.search(r'^---\n(.*?)\n---', content, re.DOTALL)
    if not match:
        return None
    try:
        if yaml:
            return yaml.safe_load(match.group(1))
        else:
            return _parse_frontmatter_simple(match.group(1))
    except Exception:
        return None


def tokenize(text: str) -> set:
    return set(re.findall(r'\b[a-z]{3,}\b', text.lower()))


def jaccard(a: set, b: set) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def find_skills(skills_dir: Path) -> list[Path]:
    """Find all skill roots (directories containing SKILL.md)."""
    skills = []
    for smd in skills_dir.rglob('SKILL.md'):
        skills.append(smd.parent)
    return sorted(skills)


def check_skills(skills: list[Path]) -> list[dict]:
    findings = []
    frontmatters = {}

    # Parse all frontmatters
    for skill_root in skills:
        smd = skill_root / 'SKILL.md'
        fm = extract_frontmatter(smd)
        if fm:
            frontmatters[skill_root.name] = fm

    names = list(frontmatters.keys())

    # 1. Near-duplicate names
    for i, n1 in enumerate(names):
        for n2 in names[i+1:]:
            if n1 != n2 and (n1 in n2 or n2 in n1):
                findings.append({'check': 'near_duplicate_name', 'severity': 'warn',
                                 'detail': chr(39)+n1+chr(39)+" and "+chr(39)+n2+chr(39)+" are near-duplicates"})

    # 2. Trigger collision (description Jaccard)
    descriptions = {}
    for name, fm in frontmatters.items():
        desc = fm.get('description', '')
        descriptions[name] = tokenize(desc)

    for i, n1 in enumerate(names):
        for n2 in names[i+1:]:
            sim = jaccard(descriptions.get(n1, set()), descriptions.get(n2, set()))
            if sim > 0.4:
                findings.append({'check': 'trigger_collision', 'severity': 'warn',
                                 'detail': f"'{n1}' <-> '{n2}' description Jaccard={sim:.2f} > 0.40"})

    # 3. Description lint
    for name, fm in frontmatters.items():
        desc = fm.get('description', '')

        if len(desc) > 1024:
            findings.append({'check': 'description_length', 'severity': 'fail',
                             'detail': f"'{name}': {len(desc)} chars > 1024"})

        if not any(kw in desc.lower() for kw in ['use when', 'when ', 'used when', 'use for']):
            findings.append({'check': 'description_trigger_words', 'severity': 'warn',
                             'detail': f"'{name}': missing 'Use when' trigger phrasing"})

        # Workflow summary smell (SDO trap)
        if re.search(r'(then|next|after that|step \d)', desc.lower()):
            findings.append({'check': 'description_workflow_summary', 'severity': 'warn',
                             'detail': f"'{name}': description may summarize workflow (SDO trap)"})

    # 4. Stale references
    for skill_root in skills:
        smd = skill_root / 'SKILL.md'
        content = smd.read_text()
        # Find referenced paths like references/foo.md or scripts/bar.py
        refs = re.findall(r'(?:references|scripts|assets|evals)/[\w./-]+', content)
        for ref in refs:
            target = skill_root / ref
            if not target.exists():
                findings.append({'check': 'stale_reference', 'severity': 'fail',
                                 'detail': f"'{skill_root.name}': references '{ref}' which does not exist"})

    # 5. Token budget (top heavy files)
    for skill_root in skills:
        smd = skill_root / 'SKILL.md'
        body_lines = smd.read_text().count('\n')
        if body_lines > 500:
            findings.append({'check': 'body_lines', 'severity': 'warn',
                             'detail': f"'{skill_root.name}': SKILL.md is {body_lines} lines > 500"})

    # 5b. Description budget (listing budget ~15k chars across all skills)
    total_desc_chars = sum(len(fm.get('description', '')) for fm in frontmatters.values())
    LISTING_BUDGET = 15000
    if total_desc_chars > LISTING_BUDGET:
        findings.append({'check': 'description_budget', 'severity': 'fail',
                         'detail': f"Total description chars {total_desc_chars} exceeds listing budget {LISTING_BUDGET}. Skills may be silently dropped."})

    # 5c. Per-skill description length
    for name, fm in frontmatters.items():
        desc_len = len(fm.get('description', ''))
        if desc_len > 800:
            findings.append({'check': 'description_length_warn', 'severity': 'warn',
                             'detail': f"'{name}': description {desc_len} chars, consider shortening (budget shared across all skills)"})

    # 5d. Trigger overlap (description keyword collision)
    desc_tokens = {}
    for name, fm in frontmatters.items():
        desc_tokens[name] = tokenize(fm.get('description', ''))

    names_list = list(desc_tokens.keys())
    for i, n1 in enumerate(names_list):
        for n2 in names_list[i+1:]:
            sim = jaccard(desc_tokens.get(n1, set()), desc_tokens.get(n2, set()))
            if sim > 0.35:
                findings.append({'check': 'trigger_overlap', 'severity': 'warn',
                                 'detail': f"'{n1}' <-> '{n2}' trigger overlap={sim:.2f} > 0.35 (shared terms: {desc_tokens[n1] & desc_tokens[n2]})"})

    # 6. Pinned model detection
    for skill_root in skills:
        for md_file in skill_root.rglob('*.md'):
            content = md_file.read_text()
            if re.search(r'claude-[a-z0-9-]+-\d{8}', content):
                findings.append({'check': 'pinned_model', 'severity': 'fail',
                                 'detail': f"'{skill_root.name}': date-pinned model reference in {md_file.name}"})

    return findings


def main():
    parser = argparse.ArgumentParser(description="Ecosystem health checks for skills")
    parser.add_argument('skills_dir', type=Path, help='Directory containing skills')
    parser.add_argument('--strict', action='store_true', help='Exit 10 on any findings')

    args = parser.parse_args()

    if not args.skills_dir.is_dir():
        print(f"Error: not a directory: {args.skills_dir}", file=sys.stderr)
        sys.exit(1)

    skills = find_skills(args.skills_dir)
    if not skills:
        print("No skills found.")
        sys.exit(0)

    print(f"Checking {len(skills)} skills in {args.skills_dir}...\n")

    findings = check_skills(skills)

    if not findings:
        print("✅ Clean — no findings.")
        sys.exit(0)

    # Group by severity
    fails = [f for f in findings if f['severity'] == 'fail']
    warns = [f for f in findings if f['severity'] == 'warn']

    if fails:
        print(f"❌ FAIL ({len(fails)}):")
        for f in fails:
            print(f"  [{f['check']}] {f['detail']}")

    if warns:
        print(f"\n⚠️  WARN ({len(warns)}):")
        for f in warns:
            print(f"  [{f['check']}] {f['detail']}")

    total = len(fails) + len(warns)
    print(f"\n{total} findings ({len(fails)} fail, {len(warns)} warn)")

    if args.strict:
        sys.exit(10)
    else:
        sys.exit(0 if not fails else 1)


if __name__ == '__main__':
    main()
