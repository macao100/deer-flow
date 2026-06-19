---
name: superpowers-code-review
description: Request and receive code reviews using subagent-based reviewer with structured context. Use after completing tasks, implementing features, or before merging. The reviewer gets precisely crafted context — never your session's history — for unbiased evaluation.
---

# Code Review (Superpowers)

## Overview

Combine requesting and receiving code review into one skill. Dispatch a code reviewer subagent with precisely crafted context for evaluation, then handle the review feedback systematically.

## Core Principle

**Every change gets reviewed.** The reviewer operates with crafted context — not your session history — to provide an unbiased, focused evaluation of the work product.

## When to Use

- After completing any non-trivial task
- Before merging to main
- When stuck and need a second perspective
- Before major refactors
- After complex bug fixes

## Requesting a Review

### Prepare Review Context
```
BASE_SHA: <commit before changes>
HEAD_SHA: <current commit>
DESCRIPTION: <what this change does>
PLAN_OR_REQUIREMENTS: <reference to spec/plan if any>
```

### Dispatch Reviewer
Send this context to a reviewer subagent — never include your session's debugging history, false starts, or thought process. The reviewer evaluates the work product, not your journey.

### Reviewer's Output Format
The reviewer should provide:
1. **Strengths** — what's well done
2. **Issues** — categorized by severity (critical, important, minor)
3. **Assessment** — ready to proceed, needs changes, or blocked

## Receiving a Review

### Process Feedback Systematically
1. **Read the entire review** before reacting
2. **Categorize issues**: critical (must fix), important (should fix), minor (consider fixing)
3. **Fix critical and important issues** before proceeding
4. **Acknowledge minor issues** — either fix or document why not
5. **Ask before assuming** — if feedback is unclear, verify before implementing

### Core Principle for Receiving
**Verify before implementing. Ask before assuming.** Don't reflexively implement every suggestion — understand the reasoning first.

## Anti-Patterns

- ❌ Skipping review for "small" changes
- ❌ Including session history in review context (biases the reviewer)
- ❌ Defensive reactions to feedback
- ❌ Implementing feedback without understanding the reasoning

## Announcement

Requesting: "I'm dispatching a code reviewer subagent with crafted context."
Receiving: "Let me process this review systematically — critical issues first."
