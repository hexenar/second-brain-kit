---
description: Answer a question ONLY with what is in the wiki, with citations and explicit confidence
argument-hint: <question>
---

# QUERY: $ARGUMENTS

Declared operation: **QUERY**. Follow `CLAUDE.md` in everything.
Quadrant: **Exploratory** · frames: human with AI · acts: AI · learns: human

1. **Read `wiki/index.md` first.** Choose the relevant pages from the index and read only those (follow their links if needed). Do not sweep folders.
2. **Answer only from the wiki.** Every claim carries the page it comes from (`[[page]]`) and the `raw/` source that page cites. Add nothing from memory (MAESTRO rule 10).
3. **If the wiki does not cover it** (fully or partly), say so explicitly: "the wiki does not cover X". If it helps, suggest what kind of source should be put in `raw/` and ingested.
4. **Point out tensions**: contradictions between pages, and expired or low-confidence pages that the answer rests on.
5. **Close with the confidence**: `**Confidence:** X — reason` (with "single source: raw/..." if everything rests on a single source).
6. **Offer to save it** as a `type: synthesis` page in `wiki/` (root). Only if the user accepts:
   - kebab-case name without accents; complete frontmatter; `sources` = the `raw/` files of the pages used;
   - links to the pages used and, in each of them, the link back (as a diff, with OK);
   - add it to `wiki/index.md` → "## Synthesis";
   - run `python3 scripts/lint.py .` and leave the result GREEN.
7. **Log it**:

```bash
python3 scripts/log.py . QUERY "<summarized question> → <answered | not covered | saved as [[page]]>"
```
