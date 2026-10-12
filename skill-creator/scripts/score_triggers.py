#!/usr/bin/env python3
"""
Score trigger accuracy using hash-stratified holdout split.

Deterministic, anti-leakage evaluation of skill description triggering.

Usage:
    python -m scripts.score_triggers --eval-set evals/triggers.json --skill-path my-skill [options]

Options:
    --dry-run       Print split without invoking claude (CI-safe)
    --strict        Require ≥8 positive + ≥8 negative, ≥3 trials per case
    --runs N        Trials per case (default 3, use odd number)
    --threshold F   Trigger rate threshold for pass (default 0.5)

Prerequisite for live mode: export CLAUDE_CODE_MAX_CONTEXT_TOKENS=524288
"""

import argparse
import hashlib
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

try:
    import yaml
except ImportError:
    yaml = None


def hash_stratified_split(cases: list, skill_name: str, holdout_frac: float = 0.4) -> dict:
    """
    Deterministic hash-stratified split: SHA256(skill_name:case_id) sorted,
    top ~holdout_frac per class goes to holdout.
    """
    classes = {}
    for c in cases:
        cls = c.get('class', 'positive' if c.get('should_trigger') else 'negative')
        classes.setdefault(cls, []).append(c)

    train, holdout = [], []
    for cls, items in sorted(classes.items()):
        # Sort by deterministic hash
        def hash_key(item):
            h = hashlib.sha256(f"{skill_name}:{item['id']}".encode()).hexdigest()
            return h
        sorted_items = sorted(items, key=hash_key)
        n_holdout = max(1, int(len(sorted_items) * holdout_frac))
        holdout.extend(sorted_items[:n_holdout])
        train.extend(sorted_items[n_holdout:])

    return {'train': train, 'holdout': holdout}


def load_eval_set(path: Path) -> list:
    """Load triggers.json and flatten to a list of cases."""
    with open(path) as f:
        data = json.load(f)

    cases = []
    for tier in ['positive', 'near_miss', 'holdout']:
        for item in data.get(tier, []):
            if 'should_trigger' not in item:
                print(f"Warning: case '{item.get('id', '?')}' in tier '{tier}' missing 'should_trigger', defaulting to False", file=sys.stderr)
            item['class'] = tier if tier != 'holdout' else ('positive' if item.get('should_trigger') else 'negative')
            if tier == 'holdout':
                item['is_holdout'] = True
            cases.append(item)
    return cases


def run_trigger_query(query: str, description: str, skill_name: str) -> bool:
    """
    Detect if a query triggers the skill via claude -p with stream-json.
    Returns True if the skill appears to be triggered.
    """
    import tempfile

    # Use tempfile to avoid polluting the working directory
    with tempfile.TemporaryDirectory(prefix='skill-trigger-') as tmp_dir:
        cmd_file = Path(tmp_dir) / f"{skill_name}-trigger.md"
        cmd_file.write_text(f"---\ndescription: {description}\n---\n\n{query}\n")

        try:
            env = os.environ.copy()
            env.pop('CLAUDECODE', None)  # Allow nested runs

            result = subprocess.run(
                ['claude', '-p', query, '--output-format', 'stream-json', '--verbose'],
                capture_output=True, text=True, timeout=120, env=env
            )

            triggered = cmd_file.stem in result.stdout
            return triggered

        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False


def score(cases: list, skill_name: str, description: str, runs: int, threshold: float, live: bool) -> dict:
    """Score all cases and compute metrics."""
    results = []

    for case in cases:
        query = case['query']
        should = case['should_trigger']

        if live:
            triggers = sum(1 for _ in range(runs) if run_trigger_query(query, description, skill_name))
            trigger_rate = triggers / runs
        else:
            trigger_rate = 0.5  # placeholder for dry-run

        passed = (trigger_rate >= threshold) if should else (trigger_rate < threshold)
        stability = max(trigger_rate, 1 - trigger_rate)

        results.append({
            'id': case['id'],
            'query': query,
            'should_trigger': should,
            'trigger_rate': trigger_rate,
            'passed': passed,
            'stability': stability,
            'is_holdout': case.get('is_holdout', False),
            'class': case.get('class', 'unknown')
        })

    # Compute metrics
    tp = sum(1 for r in results if r['should_trigger'] and r['passed'])
    fp = sum(1 for r in results if not r['should_trigger'] and not r['passed'])
    tn = sum(1 for r in results if not r['should_trigger'] and r['passed'])
    fn = sum(1 for r in results if r['should_trigger'] and not r['passed'])

    total = len(results)
    accuracy = (tp + tn) / total if total else 0
    precision = tp / (tp + fp) if (tp + fp) else 0
    recall = tp / (tp + fn) if (tp + fn) else 0
    specificity = tn / (tn + fp) if (tn + fp) else 0
    avg_stability = sum(r['stability'] for r in results) / total if total else 0

    # Holdout-only metrics
    holdout_results = [r for r in results if r['is_holdout']]
    holdout_acc = sum(1 for r in holdout_results if r['passed']) / len(holdout_results) if holdout_results else 0

    return {
        'metrics': {
            'accuracy': round(accuracy, 4),
            'precision': round(precision, 4),
            'recall': round(recall, 4),
            'specificity': round(specificity, 4),
            'stability': round(avg_stability, 4),
            'holdout_accuracy': round(holdout_acc, 4)
        },
        'confusion': {'tp': tp, 'fp': fp, 'tn': tn, 'fn': fn},
        'results': results
    }


def main():
    parser = argparse.ArgumentParser(description="Score skill trigger accuracy with hash-stratified holdout")
    parser.add_argument('--eval-set', type=Path, required=True, help='Path to triggers.json')
    parser.add_argument('--skill-path', type=Path, required=True, help='Path to skill directory')
    parser.add_argument('--dry-run', action='store_true', help='Print split without invoking claude')
    parser.add_argument('--strict', action='store_true', help='Require ≥8 pos + ≥8 neg, ≥3 trials')
    parser.add_argument('--runs', type=int, default=3, help='Trials per case (use odd number)')
    parser.add_argument('--threshold', type=float, default=0.5, help='Trigger rate threshold')
    parser.add_argument('--output', type=Path, help='Output JSON path')

    args = parser.parse_args()

    # Load description from skill
    skill_md = args.skill_path / 'SKILL.md'
    if not skill_md.exists():
        print(f"Error: SKILL.md not found in {args.skill_path}", file=sys.stderr)
        sys.exit(1)

    content = skill_md.read_text()
    # Extract description from frontmatter (simplified)
    import re
    match = re.search(r'^---\n(.*?)\n---', content, re.DOTALL)
    description = ''
    if match:
        if yaml:
            fm = yaml.safe_load(match.group(1))
            description = fm.get('description', '')
        else:
            # Minimal fallback
            for line in match.group(1).split('\n'):
                if line.strip().startswith('description:'):
                    description = line.partition(':')[2].strip()
                    break

    skill_name = args.skill_path.name

    # Load and split
    cases = load_eval_set(args.eval_set)

    # Strict mode checks
    if args.strict:
        pos = [c for c in cases if c.get('should_trigger')]
        neg = [c for c in cases if not c.get('should_trigger')]
        if len(pos) < 8:
            print(f"Strict mode: need ≥8 positive cases, got {len(pos)}", file=sys.stderr)
            sys.exit(1)
        if len(neg) < 8:
            print(f"Strict mode: need ≥8 negative cases, got {len(neg)}", file=sys.stderr)
            sys.exit(1)
        if args.runs < 3 or args.runs % 2 == 0:
            print(f"Strict mode: need ≥3 odd-count trials, got {args.runs}", file=sys.stderr)
            sys.exit(1)

    split = hash_stratified_split(cases, skill_name)
    all_cases = split['train'] + split['holdout']

    if args.dry_run:
        print(f"Split: {len(split['train'])} train, {len(split['holdout'])} holdout")
        print("\nTrain:")
        for c in split['train']:
            print(f"  [{c['id']}] {'+' if c['should_trigger'] else '-'} {c['query'][:60]}")
        print("\nHoldout:")
        for c in split['holdout']:
            print(f"  [{c['id']}] {'+' if c['should_trigger'] else '-'} {c['query'][:60]}")
        sys.exit(0)

    # Live scoring
    if not args.dry_run:
        print("NOTE: For live mode, ensure CLAUDE_CODE_MAX_CONTEXT_TOKENS=524288 is set.")
        print(f"Scoring {len(all_cases)} cases × {args.runs} runs...")

    report = score(all_cases, skill_name, description, args.runs, args.threshold, live=not args.dry_run)

    # Pin hashes for anti-tampering
    report['description_sha256'] = hashlib.sha256(description.encode()).hexdigest()
    report['eval_set_sha256'] = hashlib.sha256(json.dumps(cases, sort_keys=True).encode()).hexdigest()
    report['skill_name'] = skill_name

    output = args.output or Path('trigger_report.json')
    with open(output, 'w') as f:
        json.dump(report, f, indent=2)

    # Print summary
    m = report['metrics']
    print(f"\nResults:")
    print(f"  Accuracy:    {m['accuracy']:.1%}")
    print(f"  Precision:   {m['precision']:.1%}")
    print(f"  Recall:      {m['recall']:.1%}")
    print(f"  Specificity: {m['specificity']:.1%}")
    print(f"  Stability:   {m['stability']:.1%}")
    print(f"  Holdout acc: {m['holdout_accuracy']:.1%}")
    print(f"\n  Confusion: TP={report['confusion']['tp']} FP={report['confusion']['fp']} TN={report['confusion']['tn']} FN={report['confusion']['fn']}")
    print(f"\nReport: {output}")


if __name__ == '__main__':
    main()
