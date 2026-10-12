# Security Audit — Skill as Injection Surface

A skill is "institutionalized loading of external content as instructions." Audit every skill like you audit code.

---

## The Lethal Trifecta

High risk when all three are present simultaneously:

| Element | Meaning |
|---------|---------|
| **Private data** | Access to secrets, credentials, personal data, internal systems |
| **Untrusted content** | Processes external input (user uploads, web content, API responses) |
| **Outbound communications** | Can send data out (network calls, file writes, messaging) |

**Memory is an amplifier**: persistent memory (lessons, state files) that accumulates across sessions can carry injection payloads forward.

If a skill has all three → **high risk** → require security review before use.

---

## Audit Checklist

### Prompt injection

- [ ] No instructions in the skill that say "ignore previous instructions" or similar
- [ ] External content (API responses, file contents) is treated as DATA, not instructions
- [ ] No "anti-refusal" patterns ("never decline", "always comply")

### Supply chain

- [ ] No `curl | bash` or `wget | sh` patterns
- [ ] Dependencies are pinned (not `latest`, not floating)
- [ ] No obfuscated code (base64-encoded scripts, eval of dynamic strings)
- [ ] No typosquatting-suspicious package names
- [ ] Submodules are reviewed

### Secrets & credentials

- [ ] No plaintext API keys, passwords, tokens in any file
- [ ] No secrets in logs, eval outputs, or snapshots
- [ ] Credential handling uses environment variables or OS keychain
- [ ] `$TOOL_INPUT` / `$TOOL_OUTPUT` in hooks are quoted (command injection prevention)

### Excessive agency

- [ ] `allowed-tools` is minimal — only tools the skill actually needs
- [ ] No destructive operations without confirmation
- [ ] Skill cannot modify its own security gates

### File system

- [ ] No hardcoded absolute paths (`/Users/...`)
- [ ] No writing outside the expected workspace
- [ ] Symlinks are rejected in snapshots and packaging

### MCP / external integrations

- [ ] MCP tools are least-privilege
- [ ] External API calls have timeout and error handling
- [ ] No auto-update from remote sources

---

## Action Authorization Taxonomy

"Entailment is not permission." Just because a skill's instructions imply an action doesn't mean it's authorized to perform it.

Classify every action a skill can take:

| Class | Meaning | Example |
|-------|---------|---------|
| **Required + authorized** | Core function, safe to execute | Read a config file to parse |
| **Required + needs authorization** | Core function, risky — must ask user first | Write to production database |
| **Optional** | Enhancement, safe but not core | Generate a summary |
| **Out of scope** | Must never happen | Delete user's files, send network requests |

### Audit questions

1. What actions does this skill instruct the agent to take?
2. Which class does each fall into?
3. Are "required + needs authorization" actions gated by explicit user confirmation?
4. Are any "out of scope" actions reachable through instructions?
5. Could a prompt injection escalate an action to a higher class?

### Authorization gating rules

- **Write/Modify**: always require user confirmation (not `--yes` default)
- **Delete**: always require explicit user confirmation
- **Network send**: require confirmation if private data could be included
- **Read of secrets**: require confirmation + redaction
- **Execute arbitrary code**: require confirmation + sandbox consideration

---

## Safe Gate Cannot Be Self-Modified

A skill must not be able to alter its own security constraints. This means:

- `allowed-tools` is set in frontmatter (read by the harness, not the skill body)
- Confirmation gates live in code (scripts), not in prose that the model can negotiate away
- Review/security findings trigger a human decision, never an automatic skill edit

---

## Supply-Chain Red Flags

| Pattern | Risk | Action |
|---------|------|--------|
| `pip install <unpinned>` in scripts | Arbitrary code from PyPI | Pin exact version |
| `curl ... \| sh` | Remote code execution | Download, inspect, then run |
| Auto-update (`git pull`) | Unreviewed code enters | Prompt user to update manually |
| `evals/` excluded from package but visible on install | Test data leaks | Verify excludes work end-to-end |
| Submodule without hash pin | Supply chain injection | Pin commit SHA |

---

## SkillSpector-Inspired Risk Bands

| Score | Verdict | Action |
|-------|---------|--------|
| 0–20 | SAFE | Use normally |
| 21–50 | CAUTION | Review findings before use |
| 51+ | DO NOT INSTALL | Must fix all P0s first |

Score weights: secrets (10), injection (8), supply chain (7), excessive agency (5), file system (3), other (1–3).

---

## Minimal Privilege Template

```yaml
---
name: my-skill
allowed-tools: Read, Grep, Glob
# Add Bash, Write, Edit only if the skill actually needs them
---
```

Prefer `Read, Grep, Glob` (read-only) as the starting point. Add write/execute tools only with clear justification.
