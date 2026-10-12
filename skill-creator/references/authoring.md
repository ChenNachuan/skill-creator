# Authoring Guide — How to Write Skills

Methods for writing high-quality skills: the blueprint, failure-form matching, description methodology, carrier decision, and layering discipline.

---

## 0. Should This Be a Skill? (Entry Gate)

### Non-skill decision tree

```
Is this a one-off task?
  → YES: Don't create a skill. Just do it.
Are the rules stable (won't change next week)?
  → NO: Use a config file or knowledge base, not a skill.
Does this require heavy real-time judgment with no fixed procedure?
  → YES: Don't create a skill. Judgment without procedure is a model-params problem.
Does an existing skill cover this?
  → YES: Improve that skill instead. Don't fork.
Is the output objectively verifiable (files, data, code)?
  → NO (pure style/taste): Consider if skill is the right carrier at all.
Otherwise: Proceed to product questions.
```

### Product 9 questions

Before writing ANY content, answer these. If you can't answer 7+, the skill isn't ready to build.

| # | Question | Decides |
|---|----------|---------|
| 1 | **User** | Who specifically will use this? |
| 2 | **Problem** | What concrete problem does it solve? |
| 3 | **Pain** | What's the current pain (time, errors, inconsistency)? |
| 4 | **Measurable improvement** | How will we know it worked? (metric) |
| 5 | **Input** | What does the user provide? |
| 6 | **Output** | What artifact/behavior comes out? |
| 7 | **Boundary** | What does this skill NOT do? |
| 8 | **Risk** | What could go wrong? (security, data loss, wrong output) |
| 9 | **Type** | Delivery-effect / imitation / mixed? |

### Carrier decision (quick)

| Question | If YES → |
|----------|---------|
| Needs contextual judgment? | → **Skill** |
| High-risk / complex params / sandbox needed? | → **Dedicated tool** |
| Pure facts and exceptions? | → **Knowledge base** |
| Deterministic, verifiable? | → **Script/program** |
| Style, tone, high-dimensional? | → **Model params** |

"Skill is not the default answer." Full matrix in §5 below.

### RED GATE failure recording template

When running baseline (Phase 1), record each failure in this format:

```markdown
## Failure N: [short title]
- **Step**: [where in the transcript it diverged]
- **What the agent did**: [verbatim quote or exact action]
- **What it should have done**: [correct behavior]
- **Rationalization** (if any): [exact words the agent used to justify]
- **Category**: wrong_tool / wrong_input / wrong_interpretation / missing_step / premature_stop / hallucination / constraint_violation / error_propagation
```

These become:
1. `evals/scenarios/*.md` → `baseline_failure` field
2. Description trigger keywords (symptom vocabulary)
3. Assertion sources (what the skill must fix)

---

## 1. The Blueprint (5 Steps)

Used for both new skills and refactoring existing ones.

### Step 1: Judge the fundamentals

| Question | What it decides |
|----------|-----------------|
| **Goal** | What observable outcome should improve? |
| **Trigger** | When should the model load this skill? |
| **Output** | What artifact/behavior does the skill produce? |
| **Boundary** | What does the skill NOT do? |
| **Effort** | How heavy is the process? (T1–T4 below) |

### Step 2: Layer the content

Map each piece of content to its layer:

| Content type | Goes to |
|---|---|
| Trigger conditions, main flow, output constraints | `SKILL.md` body |
| Long procedures, examples, evaluation criteria | `references/*.md` |
| Deterministic logic (validation, computation, I/O) | `scripts/*.py` |
| Test cases, trigger evaluations | `evals/` |
| Generated artifacts, templates | `assets/` |

### Step 3: Minimal body

The body carries only:
- Hard rules (constraints the model must not forget)
- Phase checkboxes with stop conditions
- Routing (which reference to load when)
- The reference index

Everything explanatory sinks to references.

### Step 4: Optional index

For skills with >3 references, add a `## Reference files` section with one line per file: path + "load when …".

### Step 5: Structure check

Run `python3 -m scripts.quick_validate .` and verify body line count.

---

## 2. Section Whitelist (Single-File Skills)

Allowed sections in a single-file SKILL.md body (closed set — unknown sections are errors):

| Section | Required? | Purpose |
|---------|-----------|---------|
| Overview | optional | What this is (2–3 sentences) |
| Rules | **required** | Hard constraints (bullet list) |
| Workflow | **required** | Step-by-step process (checkboxes) |
| Examples | optional | Model-facing canonical cases (sink if >3) |
| Output format | optional | Model-followed template (sink if complex) |
| Index | optional | Reference file pointers (recovery only, not a second workflow) |

### When to add optional sections (gating questions)

Each optional section must **earn its place**:

| Section | Add only if… |
|---------|-------------|
| **Overview** | The skill needs a 2–3 sentence "what is this" beyond the description |
| **Examples** | High-cost boundaries repeatedly misfire without a pinned canonical case. `# Examples` = **model-facing internal reference**, NOT user-facing prompt examples (those belong in description). |
| **Output format** | Output structure must be stable. `# Output format` = **model-followed template/skeleton**, NOT explanation of "how I will output." |
| **Index** | ≥2 of: 2+ path branches, 3+ resource pointers, long tool output / multi-turn / batch runs, environment branches, body already not a short single-path note. Index is **recovery only** — never a second workflow. |

**Sinking map** (enforce strictly):
- Examples >3 → `references/examples.md` (if `references/` exists, inline Examples is FORBIDDEN)
- Output format → `assets/output-format.md` (if `assets/` exists, inline Output format is FORBIDDEN)
- Long explanations → expand the relevant reference
- Inline Examples/Output format each ≤18 non-empty lines (combined ≤30)

### `<skill-base>` convention

If ANY bundled resources exist (`references/`, `assets/`, `scripts/`, `agents/`, `evals/`), SKILL.md MUST define:

> "Treat the directory containing this SKILL.md as `<skill-base>`."

All path references use `<skill-base>/references/...`, `<skill-base>/scripts/...` — never absolute paths. This is runtime semantics, not style.

### Creator vs. target responsibility

Architecture rules (whitelist, sink thresholds, naming, packaging validation) stay in **this skill-creator** — do NOT copy them into every target skill. Target skills keep only the minimal structural rules that actually affect their execution.

### Minimal-output skills

For skills that produce minimal output (e.g., commit messages, short labels):
1. Rule says "default output only X"
2. Workflow defines a **closed set** of expansion conditions (breaking change / migration notes / explicit user request — NOT "helpful extra")
3. Final check deletes leftover body/explanations
4. Pin high-cost boundaries with at most 1 short canonical example

---

## 3. Failure-Form Table

Match the guidance form to the failure type. Wrong form backfires.

| Baseline failure | Right form | Wrong form |
|---|---|---|
| Rule skipped under pressure | Prohibition + rationalization table + red flags | Soft guidance ("prefer...", "consider...") |
| Output has wrong shape | Positive recipe or contract: state what the output IS | Prohibition list ("don't restate") |
| Missing required element | REQUIRED slot in the template they fill in | Prose reminders near the template |
| Behavior depends on a condition | Conditional keyed to observable predicate | Unconditional rule + exemptions |

**No nuance clauses**: "Don't X unless it matters" reopens the negotiation. Express exceptions as separate conditionals on observable predicates.

**Exemption clauses don't scope**: "This limit doesn't apply to code blocks" still suppresses code blocks. Restructure so the rule can't reach exempt content.

---

## 4. Description Methodology

The description is the **only** trigger surface. The body loads only after the model decides to read the skill.

### Rules

1. **Trigger conditions first**: Start with "Use when…" or "Creates/evaluates/… Use when…"
2. **Third person**: "This skill should be used when…" (injected into system prompt)
3. **Symptom keywords**: Words the user would actually type (error messages, synonyms, tool names)
4. **NEVER summarize workflow**: A description that says "does X then Y" causes the model to follow the summary and skip the body
5. **Does NOT boundary**: Explicit "Does NOT handle…" to prevent over-triggering
6. **Hard limit 1024 chars; soft target 300**. "Pushy" is fine — be direct about when to use.

### Example

```yaml
# BAD — summarizes workflow
description: Creates skills by interviewing the user, writing SKILL.md, running evals, and optimizing the description.

# GOOD — triggers only
description: >-
  Creates, evaluates, and reviews Claude Code skills. Use when the user wants
  to build a skill from scratch, improve an existing skill, run evals or
  benchmarks, optimize a skill description for triggering, or package a skill.
  Does NOT handle free-form prompt engineering or non-Claude frameworks.
```

---

## 5. Carrier Decision (Skill vs. Other)

"Skill is not the default answer." Four dimensions decide the right carrier:

| Dimension | Prefer Skill | Prefer other carrier |
|-----------|-------------|---------------------|
| **Security** | Low-risk, no credentials | High-risk: dedicated tool with sandbox |
| **Param complexity** | Simple/few params | Complex structured params: JSON file import or dedicated tool |
| **Change frequency** | Stable rules | Frequently changing: knowledge base or config |
| **Model capability** | Needs judgment/context | Deterministic: script or program |

| Carrier | When |
|---------|------|
| **Skill** | Needs contextual judgment; reusable across sessions |
| **Dedicated tool** | High-risk, complex params, needs sandboxing |
| **Knowledge base** | Facts and exceptions (not instructions) |
| **Program / script** | Verifiable hard constraints; deterministic |
| **Model params** | Style, tone, high-dimensional perception |

---

## 6. Layering & Token Budget

### Three-level loading

| Level | What | Cost | Loaded when |
|-------|------|------|-------------|
| L1 | `name` + `description` | ~50–100 tokens | Always (system prompt) |
| L2 | Body | 200–2000 tokens | When skill triggers |
| L3 | `references/*.md` | Variable | On demand |

### Rules

- **No duplication**: Information lives in exactly one place. If it's in a reference, don't repeat it in the body.
- **Weak-model readability**: Each rule stated once, in the most relevant place. Don't scatter.
- **Body <500 lines** (target 200–300). If over, sink content.
- **Scripts don't enter context** unless invoked — keep deterministic logic in scripts.

---

## 7. Complexity Tiers (T1–T4)

| Tier | Description | Process weight |
|------|-------------|---------------|
| **T1 Minimal** | Single SKILL.md, no scripts | Scaffold mode; skip RED GATE |
| **T2 Workflow** | SKILL.md + scripts + references | Standard mode |
| **T3 Multi-skill** | Orchestrator + sub-skills | Standard + cross-skill consistency review |
| **T4 Ecosystem** | Agents, hooks, multiple interdependent skills | Governed mode; full gates |

---

## 8. Function Decomposition (T3/T4 only)

For complex, long-lived skills:

1. **`functions/*.md`**: Each file is one function contract (explicit I/O, prefer pure functions)
2. **SKILL.md**: Orchestration only — the pipeline composition
3. **Trace logs**: Record input/output/tokens/duration per step to `logs/runs/*.jsonl`
4. **Trace → testcase export**: Failed traces become regression cases in `evals/`

Layer discipline: judgments in functions, rules in references, determinism in scripts, regression behaviors in evals.

---

## 9. Model-Era Rules (2026+)

New constraints discovered from modern model behavior (Fable 5, Opus 5.5, Sonnet 5.5):

### Reasoning extraction refusal

Do NOT ask models to "write out their reasoning" or "show your thought process." Modern models are trained to refuse or paraphrase rather than emit true reasoning. Instead, ask for **decisions and evidence**: "What did you conclude and why?" not "What were you thinking?"

### Compaction-aware placement

Content is truncated at ~19,900 **characters** (not tokens) during compaction. Critical rules go at the **top** of the body — content after the truncation point is lost silently. Cross-skill combined budgets can zero a skill entirely with no marker.

### Hook-enforced always-on rules

If a rule must run on EVERY invocation (not just when the skill loads), put it in a **hook**, not in skill prose. Prose is only read after the skill triggers.

### Fresh checker > self-review

When verifying skill quality, a **fresh agent** (no prior context) is more reliable than self-review. The skill author will rationalize their own work.

### Too-prescriptive skills degrade output

Over-constrained skills make modern models produce worse results. Prefer **default patterns with escape hatches** over rigid step-by-step mandates. "Do X unless condition Y" beats "Always do X."

### Give the reason, not just the request

When instructing the model, include **why** the rule exists. Models follow reasoned instructions more reliably than bare commands.

---

## Quick Checklist

- [ ] Carrier decision: is a skill the right answer?
- [ ] Prior-art checked: no existing skill covers this
- [ ] RED GATE: baseline fails without the skill
- [ ] Blueprint: goal/trigger/output/boundary/effort decided
- [ ] Failure-form matched to actual failure type
- [ ] Description: triggers only, no workflow summary
- [ ] Layering: body <500 lines, no duplication
- [ ] GREEN GATE: evals pass with the skill
