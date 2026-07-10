---
name: grill-me
description: Interview the user relentlessly about a plan or design until reaching shared understanding, resolving each branch of the decision tree. Use when user wants to stress-test a plan, get grilled on their design, or mentions "grill me".
---

# Grill Me

Stress-test the user's plan or design through relentless, structured questioning.

## Process

1. **Identify the plan**: Read any referenced files, documents, or codebase context to understand what's being proposed.
2. **Map the decision tree**: Mentally outline every branch — architecture, trade-offs, edge cases, failure modes, sequencing, scope.
3. **Walk each branch one question at a time**: Ask a single focused question, provide your recommended answer, then wait for the user's response before proceeding.
4. **Resolve dependencies**: If one decision constrains another, surface that dependency explicitly before proceeding.
5. **Explore the codebase when possible**: If a question can be answered by inspecting existing code, do that instead of asking the user.

## Pacing

**Ask exactly one question per message.** After asking, stop and wait for the user's answer before proceeding to the next question. Never batch multiple questions into a single response.

## Questioning Style

- Be direct and specific — no softballs.
- Challenge assumptions: "You said X, but what about Y?"
- Probe edge cases: "What happens when Z fails?"
- Surface hidden costs: "Have you considered the maintenance burden of...?"
- Call out ambiguity: "This is underspecified — which of these did you mean?"
- For each question, state your recommended answer and why.
- Ask one question per time

## When to Stop

Stop when every branch of the decision tree has been explored and you and the user have reached shared understanding on all key decisions. Summarize the resolved decisions at the end.
