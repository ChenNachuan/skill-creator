# NOTICE

## Provenance

This skill is based on [anthropics/skills](https://github.com/anthropics/skills) `skills/skill-creator` (Apache-2.0 License — see `LICENSE.txt`).

## Local Modifications

The following changes were made to the original anthropics/skills skill-creator:

### Modified files
- `scripts/quick_validate.py` — added `greeting`/`disable-model-invocation` fields, `metadata.uskill.*` passthrough, directory-name warning (not error)
- `scripts/package_skill.py` — expanded exclusion set, deterministic output (sorted walk, fixed zip timestamps)
- `scripts/aggregate_benchmark.py` — added Pass^k (reliability), stability metric, paired significance note
- `agents/grader.md` — added first-error attribution step (9-category taxonomy)
- `agents/comparator.md` — added position-swap dual scoring (bias mitigation)
- `references/schemas.md` — added `triggers.json` schema and scenario frontmatter schema
- `SKILL.md` — rewritten as thin routing body (~230 lines) with hard rules, phase checkboxes, and reference index

### New files
- `references/authoring.md` — blueprint, failure-form table, description methodology, carrier decision, layering
- `references/eval-methodology.md` — RED/GREEN gates, hash-stratified holdout, Pass^k, paired statistics, judge reliability
- `references/review-playbook.md` — 4-stage × 15-dimension review with evidence discipline
- `references/common-pitfalls.md` — 6 high-frequency pitfalls (seed examples, customizable)
- `references/security.md` — lethal trifecta, audit checklist, supply chain
- `references/release.md` — operating modes, release gates, versioning, SkillOps
- `agents/skill-reviewer.md` — Stage 1+2 review subagent
- `agents/doc-verifier.md` — Stage 3 doc↔code parity subagent
- `agents/adversary.md` — adversarial reviewer (refute-not-approve)
- `scripts/snapshot_skill.py` — immutable SHA-256 baseline snapshots
- `scripts/score_triggers.py` — hash-stratified holdout trigger scoring
- `scripts/run_skill_evals.py` — shipped evals runner (static/live)
- `scripts/doctor.py` — ecosystem health checks

## Third-Party Ideas Incorporated

Design patterns and concepts were adapted from the following open-source projects (ideas, not code):

| Source | Ideas |
|--------|-------|
| [tripleyak/SkillForge](https://github.com/tripleyak/SkillForge) | RED/GREEN gates, shipped evals, failure-form table, adversarial reviewer, ecosystem doctor |
| [oil-oil/oil-skill-creator](https://github.com/oil-oil/oil-skill-creator) | 15-dim review, hash-stratified holdout, immutable snapshots, versioning |
| [joeseesun/qiaomu-meta-skill](https://github.com/joeseesun/qiaomu-meta-skill) | Prior-art search, near-miss triggers, operating modes, release gates, evidence discipline, SkillOps |
| [DazhuangJammy/DazhuangSkill-Creator](https://github.com/DazhuangJammy/DazhuangSkill-Creator) | Writing blueprint, section whitelist, content sinking map |
| [claudekit/skillmark](https://github.com/claudekit/skillmark) | Security test types, token-efficiency criteria |
| [milesgoscha/skillbench](https://github.com/milesgoscha/skillbench) | Robustness perturbation, composability metrics |
| [AGI-comming/functional-skill-creator](https://github.com/AGI-comming/functional-skill-creator) | Function contracts, trace→testcase |
| [Sahir619/fable-method](https://github.com/Sahir619/fable-method) | Prove phase, null results |
| [NVIDIA/SkillSpector](https://github.com/NVIDIA/SkillSpector) | Vulnerability taxonomy, risk bands |
| [agentskills.io](https://agentskills.io) | Best-practices, description optimization methodology |
| [obra/superpowers](https://github.com/obra/superpowers) | Iron Law (RED before write), Match-Form-to-Failure |
| [bojieli/ai-agent-book](https://github.com/bojieli/ai-agent-book) | Harness framing, Pass@k vs Pass^k, Rubric+Veto, first-error attribution |
| [bojieli/ai-infra-book](https://github.com/bojieli/ai-infra-book) | Thin orchestration + thick references, cache-aware design |

## License

Apache-2.0 (see `LICENSE.txt`). Modifications and additions are released under the same license.
