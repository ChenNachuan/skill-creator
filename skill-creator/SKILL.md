---
name: skill-creator
description: >-
  Creates, edits, evaluates, reviews, and packages Claude Code skills. Use when
  the user wants to build a skill from scratch, improve or refactor an existing
  skill, decide whether a task should become a skill at all, run evals or
  benchmarks to measure skill performance, optimize a skill description for more
  reliable triggering, run a structured multi-stage skill review (structure,
  code pitfalls, documentation parity, end-to-end tests), blind-compare two
  skill outputs, scan a skill for security issues, or package a skill as a
  .skill ZIP. Does NOT handle free-form prompt engineering with no skill
  artifact, installing skills into ~/.claude/skills, runtime skill
  marketplaces, or non-Claude agent frameworks.
metadata:
  uskill.icon: "🧩"
  uskill.category: developer
  uskill.display_name: Skill Creator
  uskill.display_desc: Create, test, review, and package Claude Code skills
---

# Skill Creator

## Hard rules

1. **RED GATE before writing**: baseline must FAIL without the skill. If it doesn't, don't build.
2. **No claim without evidence**: write `missing evidence` — never fill gaps with pretty words.
3. **Reports never auto-edit a skill**: present findings; edit only on explicit user request.
4. **Description never summarizes workflow**: triggers only. Workflow summaries cause the model to skip the body.
5. **Determinism in scripts, not prose**: validation/computation goes in `scripts/`, not in bullet lists.
6. **Skill quality is behavioral**: "looks good" is not evidence. Require with/without delta.

## When to use / When NOT

**Use**: create skill · improve skill · decide if skill is the right carrier · run evals/benchmark · optimize description · structured review · blind A/B · security scan · package `.skill`.

**NOT**: free-form prompt engineering with no skill artifact · installing into `~/.claude/skills` · skill marketplaces · non-Claude agent frameworks.

## Workflow router

| User intent | Run phases | Skip |
|---|---|---|
| Create new skill | 0→1→2→3→4→5→6 | — |
| Improve existing | snapshot → 1→2→3→4→5→6 | 0 |
| Review/audit only | 5 | 0–4, 6 |
| Run evals only | 4 | others |
| Optimize description | Optimize section | 0–3, 5–6 |
| Package only | 3→6 | others |

## Operating modes

| Mode | When | Gates |
|---|---|---|
| **Scaffold** | Personal experiment | quick_validate only |
| **Standard** | Default | RED/GREEN + evals + review |
| **Governed** | Team / public / production | + security + release gates + versioning |

Confirm mode with user before starting. Default to Standard.

## State broadcast (anti-drift)

Before every branch switch or heavy operation, restate:
- **Path**: create | improve | review | eval | package
- **Step**: which phase are we in
- **Next**: one sentence — what happens next

If conversation drifts, context gets long, or goal changes → return to Workflow router and re-route. Don't continue on inertia.

---

## Create a skill

### Phase 0 — Should this exist?

- [ ] Prior-art search: is there an existing skill to improve instead?
- [ ] Non-skill decision tree: one-off → no skill; unstable rules → no skill; heavy real-time judgment → no skill
- [ ] Product 9 questions (see `references/authoring.md`): user / problem / pain / measurable improvement / input / output / boundary / risk / type
- [ ] Carrier decision: skill vs tool vs knowledge vs program (see `references/authoring.md`)

**STOP** if an existing skill covers this (improve instead) or if the task is not skill-suitable.

### Phase 1 — RED GATE

- [ ] Run target task with fresh agent **without** the skill
- [ ] Document failures **verbatim** (exact wording, rationalizations, errors)
- [ ] These become eval scenarios + description keywords

**STOP** if baseline does not fail. Do not build the skill.

### Phase 2 — Write

- [ ] Blueprint: judge goal / trigger / output / boundary / effort (see `references/authoring.md`)
- [ ] Layer content: body (rules+flow) / references (depth) / scripts (determinism)
- [ ] Match failure-form to guidance form (see `references/authoring.md`)
- [ ] Description: triggers only, third person, "Use when…", "Does NOT…", ≤1024 chars

**Depth**: `references/authoring.md`

### Phase 3 — Validate

- [ ] `python3 -m scripts.quick_validate .`
- [ ] `python3 -m py_compile scripts/*.py`
- [ ] Body ≤300 lines (target ~230); no orphan references

### Phase 4 — GREEN GATE

- [ ] Ship `evals/triggers.json` (positive + near_miss + holdout)
- [ ] Ship `evals/scenarios/*.md` (task / baseline_failure / assertions / runs)
- [ ] Run `python3 -m scripts.run_skill_evals <skill> --static`
- [ ] Run `python3 -m scripts.score_triggers --eval-set evals/triggers.json --skill-path <skill> --dry-run` (check split)
- [ ] With/without delta: no baseline failure reproduces (Pass^k ≥3 runs)
- [ ] `python3 -m scripts.aggregate_benchmark <workspace>` — Pass^k + Welch CI + noise floor

**Depth**: `references/eval-methodology.md`

### Phase 5 — Review

- [ ] Stage 1–2: `skill-reviewer` agent (structure + pitfalls)
- [ ] Stage 3: `doc-verifier` agent (doc↔code parity)
- [ ] Stage 4: end-to-end tests (main flow, never delegated)
- [ ] Adversarial pass: `adversary` agent (refute readiness)
- [ ] P0 findings = block release

**Depth**: `references/review-playbook.md`

### Phase 6 — Package & release

- [ ] `python3 -m scripts.package_skill <skill_dir> [output_dir]`
- [ ] Scaffold: done here
- [ ] Standard: + snapshot for future diffs
- [ ] Governed: + security scan + release gates + versioning (see `references/release.md`)
- [ ] Multi-skill ecosystem: `python3 -m scripts.doctor <skills_dir>` (trigger overlap, budget, stale refs)

**Depth**: `references/release.md`, `references/security.md`

---

## Improve an existing skill

1. **Snapshot** first: `python3 -m scripts.snapshot_skill snapshot <skill> <workspace>` (immutable baseline)
2. Run RED GATE on the specific problem area (what fails with current skill?)
3. Make minimal changes (diff-driven; each change addresses a documented failure)
4. GREEN GATE: run evals, verify delta, blind-compare old vs new (`comparator` + `analyzer` agents)
5. Iterate until no new failures

---

## Optimize a description

- [ ] Build `evals/triggers.json` (~20 queries: 8-10 positive + 8-10 near_miss)
- [ ] Run `python3 -m scripts.run_loop --eval-set evals/triggers.json --skill-path <skill>`
- [ ] Train/test split is handled by the script (stratified 60/40)
- [ ] Best description selected by **test** score (not train)
- [ ] `python3 -m scripts.generate_report <workspace>` — per-iteration HTML report
- [ ] Verify with 5-10 fresh queries after optimization (honest re-check)

---

## Reference files

| File | Load when |
|------|-----------|
| `references/authoring.md` | Writing/refactoring a skill — blueprint, failure-forms, description method, carrier decision |
| `references/eval-methodology.md` | Running evals — RED/GREEN, holdout, Pass^k, ablations, trigger evals, statistics |
| `references/eval-failures.md` | Auditing evals — 13 failure modes that make numbers unreliable |
| `references/review-playbook.md` | Reviewing a skill — 4 stages × 15 dimensions, evidence discipline |
| `references/common-pitfalls.md` | Code review — 6 high-frequency pitfalls (seed examples, customize) |
| `references/security.md` | Security audit — lethal trifecta, action authorization, supply chain |
| `references/release.md` | Releasing — operating modes, gates, versioning, SkillOps |
| `references/schemas.md` | JSON formats — evals, triggers, grading, benchmark, comparison |

---

## Provenance

Based on [anthropics/skills](https://github.com/anthropics/skills) skill-creator (Apache-2.0). See `NOTICE.md` for modifications and third-party ideas incorporated.
