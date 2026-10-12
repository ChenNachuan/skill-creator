# 13 Ways Skill Evals Lie

A checklist for auditing any skill evaluation. If any of these apply, the numbers are unreliable. Adapted from nullbench FAILURES.md and cross-project findings.

---

## 1. Answer-key vocabulary leakage

**Symptom**: Assertions contain words that appear verbatim in SKILL.md.

**Why it lies**: The skill "passes" by echoing its own documentation, not by doing the work.

**Check**: For each assertion pattern, grep the SKILL.md. If it matches verbatim → not a valid assertion.

**Fix**: Rewrite assertions to check *outcomes*, not *wording*. "CSV has 12 rows" not "output mentions 'tabular data'".

---

## 2. Loose substring matching

**Symptom**: Assertions pass on `if "success" in output`.

**Why it lies**: Any output mentioning "success" or "not a success" passes.

**Fix**: Structured checks (JSON paths, file structure, exact values) over substring matching.

---

## 3. Judge and subject same model family

**Symptom**: Claude skill graded by Claude judge.

**Why it lies**: Same-family models share blind spots and stylistic preferences. Goodhart's Law in action.

**Fix**: Use cross-family judge when possible. At minimum, position-swap dual scoring and length-bias audit.

---

## 4. Judge misgrade rate

**Symptom**: Judge consistently misgrades known cases.

**Why it lies**: Systematic bias that no amount of averaging fixes.

**Fix**: Calibrate the judge against a hand-labeled gold set. Report the judge's error rate alongside results.

---

## 5. Control-arm contamination

**Symptom**: "Without skill" arm sees skill artifacts via shared cwd, environment, or conversation history.

**Why it lies**: Baseline isn't actually baseline.

**Fix**: Fresh temp directory per arm. No shared state. Clean environment variables.

---

## 6. Circular trigger prompts

**Symptom**: Test query contains the skill name or unique description keywords.

**Why it lies**: Trivially triggers the skill — tests nothing about real-world activation.

**Fix**: Trigger queries must be natural user phrasing that does NOT contain skill name or description text.

---

## 7. Small-sample inflation

**Symptom**: "100% improvement!" on n=2.

**Why it lies**: No statistical power. One lucky run looks like a breakthrough.

**Fix**: Wilson/Newcombe CIs mandatory. Report n prominently. Suppress averages with n<3 discriminating tasks.

---

## 8. Both-arms-always-pass tasks counted

**Symptom**: 9/10 tasks pass with AND without the skill.

**Why it lies**: 9 of those "passes" are noise. The average is inflated by non-discriminating tasks.

**Fix**: Label saturated tasks (both always pass) and floor tasks (both always fail). Exclude from mean. If <2 tasks discriminate, suppress the average.

---

## 9. No harm controls

**Symptom**: No negative-control tasks (things the skill should NOT do).

**Why it lies**: The cheapest way for a skill to "pass" is to fire on everything.

**Fix**: Mandatory negative-control tasks for any CONFIRMATORY claim. Irrelevant-skill placebo arm ≈ 0pp.

---

## 10. LLM self-grading hallucination

**Symptom**: LLM judge "measures" metrics it cannot actually see (accuracy, completeness scores it invented).

**Why it lies**: The metric is fiction. Identical outputs get different scores by side.

**Fix**: Deterministic oracle first (assertions, scripts, file checks). LLM judge only for subjective dimensions. Documented finding: LLM self-grading invents metrics and grades identical outputs differently.

---

## 11. Missing CIs on deltas

**Symptom**: "73% vs 70%" printed without intervals.

**Why it lies**: The reader cannot distinguish signal from noise. n=100 at 73% vs 70% has a CI that includes zero.

**Fix**: Wilson CI per arm + Newcombe CI on delta. Never print bare point estimates.

---

## 12. Post-hoc registration

**Symptom**: "Evaluation plan" written after seeing results.

**Why it lies**: Confirmation bias dressed as rigor. You cherry-picked what to measure.

**Fix**: Pre-register tasks, reps, and predictions BEFORE running. Report class = EXPLORATORY if registration was broken.

---

## 13. Void runs excluded

**Symptom**: Failed/incomplete runs silently dropped from the report.

**Why it lies**: Survivorship bias. Only the runs that worked are counted.

**Fix**: Append-only ledger. Every run including voided/flat ones. Void class means "we ran it, it didn't resolve" not "we didn't run it."

---

## Quick audit

Before trusting any skill eval number, check:

- [ ] No answer-key vocabulary in SKILL.md matching assertions
- [ ] Assertions check outcomes, not substrings
- [ ] Judge ≠ same model family as subject (or position-swapped)
- [ ] Judge calibrated against gold set
- [ ] Control arm in fresh, isolated environment
- [ ] Trigger queries don't contain skill name/description
- [ ] n ≥ 3 discriminating tasks
- [ ] Non-discriminating tasks excluded from mean
- [ ] Harm/negative-control tasks present
- [ ] Deterministic oracle preferred over LLM self-grading
- [ ] CIs on all deltas
- [ ] Pre-registered before running
- [ ] All runs (including void) in ledger
