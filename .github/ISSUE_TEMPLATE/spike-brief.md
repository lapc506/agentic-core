---
name: Spike Brief (Bilingual Issue)
about: AI+Human readable issue brief with analysis
title: "[SPIKE] "
labels: "type:spike"
assignees: ''
---

# Issue Title

> **Type:** `spike`
> **Size:** `{XS|S|M|L|XL}`
> **Strategy:** `{solo|explore|team|human|worktree|review}`
> **Components:** `{component1}`, `{component2}`
> **Impact:** `{critical-path|oss-adoption|---}`
> **Flags:** `{blocked|quick-win|epic|good-first-issue|---}`
> **Branch:** `feat/short-description`

---

## Human Layer

### User Story

As a **{role}**, I want **{X}** so that **{Y}**.

### Background / Why

{2-3 paragraphs explaining the problem, motivation, and context.}

### Known Pitfalls & Gotchas

- {pitfall 1}
- {pitfall 2}

---

## Agent Layer

### Objective

{1-2 sentence technical outcome.}

### Context Files

- `path/to/file` -- {why}

### Acceptance Criteria

- [ ] {criterion}
- [ ] {criterion}

### Technical Constraints

- {constraint}

### Verification Commands

```bash
pytest tests/ -v
ruff check src/
mypy src/
```

### Agent Strategy

**Mode:** `{strategy}`

{Strategy-specific details per spike-recommend template}

---

## Parallelization Recommendation

**Recommended mechanism:** `{Subagents|Git Worktrees|Agent Teams|None (Solo)}`

**Reasoning:** {explanation}

**Cost estimate:** ~{N}x base token cost
