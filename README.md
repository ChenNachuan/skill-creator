# skill-creator

> A comprehensive skill for creating, evaluating, reviewing, and packaging Claude Code skills.

**Location**: `skill-creator/` · **License**: Apache-2.0 · **Language**: English

---

## What Is This

skill-creator is a Claude Code skill that guides agents through the full lifecycle of skill development: deciding whether a skill should exist, writing it with proven methodologies, evaluating it rigorously, reviewing it systematically, and packaging it for distribution.

It is based on [anthropics/skills](https://github.com/anthropics/skills) official skill-creator (Apache-2.0), extended with community best practices (SkillForge, oil-oil, qiaomu, Dazhuang, skillmark, skillbench, NVIDIA SkillSpector) and theory from [ai-agent-book](https://github.com/bojieli/ai-agent-book) and [ai-infra-book](https://github.com/bojieli/ai-infra-book).

---

## Design Philosophy

**Skill quality is behavioral, not aesthetic.** A skill is good when it reliably changes agent behavior for the better — not when it reads well.

Core principles:
- **Constraints over guidance**: What can be enforced mechanically should not be left to prose
- **Determinism in scripts**: Validation and computation live in `scripts/`, not bullet lists
- **Evidence over opinion**: "Looks good" is not evidence; require with/without behavioral delta
- **Thin routing, thick references**: SKILL.md routes; depth lives in `references/`
- **Falsifiability**: Every claim must be testable (RED GATE / GREEN GATE)

---

## Directory Structure

```
skill-creator/
├── SKILL.md                    # Entry point (~175 lines, thin routing)
├── LICENSE.txt                 # Apache-2.0
├── NOTICE.md                   # Provenance + third-party attributions
├── agents/                     # Sub-agent definitions
│   ├── grader.md               # 8-step eval scoring + first-error attribution
│   ├── comparator.md           # Blind A/B with position-swap dual scoring
│   ├── analyzer.md             # Post-hoc analysis + benchmark patterns
│   ├── skill-reviewer.md       # Structure + pitfall code review
│   ├── doc-verifier.md         # Documentation ↔ code parity
│   └── adversary.md            # Adversarial reviewer (refute-not-approve)
├── assets/
│   └── eval_review.html        # Eval query editor
├── eval-viewer/
│   ├── generate_review.py      # Interactive HTML review generator
│   └── viewer.html             # Dual-tab review UI
├── references/                 # Deep-dive documentation
│   ├── authoring.md            # Blueprint, failure-forms, description method
│   ├── eval-methodology.md     # RED/GREEN, holdout, Pass^k, ablations, pre-registration
│   ├── eval-failures.md        # 13 ways evals lie + audit checklist
│   ├── review-playbook.md      # 4 stages × 15 dimensions
│   ├── common-pitfalls.md      # 6 high-frequency pitfalls (customizable)
│   ├── security.md             # Lethal trifecta, action authorization, supply chain
│   ├── release.md              # Operating modes, gates, versioning, SkillOps
│   └── schemas.md              # JSON schema definitions
└── scripts/                    # Deterministic tools
    ├── quick_validate.py       # Frontmatter validation (uskill-aware)
    ├── package_skill.py        # Deterministic .skill ZIP packaging
    ├── snapshot_skill.py       # SHA-256 immutable baseline snapshots
    ├── score_triggers.py       # Hash-stratified holdout trigger scoring
    ├── run_skill_evals.py      # Shipped evals runner (static/live)
    ├── aggregate_benchmark.py  # Pass^k + Welch CI + noise floor
    ├── run_loop.py             # Description optimization loop
    ├── improve_description.py  # Claude-powered description rewriting
    ├── run_eval.py             # Trigger-rate evaluation
    ├── generate_report.py      # HTML iteration reports
    ├── doctor.py               # Ecosystem health checks
    └── utils.py                # Shared utilities
```

---

## Quick Start

### Install

```bash
ln -s /path/to/skill-creator ~/.claude/skills/skill-creator
```

### Use

In a new Claude Code session, say any of:

| Intent | Example phrase |
|--------|---------------|
| Create | "Create a skill that formats CSV files" |
| Improve | "Improve my ad_api skill" |
| Review | "Review the structure of this skill" |
| Evaluate | "Run evals on this skill" |
| Optimize | "Optimize the skill description for better triggering" |
| Package | "Package this skill as a .skill file" |
| Security | "Scan this skill for security issues" |

---

## Workflow

### Creating a Skill (7 Phases)

```
Phase 0: Should this exist?  ──→  Prior-art search, non-skill decision tree,
                                  product 9 questions, carrier decision
                                  STOP if not skill-suitable

Phase 1: RED GATE             ──→  Run task WITHOUT skill, document failures verbatim
                                  STOP if baseline doesn't fail

Phase 2: Write                ──→  Blueprint (5 steps), layer content,
                                  match failure-form to guidance form,
                                  description (triggers only)

Phase 3: Validate             ──→  quick_validate + py_compile + line count

Phase 4: GREEN GATE           ──→  Ship evals/ (triggers + scenarios),
                                  hash-stratified holdout, Pass^k,
                                  aggregate_benchmark (Welch CI + noise floor)
                                  STOP if baseline failures reproduce

Phase 5: Review               ──→  skill-reviewer → doc-verifier → adversary
                                  4 stages × 15 dimensions, P0 = block
                                  Stage 4 (e2e) is never delegated

Phase 6: Package & release    ──→  package_skill → snapshot
                                  Governed: + security scan + release gates
```

### Operating Modes

| Mode | When | Gates |
|------|------|-------|
| **Scaffold** | Personal experiment | quick_validate only |
| **Standard** | Default | RED/GREEN + evals + review |
| **Governed** | Team / public / production | + security + release gates + versioning |

---

## Key Innovations

### 1. RED GATE / GREEN GATE

Before writing any skill content, prove the baseline **fails** without it. Document failures verbatim. These become eval scenarios and description keywords.

After writing, prove the skill **fixes** those failures. With/without behavioral delta — not self-assessment.

### 2. Shipped Evals (Behavioral Tests)

Every skill ships with `evals/`:
- `triggers.json` — 3-tier trigger samples (positive / near_miss / holdout)
- `scenarios/*.md` — task + baseline_failure + assertions + runs

Skill quality is behavioral. Tests must ship with the artifact.

### 3. Hash-Stratified Holdout

Deterministic train/test split: `SHA256(skill_name:case_id)` sorted, ~40% per class to holdout. Train phase never reads baseline reports. Select phase uses holdout only. Anti-leakage by design.

### 4. Pass^k + Welch CI

- **Pass@k**: capability ceiling ("can it succeed?")
- **Pass^k**: reliability ("does it always succeed?")
- **Welch's t-interval**: 95% CI on A/B deltas
- **Noise-floor diagnosis**: why an eval can't resolve a lift

### 5. 4-Stage Review × 15 Dimensions

Structure scan → code pitfalls → doc↔code parity → end-to-end tests. Each dimension rated P0 (block) / P1 / P2. Evidence discipline: `missing evidence` over pretty words.

### 6. Adversarial Reviewer

A fresh agent charged to **refute** readiness, not approve it. Produces failure scenarios, rationalization loopholes, security concerns. "Your job is to disprove readiness."

### 7. Security Audit

- **Lethal trifecta**: private data + untrusted content + outbound comms
- **Action authorization taxonomy**: entailment ≠ permission (4 classes)
- **Supply-chain red flags**: unpinned deps, `curl|bash`, auto-update
- **Safe gate cannot be self-modified**

### 8. Pre-Registration & Report Classes

- **CONFIRMATORY**: registered + enough graded + harm controls
- **EXPLORATORY**: registration broken → per-task figures only, suppress average
- **VOID**: thin cells → explain why, no numbers

### 9. Eval Failure Modes

13 documented ways skill evals lie (answer-key leakage, loose matching, same-family judge, survivorship bias, etc.) with audit checklist.

### 10. Model-Era Rules

Modern model behaviors that change how skills should be written:
- Reasoning extraction refusal → ask for decisions, not thought process
- Compaction ~19,900 char gate → critical rules at top
- Hook-enforced always-on rules → prose only after trigger
- Fresh checker > self-review
- Too-prescriptive skills degrade output

---

## Script Reference

| Script | Purpose | Key features |
|--------|---------|-------------|
| `quick_validate.py` | Frontmatter validation | uskill fields, dir-name warning (not error), pyyaml-optional |
| `package_skill.py` | Create .skill ZIP | Deterministic (sorted, fixed timestamps), expanded excludes |
| `snapshot_skill.py` | Immutable baseline | SHA-256 tree digest, atomic write, verify mode |
| `score_triggers.py` | Trigger accuracy | Hash-stratified holdout, stability metric, dry-run |
| `run_skill_evals.py` | Run shipped evals | `--static` (CI-safe) / `--live` (model) |
| `aggregate_benchmark.py` | Benchmark stats | Pass^k, Welch CI, noise-floor diagnosis |
| `run_loop.py` | Description optimization | Train/test split, iterative improvement |
| `improve_description.py` | Rewrite description | Claude subprocess (no API key), extended thinking |
| `run_eval.py` | Trigger-rate eval | Temp command + stream-json detection |
| `generate_report.py` | HTML reports | Per-iteration pass/fail visualization |
| `doctor.py` | Ecosystem health | Trigger overlap, description budget, stale refs, token budget |

---

## Agent Reference

| Agent | Role | Mode |
|-------|------|------|
| `grader` | Grade assertions against transcripts | Read + write grading.json |
| `comparator` | Blind A/B with position-swap | Read-only |
| `analyzer` | Post-hoc unblinded analysis + benchmark patterns | Read-only |
| `skill-reviewer` | Structure scan + pitfall code review | Read-only |
| `doc-verifier` | Documentation ↔ code parity | Read-only |
| `adversary` | Refute readiness (not approve) | Read-only |

---

## Reference Files

| File | Load when |
|------|-----------|
| `authoring.md` | Writing/refactoring — blueprint, failure-forms, description method, carrier decision, model-era rules |
| `eval-methodology.md` | Running evals — RED/GREEN, holdout, Pass^k, ablations, pre-registration, trigger evals |
| `eval-failures.md` | Auditing evals — 13 failure modes + checklist |
| `review-playbook.md` | Reviewing — 4 stages × 15 dimensions, evidence discipline |
| `common-pitfalls.md` | Code review — 6 pitfalls (seed examples, customize) |
| `security.md` | Security audit — lethal trifecta, action authorization, supply chain |
| `release.md` | Releasing — operating modes, gates, versioning, SkillOps |
| `schemas.md` | JSON formats — evals, triggers, grading, benchmark, comparison |

---

## Core Concepts

### Carrier Decision

"Skill is not the default answer." Four dimensions decide:

| Dimension | Prefer Skill | Prefer other |
|-----------|-------------|-------------|
| Security | Low-risk | High-risk → dedicated tool |
| Param complexity | Simple | Complex → JSON file import |
| Change frequency | Stable | Changing → knowledge base |
| Model capability | Needs judgment | Deterministic → script |

### Failure-Form Matching

| Baseline failure | Right form | Wrong form |
|---|---|---|
| Rule skipped under pressure | Prohibition + rationalization table | Soft guidance |
| Output has wrong shape | Positive recipe | Prohibition list |
| Missing element | REQUIRED slot template | Prose reminders |
| Conditional behavior | Observable predicate rule | Unconditional + exemptions |

### Description Rules

1. **Trigger conditions first** — "Use when…"
2. **Third person** — injected into system prompt
3. **Symptom keywords** — words users actually type
4. **NEVER summarize workflow** — causes model to skip body
5. **Does NOT boundary** — prevent over-triggering
6. **Hard 1024 chars, soft 300** — pushy is fine

---

## Project History

| Date | Milestone |
|------|-----------|
| 2026-10-11 | Project initiated from internal prompt-alpha spec (9 screenshots) |
| 2026-10-12 | Baseline acquired (anthropics/skills) + 6 modules implemented |
| 2026-10-12 | Community research (3 parallel agents: ecosystem, eval tools, security/harness) |
| 2026-10-12 | Dazhuang research + creation-flow gap fixes |
| 2026-10-12 | A1–A10 research findings implemented (trigger evals, pre-registration, ablations, Welch CI, action authorization, model-era rules) |
| 2026-10-12 | Code review (2 rounds) + all issues fixed |
| 2026-10-12 | Restructured to `skill-creator/` + this documentation |

---

## Research Sources

**Baseline**: [anthropics/skills](https://github.com/anthropics/skills) (Apache-2.0)

**Community projects** (ideas, not code):
- [tripleyak/SkillForge](https://github.com/tripleyak/SkillForge) — RED/GREEN gates, shipped evals, failure-form table
- [oil-oil/oil-skill-creator](https://github.com/oil-oil/oil-skill-creator) — 15-dim review, hash-stratified holdout, snapshots
- [joeseesun/qiaomu-meta-skill](https://github.com/joeseesun/qiaomu-meta-skill) — operating modes, release gates, evidence discipline
- [DazhuangJammy/DazhuangSkill-Creator](https://github.com/DazhuangJammy/DazhuangSkill-Creator) — blueprint, section whitelist, eval pre-alignment
- [microsoft/waza](https://github.com/microsoft/waza) — spec verify, token budgets, grader registry
- [daymade/claude-code-skills](https://github.com/daymade/claude-code-skills) — collision detection, concurrent safety
- [yaniv-golan/skill-creator-plus](https://github.com/yaniv-golan/skill-creator-plus) — compaction mechanics, portability linter
- [rolling-codes/better-skill-creator](https://github.com/rolling-codes/better-skill-creator) — trigger-rate separation, action taxonomy
- [NVIDIA/SkillSpector](https://github.com/NVIDIA/SkillSpector) — vulnerability taxonomy, supply chain
- [NVIDIA/SkillEvaluator](https://github.com/NVIDIA/SkillEvaluator) — Skill Lift, process metrics, ATIF
- [adewale/skill-eval-harness](https://github.com/adewale/skill-eval-harness) — materialized ablations, noise floor
- [bharat-goel/nullbench](https://github.com/bharat-goel/nullbench) — pre-registration, report classes, FAILURES.md
- [TanbirRamim/skill-trigger-bench](https://github.com/TanbirRamim/skill-trigger-bench) — trigger evals, description budget
- [TiesPetersen/SkillBenchmark](https://github.com/TiesPetersen/SkillBenchmark) — blind judge, Welch CI
- [obra/superpowers](https://github.com/obra/superpowers) — Iron Law, Match-Form-to-Failure

**Theory**:
- [bojieli/ai-agent-book](https://github.com/bojieli/ai-agent-book) — Harness framing, Pass@k vs Pass^k, first-error attribution
- [bojieli/ai-infra-book](https://github.com/bojieli/ai-infra-book) — thin orchestration + thick references

---

## License

Apache-2.0. See `skill-creator/LICENSE.txt` and `skill-creator/NOTICE.md`.
