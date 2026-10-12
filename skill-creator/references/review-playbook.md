# Review Playbook — 4 Stages × 15 Dimensions

Structured review for existing skills. Review is **read-only**: findings go to a workspace directory, never into the skill being reviewed.

## Process Overview

```
Stage 1: Structure scan     ─┐
Stage 2: Code / pitfall     ─┤→ skill-reviewer agent
                             ─┘
Stage 3: Doc ↔ code parity   ──→ doc-verifier agent
Stage 4: End-to-end tests    ──→ main flow (NEVER delegated)
Adversarial pass             ──→ adversary agent (after Stage 1–3)
```

**Evidence discipline**: Every P0/P1 finding must cite evidence (file, line, output). If you cannot confirm something, write `unverified` — do NOT guess a severity.

---

## Stage 1: Structure Scan

Run via `skill-reviewer` agent (or directly for quick checks):

- [ ] Frontmatter complete: `name` (kebab-case, ≤64 chars), `description` (≤1024 chars)
- [ ] Directory name matches frontmatter `name`
- [ ] Description has trigger words (user vocabulary, not just technical nouns)
- [ ] Description does NOT summarize workflow (SDO trap)
- [ ] `python -m py_compile scripts/*.py` passes (import paths valid)
- [ ] No orphan references (every file in SKILL.md index exists; every reference is indexed)
- [ ] Shared modules consistent (if skill family)
- [ ] Root entry isolation: only one `SKILL.md` (examples use `SKILL.example.md`)

## Stage 2: Code Review — Pitfall Scan

Run via `skill-reviewer` agent. Check against `references/common-pitfalls.md`:

- [ ] argparse subparser defaults (SUPPRESS)
- [ ] API read/write field name symmetry
- [ ] `allow_fail` consistency
- [ ] Status value i18n
- [ ] Operator placement (body vs query)
- [ ] Confirm logic vs documentation
- [ ] Domain-specific pitfalls (from your local additions)

For each finding: P0 (blocks release) / P1 (must fix before next iteration) / P2 (nice to have).

## Stage 3: Documentation ↔ Code Parity

Run via `doc-verifier` agent:

- [ ] Every command in SKILL.md exists in argparse/CLI
- [ ] Parameter names match code
- [ ] Examples are runnable (correct flags, valid paths)
- [ ] Constraints traceable to code ("always pass `allow_fail=True`" ← actual check)
- [ ] Return shapes documented match actual returns

Output: doc-drift table (claim | code | verdict: match/mismatch/unverified).

## Stage 4: End-to-End Tests (unskippable)

Main flow executes — never delegated to a subagent:

- [ ] Test both entry points (unified entry + direct call)
- [ ] Test `--yes` / `--env` flag placement
- [ ] Write operations: verify with a follow-up read
- [ ] Clean up after tests

---

## 15-Dimension Review Table

Each dimension rated P0 (block release) / P1 / P2 / `unverified`.

| # | Dimension | What to check | Typical P0 |
|---|-----------|---------------|------------|
| 1 | **Product value** | Does this skill solve a real problem? Would the user notice if it disappeared? | Skill exists without a demonstrated need |
| 2 | **Trigger boundary** | Does the description trigger on the right queries and NOT on near-misses? | Over-triggering on unrelated tasks |
| 3 | **Main flow** | Is the primary workflow clear and achievable end-to-end? | Critical step missing or ambiguous |
| 4 | **Over-constraint** | Does the skill over-prescribe where judgment is needed? | Rigid rules block valid use cases |
| 5 | **Proceduralization** | Should deterministic logic be a script instead of prose? | Long "always do X then Y then Z" that could be a script |
| 6 | **Artifacts & UI** | Are output formats, templates, and generated files correct? | Template produces invalid output |
| 7 | **Onboarding** | Can a first-time user get value within one session? | No quick-start, 500-line body, no examples |
| 8 | **Stability** | Does the skill resist partial failure? Re-runnable? No destructive surprises? | Overwrites data without backup |
| 9 | **Effect evidence** | Is there measurable proof the skill works (evals, before/after)? | Claims with no supporting evidence |
| 10 | **Weak-model readability** | Each rule stated once? Main file holds main flow only? | Same rule in 3 places, all slightly different |
| 11 | **Layering & token** | Body <500 lines? Heavy content in references? No duplication? | Body 800+ lines with inline API reference |
| 12 | **Compatibility** | Works across expected environments (Python version, OS, API version)? | Hardcoded absolute paths |
| 13 | **Host neutrality** | Skill works regardless of brand/runtime-specific jargon? Adapters removable? | References `claude -p` as the only execution method |
| 14 | **README** | Is there a README for humans installing/configuring the skill? | No install instructions |
| 15 | **Security & credentials** | Lethal trifecta check; secrets not in code; least privilege | API key in plaintext |

## Requirement Applicability Table

Before scoring, mark each row `applicable` / `N/A` / `TBD`:

| Requirement | Status | Evidence |
|-------------|--------|----------|
| Credential entry | | |
| Credential closure (input → save → partial-failure recovery → read-back) | | |
| Default + fallback paths | | |
| Feature introduction / onboarding | | |
| Publish contract (what the skill promises) | | |

## Multi-Agent Dispatch

| Agent | Stages | Mode | Output |
|-------|--------|------|--------|
| `skill-reviewer` | 1 + 2 | Read-only | findings (P0/P1/P2 + evidence) |
| `doc-verifier` | 3 | Read-only | doc-drift table |
| `adversary` | After 1–3 | Read-only | failure scenarios, gaps, security concerns |
| Main flow | 4 | Read-write (test artifacts) | e2e test results |

**Stage 4 is never delegated** — the main flow must run end-to-end tests to see real behavior.

## Output Location

Write review reports to `{workspace}/review-{timestamp}/`:
```
review-2026-01-15T10-30-00/
├── stage1-structure.md
├── stage2-pitfalls.md
├── stage3-doc-parity.md
├── stage4-e2e.md
├── adversary-report.md
└── findings.json          # consolidated P0/P1/P2
```

Never write review outputs into the skill directory under review.
