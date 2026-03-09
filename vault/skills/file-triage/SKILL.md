# Skill: File Triage

**Tier:** Bronze
**Trigger:** A new `.md` file appears in `Inbox/`
**Output:** One file in either `Needs_Action/` or `Done/`

---

## Purpose

This skill teaches the AI employee how to read an incoming task, understand it,
decide what to do with it, and write a properly structured output file.
Follow each step in order. Do not skip steps.

---

## Step 1 — Read the Inbox File

1. Open the file from `Inbox/`.
2. Read the entire content before drawing any conclusions.
3. Identify and record the following:

   - **Title** — the top-level heading (`# ...`) or the filename if no heading exists
   - **Body** — all content below the title
   - **Requests** — any sentences that ask for something (look for words like *please*, *need*, *can you*, *send*, *schedule*, *review*, *approve*)
   - **Deadlines** — any dates, times, or urgency words (*urgent*, *ASAP*, *by Friday*, *before EOD*)
   - **Attached context** — links, quoted text, or referenced files

4. If the file is empty or unreadable, treat it as low priority and note it in your output.

---

## Step 2 — Summarize the Task

Write a summary using this structure. Keep each field to one or two sentences.

```
What:    What is being asked or communicated?
Who:     Who sent it, or who is it about? (use "Unknown" if not stated)
When:    Is there a deadline or time reference? (use "None stated" if absent)
Why:     What is the underlying reason or goal?
```

**Rules for summarizing:**
- Use plain, direct language.
- Do not add opinions or assumptions.
- If the task is vague, summarize what is known and flag the gaps explicitly.
- Never truncate — if the original is long, your summary must still capture all distinct requests.

---

## Step 3 — Classify the Task

Read your summary and apply the decision rules below in order.
Stop at the first rule that matches.

| Rule | Condition | Decision |
|------|-----------|----------|
| 1 | The file contains no requests and no action items | **Done** — informational only |
| 2 | The request is already completed or the file is a confirmation/receipt | **Done** — archive it |
| 3 | The request requires sending a message, email, or post | **Needs Action** — draft required, human must approve |
| 4 | The request involves money, contracts, or legal matters | **Needs Action** — escalate to human immediately |
| 5 | The request is a routine internal task (summarize, organize, label) | **Needs Action** — AI may proceed autonomously |
| 6 | The request is unclear or contradictory | **Needs Action** — flag for human clarification |
| 7 | None of the above apply | **Needs Action** — default to caution |

Record your decision as either `NEEDS_ACTION` or `DONE`.

---

## Step 4 — Write the Output File

### If decision is `NEEDS_ACTION`

Create a file in `Needs_Action/` named:
```
YYYYMMDD_HHMMSS_<original-filename>.md
```

Use this exact template:

```markdown
# Action Required — <Title>

**Date received:** <timestamp>
**Source:** Inbox/<original-filename>
**Priority:** <High / Medium / Low>

---

## Summary

**What:** <what>
**Who:**  <who>
**When:** <when>
**Why:**  <why>

---

## Gaps / Flags

<List anything unclear, missing, or that requires human judgment.
Write "None" if everything is clear.>

---

## Recommended Next Step

<One clear sentence describing the single most important action to take next.>

---

## Original Content

<Paste the full original file content here, unmodified.>

---

_Triaged by AI Employee — File Triage Skill_
```

---

### If decision is `DONE`

Create a file in `Done/` named:
```
YYYYMMDD_HHMMSS_<original-filename>.md
```

Use this exact template:

```markdown
# Archived — <Title>

**Date received:** <timestamp>
**Source:** Inbox/<original-filename>
**Reason archived:** <one sentence explaining why no action is needed>

---

## Summary

**What:** <what>
**Who:**  <who>
**When:** <when>
**Why:**  <why>

---

## Original Content

<Paste the full original file content here, unmodified.>

---

_Triaged by AI Employee — File Triage Skill_
```

---

## Step 5 — Update the Dashboard

After writing the output file, open `Dashboard.md` and:

1. Increment the count for either `Needs Action` or `Done` in the Task Summary table.
2. Append one row to the Activity Log table:

   ```
   | <timestamp> | File Triage: <original-filename> | <NEEDS_ACTION or DONE> |
   ```

3. Save `Dashboard.md`.

---

## Error Handling

If anything goes wrong during triage, do the following:

1. Do **not** delete or modify the original Inbox file.
2. Create a file in `Needs_Action/` named `ERROR_<timestamp>_<filename>.md`.
3. Describe what went wrong in plain language.
4. Stop and wait for human review.

---

## Quality Checklist

Before finishing, verify:

- [ ] Output file is in the correct folder (`Needs_Action/` or `Done/`)
- [ ] Output file uses the correct template for its decision
- [ ] All four summary fields are filled in (no blanks)
- [ ] Original content is pasted in full at the bottom
- [ ] `Dashboard.md` activity log has been updated
- [ ] Original Inbox file has **not** been deleted or modified

---

## Boundaries

This skill does **not** authorize the AI to:

- Send any message to any person or system
- Delete the original Inbox file
- Make decisions involving money, legal matters, or personnel
- Access any system outside this vault

If any of the above are required to complete the task, stop and escalate.
