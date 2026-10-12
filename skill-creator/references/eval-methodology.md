# Eval Methodology — RED/GREEN Gates, Holdout, Reliability

How to prove a skill works: baseline failure → shipped evals → hash-stratified holdout → reliability metrics.

---

## 0. Eval Pre-Alignment (before ANY evaluation)

**Hard rule**: The first response to any eval/assessment request MUST stop at a proposal. No scoring, no "who's better", no with-vs-without before the user confirms.

### Step 1: Skill typing (判型)

| Type | Description | Eval focus |
|------|-------------|------------|
| **Delivery-effect** (default) | Does the skill produce correct outcomes? | Pass/fail assertions, behavioral delta |
| **Imitation-restoration** | Does it mimic a persona/style/method? | Tone, expression, thinking framework, decision style |
| **Mixed** | Primary + secondary with explicit weights | Both, with declared weights |

### Step 2: AI initial judgment (6 fixed fields)

1. What this skill is
2. Primary direction (delivery / imitation / mixed)
3. Secondary direction (if mixed)
4. Reasoning for the judgment
5. Easy-to-misjudge aspects
6. Suggested next step for alignment

### Step 3: Evaluation proposal (8 sections)

1. What this skill is
2. **Recommended** primary eval direction + why
3. **Alternative directions** (must show, not hide)
4. Possible mainstream directions (with weights if mixed)
5. Comparison mode (single / with-vs-without / A vs B / A vs B vs C)
6. 3–5 dimensions + what each measures + what is explicitly **out of scope**
7. Test case plan (real cases, sample types/count, false-positive traps)
8. Decisions the user must make (which kind of "good"? what's out of scope? weights?)

### Step 4: Alignment script (say exactly this)

1. "I initially think it should be evaluated as…"
2. "Besides that, it could also be evaluated as…"
3. "This time, which one do you want me to use?"

### Step 5: Formal plan (after user sign-off)

Lock: object / directions+weights / dimensions / explicit non-scope / case plan / comparison controls (same model/env/budget/time, blind?) / conclusion requirements.

**Only explicit user sign-off unlocks execution.** Once signed off, must run to completion.

---

## 0.5 Pre-Registration & Report Classes

Before running ANY evaluation, **pre-register**: declare tasks, repetitions, and per-task predictions. Reports state whether they measured what was registered.

### Three report classes

| Class | Condition | What prints |
|-------|-----------|-------------|
| **CONFIRMATORY** | Registered + enough graded + harm controls present | Full results with CIs |
| **EXPLORATORY** | Registration broken or missing | Per-task figures only — **suppress the average** |
| **VOID** | Thin cells / no discrimination | Nothing quantitative; explain why |

### Mandatory elements

- **Harm/negative-control tasks** required for CONFIRMATORY — without a negative control, the cheapest way for any skill to pass is "fire on everything"
- **Non-discriminating tasks**: tasks where both arms pass are labeled and excluded from the mean; suppress average if <2 tasks discriminate
- **Answer-key preflight**: every assertion pattern cross-checked against SKILL.md; verbatim match **blocks CONFIRMATORY** (catches skill-diction graders)
- **Placebo + known-positive bracket**: irrelevant-skill arm ≈ 0pp; known-good skill ≈ 100pp. A harness that always reports null passes placebo — need both arms.
- **Wilson CI** (per arm) + **Newcombe CI** (delta) at 95% mandatory — never print bare point estimates

### Failure modes to check (from nullbench FAILURES.md)

1. Answer-key vocabulary leakage into SKILL.md
2. Loose substring matching
3. Judge and subject from same model family
4. Judge misgrade rate > acceptable
5. Control-arm contamination via shared cwd
6. Circular trigger prompts (query contains skill name)
7. Small-sample inflation
8. Both-arms-always-pass tasks counted as wins
9. No harm controls
10. LLM self-grading hallucinating metrics
11. Missing CIs on deltas
12. Registration declared after seeing results
13. Void runs excluded from ledger

---

## 0.6 Trigger Evaluation (separate surface)

Trigger quality and task quality are **different failure modes**. Evaluate separately.

| Metric | What it measures | Target |
|--------|-----------------|--------|
| **Trigger rate** | % of should-trigger queries that activate | ≥80% |
| **False-trigger rate** | % of should-NOT-trigger queries that activate | ≤10% |
| **Near-miss accuracy** | % of adjacent-skill queries correctly rejected | ≥80% |
| **Stability** | max(rate, 1-rate) per query | ≥0.8 |

### 8 trigger failure modes

| # | Mode | Fix |
|---|------|-----|
| P1 | **Shy description** — too conservative | Expand trigger vocabulary |
| P2 | **Implementation-speak** — describes how, not when | Rewrite to "Use when…" |
| P3 | **Vocabulary gap** — user words missing | Add user's actual phrasing |
| P4 | **Implicit domain** — domain assumed, not stated | Name the domain explicitly |
| P5 | **Budget cut** — description truncated | Prioritize trigger phrases first |
| P6 | **No boundary** — no "Does NOT" | Add explicit boundary |
| P7 | **Broad nouns** — over-triggers on common words | Narrow to specific symptoms |
| P8 | **Hijack risk** — description attracts unrelated queries | Tighten "Does NOT" |

### Discipline

- Trigger evals run on **fresh temp projects** with only chosen skills installed
- Multi-run (≥3) per query; report trigger_rate not yes/no
- Test **with neighbors installed** (`--with other-skill`) for collision detection
- Cross-model: descriptions trigger differently across models — record routing behavior per model

---

## 1. RED GATE / GREEN GATE

### RED GATE (prove necessity)

Before writing ANY skill content:

1. Run the target task with a fresh agent **without** the skill
2. Document failures **verbatim** — exact wording of wrong actions, rationalizations, errors
3. **STOP if baseline does not fail**: if the agent already does it right, don't build a skill

The baseline failures become:
- Eval scenario descriptions (`baseline_failure` field)
- Description trigger keywords (symptom vocabulary)
- Assertion sources (what the skill must fix)

### GREEN GATE (prove efficacy)

After writing the skill:

1. Re-run the same scenarios WITH the skill
2. Verify: **no baseline failure reproduces**
3. For discipline-enforcing skills: run ≥3 times under pressure (time constraints, competing priorities)

---

## 2. Three-Tier Trigger Samples

| Tier | Purpose | Count |
|------|---------|-------|
| **positive** | Queries that MUST trigger | 8–10 |
| **near_miss** | Adjacent-skill confusion (harder than plain negatives) | 8–10 |
| **holdout** | Reserved for unbiased final scoring | Subset via hash split |

Near-miss examples for a skill-creator:
- "Help me write a Python script to parse JSON" (programming, not skill creation)
- "Review this pull request" (code review, not skill review)
- "What's the best way to structure a project?" (general question)

---

## 3. Hash-Stratified Holdout

Deterministic, anti-leakage train/test split:

```
For each case: hash = SHA256(skill_name + ":" + case_id)
Sort by hash within each class (positive / near_miss / holdout)
Take top ~40% as holdout per class
```

**Critical discipline**:
- **Train phase MUST NOT read baseline reports** (structural anti-leakage)
- **Select phase compares on holdout only**
- Report pins `description_sha256` + `eval_set_sha256` (anti-tampering)

---

## 4. Stability Metric

For each eval case with k runs:

```
trigger_rate = (times triggered) / k
stability = max(trigger_rate, 1 - trigger_rate)
```

- `stability = 1.0` means perfectly consistent (all runs agree)
- `stability = 0.5` means random (equivalent to coin flip)
- Strict mode: ≥3 odd-count trials; pass = trigger_rate ≥ 0.5

---

## 5. Pass^k (Reliability)

| Metric | What it measures | Formula |
|--------|-----------------|---------|
| **Pass@k** | Capability ceiling ("can it succeed?") | 1 - (1-p)^k |
| **Pass^k** | Reliability ("does it always succeed?") | p^k (all k runs pass) |

p=0.6: Pass@5 ≈ 99%, Pass^5 ≈ 7.8%. **Report both.**

A skill with 70% single-run pass rate is NOT a 70% reliable skill if Pass^3 = 34%.

---

## 6. Paired Significance Testing

For A/B comparison (skill vs no-skill, old vs new):

- **McNemar's test** for paired binary outcomes (same eval, two conditions)
- **Paired bootstrap** for continuous metrics (time, tokens)
- Report 95% CI; use 3–5 random seeds and report mean ± stddev
- **"73% vs 70%" on n=100 is often NOT significant** — the CI typically includes zero

---

## 7. Judge Reliability

When using LLM judges (grader, comparator):

| Bias | Mitigation |
|------|------------|
| **Position bias** | Score A/B then B/A; inconsistency → TIE |
| **Length bias** | Penalize verbosity; align lengths before comparing; audit score-vs-length correlation |
| **Same-family bias** | Agent and judge from same model family can collude; use cross-family judge |
| **Self-approval** | Never have the skill author grade their own work; use fresh adversarial reviewer |

**Rubric with Veto**: When using rubrics, add a Veto criterion — if triggered (e.g., hallucination), automatic fail regardless of other scores.

---

## 8. Failure Attribution

When expectations fail, locate the **first divergent error** (later errors are cascading):

1. Walk the transcript chronologically
2. Find the earliest step where output diverged from expected
3. Classify into one of: `wrong_tool` / `wrong_input` / `wrong_interpretation` / `missing_step` / `premature_stop` / `hallucination` / `constraint_violation` / `error_propagation` / `other`
4. Record in `grading.json` under `first_error` (step, category, evidence, cascade_effects, confidence)

---

## 9. Evidence Discipline

| Rule | Application |
|------|-------------|
| Missing evidence → write `missing evidence` | Never fill gaps with pretty words |
| `recorded_fixture` ≠ `live evidence` | Cached recordings don't prove live behavior |
| Blind review = 3-tuple | reviewer + decision + reason + "judged before reveal" |
| "Looks good" is not evidence | Require behavioral delta (with vs without) |

---

## 10. Materialized Ablations (which part is load-bearing?)

Beyond with/without, test **which specific instruction/script/checklist matters**:

```
ablation: remove-rule-3     → run evals → measure delta
ablation: remove-script-x   → run evals → measure delta
ablation: remove-example-2  → run evals → measure delta
```

Each ablation declares `expected_regressions` before running. If removing a part produces NO regression, that part is dead weight — candidate for deletion.

### Noise-floor diagnosis

When an eval cannot resolve a lift, say **why** (not just "n.s."):

| Verdict | Meaning |
|---------|---------|
| `too_few_cases_moved` | Not enough tasks changed between arms |
| `noise_floor_above_headroom` | Variance swamps the signal |
| `above_min_lift` | Effect is real but below threshold |

Lift CI via sign-flip test inversion; report 95% interval.

### Trajectory diff (behavioral evidence)

Alongside pass rates, compare **how arms behaved**:

| Metric | What it shows |
|--------|---------------|
| Commands exclusive to one arm | Different strategies |
| Event-count deltas (steps/tool calls/file ops) | Efficiency difference |
| Skill-load rates per arm | Was the skill actually used? |

Pairs with empty/unreadable traces are blocked, not silently passed.

---

## 11. Methodology Notes

### Deterministic-oracle preference

Prefer deterministic grading (assertions, scripts, file checks) over LLM self-grading. LLM judges hallucinate metrics and grade identical outputs differently by side. Use LLM judges only for subjective dimensions, with position-swap and Veto.

### Robustness perturbation

Inject failures during eval: `tool_failure`, `ambiguous_instructions`, `missing_fields`. Verify the skill handles gracefully.

### Multi-model adapter

When deploying across models: use mock (verify delta logic), Claude CLI, Anthropic API, OpenAI API adapters. Compare Pass^k across models.

### Concept coverage (knowledge skills)

For reference/knowledge skills, use `matchedConcepts/totalConcepts` instead of binary assertions. Three-level matching: substring → fuzzy word-level (≥0.80) → auto-variants (hyphens, plurals). Pass threshold ≥70%.
