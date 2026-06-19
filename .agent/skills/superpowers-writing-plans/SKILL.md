---
name: superpowers-writing-plans
description: Create structured implementation plans from specs or requirements before touching code. Use when you have a spec, design doc, or multi-step task. Save plans to docs/plans/ for traceability.
---

# Writing Plans (Superpowers)

## Overview

Transform specs and design documents into actionable implementation plans before touching code. A plan prevents scope creep, identifies dependencies, and provides a clear completion checklist.

## Core Principle

**Plan the work, then work the plan.** Without a plan, you're just reacting. With a plan, you're executing.

## When to Use

- After a design is approved (post-brainstorming)
- For any multi-step implementation task
- When the user provides requirements or a spec
- Before starting implementation

## Plan Structure

### Required Sections
1. **Goal** — one sentence describing what success looks like
2. **Tasks** — ordered list of independent, testable tasks
   - Each task: description, acceptance criteria, estimated complexity
   - Tasks should be independently verifiable and committable
3. **Dependencies** — what must be done before what
4. **Risks** — what could go wrong and mitigation
5. **Verification** — how to confirm the whole plan is complete

### Task Writing Guidelines
- **Independent**: Each task produces a committable, testable unit of work
- **Ordered**: Tasks are sequenced by dependency and risk (riskiest first)
- **Sized**: Each task should take roughly similar effort (no 5-minute tasks next to 5-day tasks)
- **Verifiable**: Each task has clear acceptance criteria

## Plan Location
Save plans to: `docs/plans/YYYY-MM-DD--plan-name.md`

## Announcement

"I'm using the writing-plans skill to create the implementation plan."

## Transition
After plan approval, use `subagent-driven-development` to execute tasks.
