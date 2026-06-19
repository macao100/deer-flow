---
name: superpowers-finishing-branch
description: Guide completion of development work by presenting clear options (merge, PR, abandon) and handling the chosen workflow. Use when implementation is complete, tests pass, and you need to integrate.
---

# Finishing a Development Branch (Superpowers)

## Overview

When implementation is complete and all tests pass, this skill guides the integration decision: merge directly, open a PR, or abandon the work. It ensures nothing is left behind — no dangling worktrees, no forgotten cleanup.

## Core Principle

**Finish what you start, cleanly.** Every branch that opens must close — with a deliberate decision and proper cleanup.

## When to Use

- Implementation is complete on a feature branch
- All tests pass
- You need to decide how to integrate the work
- When the user says "ship it", "merge", "PR", "wrap up"

## Workflow

### Step 1: Verify Tests
- Run the full test suite one last time
- Confirm all tests pass with clean output
- Check for any uncommitted changes

### Step 2: Detect Environment
- What branch are we on?
- What's the target branch (main/master)?
- Are there worktrees or stashes to clean up?

### Step 3: Present Options
1. **Merge directly** — fast, for trusted changes with passing tests
2. **Open a PR** — for changes that need review or discussion
3. **Abandon** — if the approach didn't work out, clean up deliberately

### Step 4: Execute Choice
- Merge: `git checkout main && git merge --no-ff feature-branch`
- PR: Push branch, create PR with structured description
- Abandon: `git checkout main && git branch -D feature-branch`, clean worktrees

### Step 5: Clean Up
- Remove git worktrees if any were created
- Delete the local feature branch after merge
- Update any tracking documents

## Guardrails

- Never merge without passing tests
- Never abandon without explicit user confirmation
- Clean up worktrees — don't leave isolation environments dangling

## Announcement

"I'm using the finishing-a-development-branch skill to complete this work."
