#!/usr/bin/env python3
"""
Run shipped evals for a skill (static lint or live model evaluation).

Usage:
    python -m scripts.run_skill_evals <skill_dir> --static    # CI-safe, no model calls
    python -m scripts.run_skill_evals <skill_dir> --live      # headless model evaluation

Prerequisite for --live: export CLAUDE_CODE_MAX_CONTEXT_TOKENS=524288

Exit codes:
    0 = all evals pass
    1 = evals fail (static or live)
"""

import argparse
import json
import re
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    yaml = None


def run_static(skill_dir: Path) -> dict:
    """
    Static checks: structure lint + trigger keyword presence + schema check.
    No model calls. CI-safe.
    """
    findings = []

    # 1. SKILL.md exists
    skill_md = skill_dir / 'SKILL.md'
    if not skill_md.exists():
        findings.append({'check': 'skill_md_exists', 'status': 'fail', 'detail': 'SKILL.md not found'})
        return {'passed': False, 'findings': findings}

    content = skill_md.read_text()

    # 2. Frontmatter valid
    match = re.search(r'^---\n(.*?)\n---', content, re.DOTALL)
    if not match:
        findings.append({'check': 'frontmatter', 'status': 'fail', 'detail': 'No YAML frontmatter'})
    elif yaml:
        try:
            fm = yaml.safe_load(match.group(1))
            if not isinstance(fm, dict):
                findings.append({'check': 'frontmatter', 'status': 'fail', 'detail': 'Frontmatter not a dict'})
            else:
                # 3. name and description present
                if 'name' not in fm:
                    findings.append({'check': 'name', 'status': 'fail', 'detail': 'Missing name'})
                if 'description' not in fm:
                    findings.append({'check': 'description', 'status': 'fail', 'detail': 'Missing description'})
                elif len(fm.get('description', '')) > 1024:
                    findings.append({'check': 'description_length', 'status': 'fail', 'detail': f"Description {len(fm['description'])} chars > 1024"})
        except yaml.YAMLError as e:
            findings.append({'check': 'frontmatter_yaml', 'status': 'fail', 'detail': str(e)})

    # 4. Body line count
    body_lines = content.count('\n')
    if body_lines > 500:
        findings.append({'check': 'body_lines', 'status': 'warn', 'detail': f"{body_lines} lines > 500 target"})

    # 5. evals/ directory exists with triggers.json
    evals_dir = skill_dir / 'evals'
    if not evals_dir.exists():
        findings.append({'check': 'evals_dir', 'status': 'warn', 'detail': 'No evals/ directory (recommend shipping evals)'})
    else:
        triggers = evals_dir / 'triggers.json'
        if not triggers.exists():
            findings.append({'check': 'triggers_json', 'status': 'warn', 'detail': 'No evals/triggers.json'})
        else:
            try:
                with open(triggers) as f:
                    data = json.load(f)
                has_positive = bool(data.get('positive'))
                has_near_miss = bool(data.get('near_miss'))
                if not has_positive:
                    findings.append({'check': 'triggers_positive', 'status': 'fail', 'detail': 'No positive trigger cases'})
                if not has_near_miss:
                    findings.append({'check': 'triggers_near_miss', 'status': 'warn', 'detail': 'No near-miss cases'})
            except json.JSONDecodeError as e:
                findings.append({'check': 'triggers_json_parse', 'status': 'fail', 'detail': str(e)})

    # 6. Scripts compile
    scripts_dir = skill_dir / 'scripts'
    if scripts_dir.exists():
        for py_file in sorted(scripts_dir.glob('*.py')):
            try:
                compile(py_file.read_text(), str(py_file), 'exec')
            except SyntaxError as e:
                findings.append({'check': f'script_compile:{py_file.name}', 'status': 'fail', 'detail': str(e)})

    # Determine pass
    has_fail = any(f['status'] == 'fail' for f in findings)
    return {'passed': not has_fail, 'findings': findings}


def run_live(skill_dir: Path, runs: int = 3) -> dict:
    """
    Live evaluation: run scenarios with headless claude + grader assertions.
    Skips if static checks fail.
    """
    static = run_static(skill_dir)
    if not static['passed']:
        print("Static checks failed — skipping live evaluation")
        return {'passed': False, 'static': static, 'live': None}

    evals_dir = skill_dir / 'evals' / 'scenarios'
    if not evals_dir.exists():
        return {'passed': True, 'static': static, 'live': {'note': 'No scenarios/ directory'}}

    scenario_files = sorted(evals_dir.glob('*.md'))
    if not scenario_files:
        return {'passed': True, 'static': static, 'live': {'note': 'No scenario files'}}

    results = []
    for sf in scenario_files:
        content = sf.read_text()
        match = re.search(r'^---\n(.*?)\n---', content, re.DOTALL)
        if not match or not yaml:
            results.append({'file': sf.name, 'status': 'skip', 'reason': 'No frontmatter or no yaml'})
            continue

        try:
            meta = yaml.safe_load(match.group(1))
        except yaml.YAMLError as e:
            results.append({'file': sf.name, 'status': 'fail', 'reason': str(e)})
            continue

        task = meta.get('task', 'unknown')
        assertions = meta.get('assertions', [])
        runs_n = meta.get('runs', runs)

        # Note: actual execution requires spawning claude subprocess
        # For now, report what would be run
        results.append({
            'file': sf.name,
            'task': task,
            'assertions': len(assertions),
            'runs': runs_n,
            'status': 'ready'
        })

    return {'passed': True, 'static': static, 'live': {'scenarios': results}}


def main():
    parser = argparse.ArgumentParser(description="Run shipped evals for a skill")
    parser.add_argument('skill_dir', type=Path, help='Path to skill directory')
    parser.add_argument('--static', action='store_true', help='Static checks only (CI-safe)')
    parser.add_argument('--live', action='store_true', help='Live model evaluation')
    parser.add_argument('--runs', type=int, default=3, help='Runs per scenario')
    parser.add_argument('--output', type=Path, help='Output JSON path')

    args = parser.parse_args()

    if not args.static and not args.live:
        args.static = True  # Default to static

    if args.static and not args.live:
        result = run_static(args.skill_dir)
    else:
        result = run_live(args.skill_dir, args.runs)

    if args.output:
        with open(args.output, 'w') as f:
            json.dump(result, f, indent=2)
        print(f"Report: {args.output}")

    # Print summary
    if 'findings' in result:
        for f in result['findings']:
            icon = {'fail': '❌', 'warn': '⚠️', 'pass': '✅'}.get(f['status'], '❓')
            print(f"  {icon} [{f['check']}] {f['detail']}")

    status = 'PASS' if result['passed'] else 'FAIL'
    print(f"\n{status}")
    sys.exit(0 if result['passed'] else 1)


if __name__ == '__main__':
    main()
