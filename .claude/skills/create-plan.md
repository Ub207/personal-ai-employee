# Skill: Create Plan

## Purpose
Generate a structured Plan.md file for complex multi-step tasks.
This enables Claude to reason through tasks systematically before executing.

## Trigger
Run this skill when:
- A task requires multiple steps to complete
- The user asks you to "plan" or "think through" something
- You detect a complex request in /Needs_Action

## Steps

1. **Understand the Objective**
   - Read the task description from the input file
   - Identify the desired end state
   - Note any constraints or requirements

2. **Research Context**
   - Read Company_Handbook.md for relevant rules
   - Check Business_Goals.md for alignment
   - Review similar tasks in /Done for patterns

3. **Break Down the Task**
   - List all required steps in logical order
   - Identify dependencies between steps
   - Estimate effort for each step

4. **Identify Risks & Approvals**
   - Flag steps requiring human approval (per Company_Handbook.md)
   - Note potential failure points
   - Suggest fallback options

5. **Write Plan.md**
   - Use the template below
   - Save to /Plans/ folder
   - Link back to original request

6. **Execute or Wait**
   - If all steps are auto-approved: begin execution
   - If approvals needed: create approval requests first

## Output Template

```markdown
---
type: plan
created: {ISO_TIMESTAMP}
status: in_progress
objective: {Brief description}
estimated_steps: {N}
requires_approval: {true/false}
---

# Plan: {Objective}

## Objective
{Clear statement of what we're trying to achieve}

## Context
- **Source:** {Original file/request}
- **Priority:** {high/normal/low}
- **Deadline:** {If specified}

## Steps

| # | Action | Status | Notes |
|---|--------|--------|-------|
| 1 | {First step} | [ ] | {Details} |
| 2 | {Second step} | [ ] | {Details} |
| 3 | {Third step} | [ ] | {Details} |

## Required Approvals
{List any steps requiring human sign-off per Company_Handbook.md}

## Risks & Mitigations
| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| {Risk 1} | Low/Med/High | Low/Med/High | {How to avoid/handle} |

## Success Criteria
- [ ] {Criterion 1}
- [ ] {Criterion 2}

## Notes
{Additional context, decisions made, alternatives considered}
```

## Example Output

```markdown
---
type: plan
created: 2026-03-09T10:30:00Z
status: pending_approval
objective: Send invoice to Client A
estimated_steps: 4
requires_approval: true
---

# Plan: Send Invoice to Client A

## Objective
Generate and email invoice for January services to Client A.

## Context
- **Source:** WHATSAPP_2026-03-09_client_a.md
- **Priority:** high (invoice request)
- **Deadline:** End of week

## Steps

| # | Action | Status | Notes |
|---|--------|--------|-------|
| 1 | Verify client rate | [ ] | Check Company_Handbook.md |
| 2 | Generate invoice PDF | [ ] | Use template in /Templates/ |
| 3 | Draft email with attachment | [ ] | Auto-approved |
| 4 | Send email | [ ] | REQUIRES APPROVAL |

## Required Approvals
- Step 4: Sending external email with attachment

## Risks & Mitigations
| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Wrong amount | Low | High | Double-check with handbook rates |
| Wrong email | Low | High | Verify against known contacts |

## Success Criteria
- [ ] Invoice sent to correct email
- [ ] Client confirms receipt
- [ ] Transaction logged in Dashboard

## Notes
Client A rate: $150/hour per handbook. January hours: 10 = $1,500 total.
```

## Related Skills
- `process-inbox` — Use after plan execution
- `update-dashboard` — Update after plan completion
