#!/usr/bin/env python3
"""
Snapshot a skill directory with SHA-256 integrity verification.

Atomic writes: temp dir + rename. Re-runnable. Never leaves partial baseline-*.

Usage:
    python -m scripts.snapshot_skill snapshot <skill_dir> <workspace>
    python -m scripts.snapshot_skill verify <skill_dir> <snapshot_dir>

Example:
    python -m scripts.snapshot_skill snapshot my-skill workspace/
    python -m scripts.snapshot_skill verify my-skill workspace/baseline-2026-01-15T10-30-00/
"""

import argparse
import hashlib
import os
import shutil
import sys
import time
from pathlib import Path


def compute_tree_digest(root: Path) -> str:
    """Compute SHA-256 digest of all files in the tree (length-prefixed path + bytes)."""
    h = hashlib.sha256()
    for file_path in sorted(root.rglob('*')):
        if file_path.is_symlink():
            raise ValueError(f"Symbolic link found in tree: {file_path}")
        if not file_path.is_file():
            continue
        rel = file_path.relative_to(root)
        data = file_path.read_bytes()
        # Length-prefixed to prevent path/content ambiguity
        path_bytes = str(rel).encode('utf-8')
        h.update(len(path_bytes).to_bytes(8, 'big'))
        h.update(path_bytes)
        h.update(len(data).to_bytes(8, 'big'))
        h.update(data)
    return h.hexdigest()


def snapshot(skill_dir: Path, workspace: Path) -> int:
    """Create an immutable snapshot of skill_dir into workspace."""
    if not skill_dir.is_dir():
        print(f"Error: not a directory: {skill_dir}", file=sys.stderr)
        return 1

    # Reject symlinks in source
    for p in skill_dir.rglob('*'):
        if p.is_symlink():
            print(f"Error: symlink found in source: {p}", file=sys.stderr)
            return 1

    ts = time.strftime('%Y-%m-%dT%H-%M-%S')
    target = workspace / f"baseline-{ts}"
    tmp = workspace / f".tmp-snapshot-{ts}"

    # If an identical snapshot already exists (idempotent re-run), exit 0
    if target.exists():
        existing_digest = (target / '.digest').read_text().strip() if (target / '.digest').exists() else None
        if existing_digest:
            current = compute_tree_digest(skill_dir)
            if current == existing_digest:
                print(f"Snapshot already exists and matches: {target}")
                return 0

    # Clean stale temp dirs
    for stale in workspace.glob('.tmp-snapshot-*'):
        shutil.rmtree(stale, ignore_errors=True)

    try:
        tmp.mkdir(parents=True, exist_ok=True)
        # Copy tree
        for src in sorted(skill_dir.rglob('*')):
            if src.is_file() and not src.is_symlink():
                rel = src.relative_to(skill_dir)
                dst = tmp / rel
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dst)

        # Compute and store digest
        digest = compute_tree_digest(tmp)
        (tmp / '.digest').write_text(digest + '\n')

        # Atomic rename
        os.rename(tmp, target)
        print(f"Snapshot created: {target}")
        print(f"Digest: {digest}")
        return 0

    except Exception as e:
        # Clean up temp on failure
        shutil.rmtree(tmp, ignore_errors=True)
        print(f"Error: {e}", file=sys.stderr)
        return 1


def verify(skill_dir: Path, snapshot_dir: Path) -> int:
    """Verify skill_dir matches the snapshot."""
    if not skill_dir.is_dir():
        print(f"Error: not a directory: {skill_dir}", file=sys.stderr)
        return 1
    if not snapshot_dir.is_dir():
        print(f"Error: snapshot not found: {snapshot_dir}", file=sys.stderr)
        return 1

    digest_file = snapshot_dir / '.digest'
    if not digest_file.exists():
        print(f"Error: no .digest in snapshot (corrupt?)", file=sys.stderr)
        return 1

    expected = digest_file.read_text().strip()
    actual = compute_tree_digest(skill_dir)

    if actual == expected:
        print(f"Verify OK: {skill_dir} matches {snapshot_dir}")
        return 0
    else:
        print(f"Verify FAILED: {skill_dir} does NOT match {snapshot_dir}", file=sys.stderr)
        print(f"  expected: {expected}", file=sys.stderr)
        print(f"  actual:   {actual}", file=sys.stderr)
        return 1


def main():
    parser = argparse.ArgumentParser(description="Snapshot and verify skill directories")
    sub = parser.add_subparsers(dest='command', required=True)

    p_snap = sub.add_parser('snapshot', help='Create immutable snapshot')
    p_snap.add_argument('skill_dir', type=Path)
    p_snap.add_argument('workspace', type=Path)

    p_ver = sub.add_parser('verify', help='Verify skill matches snapshot')
    p_ver.add_argument('skill_dir', type=Path)
    p_ver.add_argument('snapshot_dir', type=Path)

    args = parser.parse_args()

    if args.command == 'snapshot':
        sys.exit(snapshot(args.skill_dir, args.workspace))
    elif args.command == 'verify':
        sys.exit(verify(args.skill_dir, args.snapshot_dir))


if __name__ == '__main__':
    main()
