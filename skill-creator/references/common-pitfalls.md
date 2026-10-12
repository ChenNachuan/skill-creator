# Common Pitfalls — Seed Examples (Customizable Template)

> **DISCLAIMER**: These 6 are **SEED EXAMPLES** distilled from one team's data-API skills — **NOT a universal checklist**. Audit your own skill's actual failure modes and maintain a local additions section below. What is common in one domain may be irrelevant in another.

Each pitfall has: **Symptom** (what you see) → **Root cause** (why it happens) → **Check** (grep/script recipe) → **Fix** (pattern to apply).

---

## 1. argparse Subparser Default Override

**Symptom**: A CLI flag works at the top level but is silently ignored when used with a subcommand.

**Root cause**: Subparser redefines the same argument with a `default=`, which overrides the parent parser's value even when the user didn't pass it.

```python
# BROKEN: subparser default=False silently overrides parent --yes
parser.add_argument('--yes', action='store_true')
sub = parser.add_subparsers()
sub_parser = sub.add_parser('write')
sub_parser.add_argument('--yes', action='store_true', default=False)  # ← overrides
```

**Check**:
```bash
grep -n "add_argument.*default=" scripts/*.py | grep -v "SUPPRESS"
# Review each: is this argument also defined on the parent parser?
```

**Fix**: Use `argparse.SUPPRESS` as the default in subparsers:
```python
sub_parser.add_argument('--yes', action='store_true', default=argparse.SUPPRESS)
```

---

## 2. API Read/Write Field Name Asymmetry

**Symptom**: A GET endpoint returns `column_type` but the POST endpoint expects `data_type`. Code that round-trips data fails silently or with confusing errors.

**Root cause**: The API uses different field names for the same concept on read vs. write paths.

**Check**:
```bash
# Find field names in response parsing vs request construction
grep -n "column_type\|data_type\|field_name\|param_name" scripts/*.py
# Compare: are the same concepts named differently on read vs write?
```

**Fix**: Add an explicit field-mapping layer at the API boundary:
```python
READ_TO_WRITE = {"column_type": "data_type", "col_name": "name"}
def to_write_fields(read_record: dict) -> dict:
    return {READ_TO_WRITE.get(k, k): v for k, v in read_record.items()}
```

---

## 3. `allow_fail` Consistency

**Symptom**: Query operations silently swallow errors while write operations crash (or vice versa).

**Root cause**: `allow_fail` (or equivalent error-tolerance flag) is passed on one path but not the other, or defaults to different values.

**Check**:
```bash
grep -n "allow_fail\|fail_silently\|suppress_error" scripts/*.py
# Verify: reads and writes use the same policy, or the difference is intentional
```

**Fix**: Make the policy explicit and consistent:
- Reads: `allow_fail=True` (return empty/partial, caller checks)
- Writes: `allow_fail=False` + status check + clear error message

---

## 4. Status Value i18n (Chinese/English)

**Symptom**: Code checks `if status == 'published'` but the API sometimes returns `'已上架'`. Logic branches are never taken.

**Root cause**: API or database returns localized status strings depending on locale/tenant.

**Check**:
```bash
grep -n "== ['\"]published\|== ['\"]draft\|== ['\"]已\|== ['\"]草稿" scripts/*.py
# Look for hardcoded status comparisons without normalization
```

**Fix**: Normalize at the boundary:
```python
STATUS_MAP = {"已上架": "published", "已下架": "archived", "published": "published", "archived": "archived"}
def normalize_status(raw: str) -> str:
    return STATUS_MAP.get(raw, raw)
```

---

## 5. Operator Position (Body vs Query Param)

**Symptom**: Some API calls pass `operator` in the request body; others require it as a query parameter. One path works, the other gets 400 or silently loses the audit trail.

**Root cause**: Different endpoints use different conventions for where the acting user/operator is specified.

**Check**:
```bash
grep -n "operator" scripts/*.py | grep -i "param\|body\|query\|payload\|json"
# For each API call: is operator in the right place for that endpoint?
```

**Fix**: Document per-endpoint in a comment or dict:
```python
# Endpoint operator placement:
#   POST /api/v1/tables     → body
#   PUT  /api/v1/tables/:id → query param
#   DELETE /api/v1/rows     → body
```

---

## 6. Confirm Logic vs Documentation Drift

**Symptom**: SKILL.md says "confirmation is required for destructive operations," but code only confirms for a subset. Or the reverse.

**Root cause**: Documentation and code evolved independently.

**Check**:
```bash
# Compare documented confirmation requirements against actual code
grep -n "confirm\|Confirm\|yes.*[Yy]/[Nn]" scripts/*.py
grep -n "confirm\|确认" SKILL.md references/*.md
# Cross-reference: every documented confirmation has a code check, and vice versa
```

**Fix**: Single source of truth — either generate the confirmation table from code comments, or add a test that asserts documentation matches code:
```python
CONFIRM_REQUIRED = {"delete_table", "drop_column", "bulk_update"}  # source of truth
```

---

## Local additions (your domain here)

Add pitfalls you discover in your own skills:

| # | Symptom | Root cause | Check | Fix |
|---|---------|------------|-------|-----|
| 7 | | | | |
| 8 | | | | |
