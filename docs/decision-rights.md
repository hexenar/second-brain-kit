# Who decides what: the kit on the AI decision matrix

This document maps the kit's operations onto a published framework: the **AI Decision Matrix** by I. Sebastian, P. Weill, T. Haskamp and J. vom Brocke, "Designing Decision Rights for AI" (MIT Sloan, 2026). It is summarised here in our own words; search for the original by title and authors. How the kit's operations are classified is ours, not the authors'.

## The framework in brief

Every decision has three components:

| Component | What it is |
|---|---|
| **Frame** | Define the decision: what is being asked and by which criteria. |
| **Act** | Take or recommend the action. |
| **Learn** | Own the outcome and improve it. |

Each component has one of three participants: **human**, **human with AI** or **AI**.

Two axes sort decisions: **ambiguity** (is it clear what has to be decided?) and **risk** (how costly is a mistake?). That gives four quadrants:

| Quadrant | Ambiguity · risk | Approach | Frame | Act | Learn |
|---|---|---|---|---|---|
| **Exploratory** | high · low | Enable experimentation to learn fast | human with AI | AI | human |
| **Strategic** | high · high | Lead with continuous oversight | human with AI | human with AI | human |
| **Routine** | low · low | Automate and monitor | AI | AI | AI |
| **Consequential** | low · high | Manage to ensure reliability | AI | AI | human |

## The kit on the matrix

| Kit operation | Quadrant | Frame | Act | Learn | Difference from the framework |
|---|---|---|---|---|---|
| `/query` | Exploratory | human with AI (the question) | AI (answers only from the wiki) | human (decides whether to save it as a synthesis page) | None |
| `/lint` | Routine | **script** (fixed rules in `lint.py`) | **script** | **script** (GREEN/RED); the human only looks when it turns RED | The actor is a script, not a model |
| `/ingest` | Consequential: everything else rests on the wiki | human with AI (5-step plan and a question) | human with AI (changes to existing pages arrive as a diff to approve) | human + script (lint GREEN and log) | More conservative, on purpose |
| `CLAUDE.md`, categories, new rules | Strategic | human with AI | human | human | None; rule 9 requires every rule to be born with its check |

## What the framework lacks and the kit adds

1. **A fourth participant: the rule or the script.** When the result must come out the same every time and be auditable, a language model does not decide. In the kit, the lint and the sha256 register of `raw/` are code.
2. **An exit lock.** Besides risk, what matters is whether something leaves or gets deleted: `raw/` is immutable, `wiki/log.md` only grows and pages are archived instead of deleted. None of that depends on the quadrant.
3. **Every operation declares its quadrant.** Each command in `.claude/commands/` states in one line its quadrant and who frames, acts and learns. The split is written down and does not rely on anyone's memory. The lint warns when a command does not declare it (MAESTRO rule 11).

## How to use it when you add an operation

1. Place it on the matrix: is it clear what has to be decided? How costly is a mistake?
2. If the result must be reproducible, let a script do it. The model writes and explains.
3. Add the `Quadrant:` line to the command, with who frames, acts and learns.
4. If it is consequential, make changes arrive as a diff to approve and finish with an automatic check.
