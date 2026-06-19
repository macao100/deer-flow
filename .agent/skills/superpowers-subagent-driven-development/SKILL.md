---
name: superpowers-subagent-driven-development
description: Execute implementation plans by dispatching independent tasks to subagents in parallel. Use when executing multi-task plans where tasks are independent. Requires git worktree setup for isolation.
---

# Subagent-Driven Development (Superpowers)

## Overview

Execute implementation plans by dispatching independent tasks to subagents that work in isolated git worktrees. Each subagent gets a clean context, works on one task, and returns a verified result.

## Core Principle

**Isolate to accelerate.** Independent tasks run in parallel in clean contexts — no context pollution between tasks, no accidental coupling.

## When to Use

- When executing a multi-task implementation plan
- Tasks are confirmed independent (no shared mutable state)
- After `writing-plans` has produced an approved plan

## Workflow

### Step 1: Read the Plan
- Load the plan file once
- Extract all tasks with full descriptions and acceptance criteria
- Create a task tracking list

### Step 2: Assess Independence
- Verify tasks don't share mutable state
- Identify any hidden dependencies
- Group tasks that must be sequential

### Step 3: Dispatch Subagents
For each independent task:
- Create isolated git worktree
- Dispatch subagent with: task description, acceptance criteria, relevant code context
- Subagent follows TDD → implement → verify → report

### Step 4: Collect and Integrate
- Collect results from all subagents
- Verify each task's acceptance criteria
- Integrate into main branch
- Run full test suite

## Prerequisites

- Git worktrees enabled
- Plan document exists in `docs/plans/`
- Tasks confirmed independent

## Guardrails

- Each subagent gets targeted context only — not the full plan
- Subagents must verify before reporting completion
- If a subagent fails, stop and investigate — don't dispatch more

## Announcement

"I'm using subagent-driven development. Reading the plan and assessing task independence first."
