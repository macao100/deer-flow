---
name: superpowers-verification-before-completion
description: Enforces disciplined verification before claiming work is complete. Never claim "done" without evidence. Use when completing tasks, implementing features, or submitting work for review. Evidence before claims, always.
---

# Verification Before Completion (Superpowers)

## Overview

Claiming work is complete without verification is dishonesty, not efficiency. This skill enforces a mandatory verification gate before any work can be declared done.

## Core Principle

**Evidence before claims, always.** If you can't prove it works, it's not done.

## When to Use

- When a task appears complete
- Before submitting work for review
- Before merging or deploying
- Before handing off to another developer
- When the user says "verify", "check your work", "is this done?"

## The 5-Step Gate

### Step 1: Identify the Proof Command
What command, when run, will demonstrate the work is correct?
- Tests passing? → `pytest` or equivalent
- Build succeeding? → `npm run build` or equivalent
- Feature working? → The specific curl/CLI command that exercises it

### Step 2: Run It Fresh
- Execute the command in a clean state
- Do NOT rely on cached results or memory of running it earlier
- If the environment needs setup, do it now

### Step 3: Read Full Output and Exit Code
- Read the COMPLETE output, not just the summary
- Check the exit code explicitly
- Look for warnings, not just errors

### Step 4: Verify the Claim Matches Evidence
- Does the output actually prove the claim?
- Are there any caveats or partial failures?
- Is the evidence sufficient for someone else to agree?

### Step 5: State the Result with Evidence
```
✅ VERIFIED: All 42 tests pass (0 failures, 0 errors)
   Command: pytest tests/ -v
   Exit code: 0
   Coverage: 87% (threshold: 80%)
```

OR

```
❌ NOT VERIFIED: 3 test failures in auth module
   Command: pytest tests/ -v
   Exit code: 1
   Failures: test_login, test_logout, test_session_expiry
```

## Anti-Patterns

- ❌ "It should work" — not evidence
- ❌ "It worked earlier" — run it again now
- ❌ "I only changed one line" — verify anyway
- ❌ Skipping verification for "trivial" changes — trivial changes cause the most embarrassing bugs

## Announcement

"I'm using verification-before-completion. Let me run the proof command to confirm this is actually done."
