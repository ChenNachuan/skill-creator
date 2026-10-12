# Release — Operating Modes, Gates, Versioning, SkillOps

How to right-size process and ship skills responsibly.

---

## Operating Modes

| Mode | Use case | Gates applied |
|------|----------|---------------|
| **Scaffold** | Personal experiment, learning, throwaway | quick_validate only; skip RED GATE |
| **Standard** | Default for real skills | RED/GREEN, evals shipped, 4-stage review |
| **Governed** | Team reuse, public release, production | + security scan, release gates, versioning, publish checklist |

### Gate selection

| Gate | Scaffold | Standard | Governed |
|------|----------|----------|----------|
| quick_validate | ✅ | ✅ | ✅ |
| RED GATE | skip | ✅ | ✅ |
| GREEN GATE (evals shipped) | optional | ✅ | ✅ |
| Hash holdout | skip | ✅ | ✅ |
| 4-stage review | skip | ✅ | ✅ |
| Adversarial review | skip | optional | ✅ |
| Security scan | skip | checklist only | ✅ + script |
| Release gates (pass/warn/block) | skip | warn-only | ✅ |
| Versioning | skip | recommended | ✅ |
| Publish checklist | skip | skip | ✅ |

---

## Release Gates (Three Outcomes)

Each check produces one of:

| Verdict | Meaning |
|---------|---------|
| **pass** | Verified — evidence exists |
| **warn** | Noted, doesn't block; fix before next iteration |
| **block** | **Forbidden to claim ready** — must fix before release |

### Stage progression

| Check | local | pr | published |
|-------|-------|----|-----------|
| Dirty worktree | warn | **block** | **block** |
| Missing evidence (P0) | warn | **block** | **block** |
| Security findings (P0) | warn | warn | **block** |
| evals not shipped | warn | warn | **block** |

---

## Evidence Levels

| Level | Counts as | Notes |
|-------|-----------|-------|
| `provider_backed` | pass | Verified by running the actual tool/script |
| `human_blind_review` | pass | Independent reviewer, judged before reveal |
| `recorded_fixture` | warn | Cached recording, not live proof |
| `missing evidence` | warn / block | Write this explicitly; never fill with pretty words |

**A report never auto-edits a skill.** If review finds issues, present them to the user. Only edit when the user explicitly requests it.

---

## Root Entry Isolation

- Exactly **one** `SKILL.md` in the skill directory tree
- Example/fixture files use `SKILL.example.md` or `SKILL.fixture.md` (not `SKILL.md`)
- `package_skill.py` scans the full tree and blocks if extra `SKILL.md` found

---

## Versioning

Add to frontmatter (optional):

```yaml
metadata:
  version: "1.2.0"
```

| Change type | Bump |
|-------------|------|
| Bug fix, wording, minor formatting | PATCH |
| New capability, new reference file, behavior change | MINOR |
| Breaking change to interface/contract | MAJOR |

**Changelog lives in Release notes**, not in SKILL.md body. Same version number is released only once.

---

## Publish Checklist (Governed)

- [ ] `quick_validate` passes
- [ ] Snapshot created (immutable baseline for future diffs)
- [ ] Secret scan: `grep -rn "api.key\|password\|token\|secret" .` (manual or scripted)
- [ ] Security checklist (see `references/security.md`)
- [ ] evals/ shipped and passing
- [ ] `package_skill` produces clean ZIP
- [ ] Isolated install verify: install in clean env, run smoke test
- [ ] Version bumped and changelog written

Never push directly to main for Governed skills. Use feature branch → PR → checks → merge.

---

## SkillOps (Post-Release Loop)

Signal → action mapping:

| Signal | Action |
|--------|--------|
| One-off user preference ("I like X style") | Record only — do NOT change rules |
| Repeated wrong trigger | Add trigger eval case; refine description |
| Quality regression on a task type | Add output eval scenario |
| Security finding | Fix immediately (P0); no process gate needed |

**Hard rule**: Reports and observations never auto-edit a skill. Only explicit user request triggers changes.

---

## Optional Exports

### skill-ir.json (platform-neutral contract)

Answers: "What does this skill own?" — identity, behavior, trigger, execution, artifacts, platform, evidence-boundary. Useful for cross-platform diffing and regression.

### Cross-runtime notes

For Codex / agentskills.io targets: strip Claude-specific fields, generate `MIGRATION_NOTES.md` explaining each strip. Watch 64-char name / 1024-char description limits.

### CI integration

Use `claude plugin eval` for automated with/without testing in CI pipelines. See Claude Code docs for setup.
