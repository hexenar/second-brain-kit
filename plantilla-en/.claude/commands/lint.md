---
description: Check the wiki's health (programmatic lint + judgment review) and propose fixes as a diff
argument-hint: "[optional focus: page or topic]"
---

# LINT

Declared operation: **LINT**. Follow `CLAUDE.md` in everything.
Quadrant: **Routine** · frames, acts and learns: the script (`scripts/lint.py`); the human reviews if it comes out RED

Focus given by the user (may be empty): $ARGUMENTS
The programmatic lint always runs over the whole wiki; the focus only sets priorities for the judgment review.

## 1. Programmatic lint

```bash
python3 scripts/lint.py .
python3 scripts/lint.py . --json     # if you need to process the list of failures
```

First line: `LINT: GREEN (0 failures)` or `LINT: RED (N failures)`. Exit 0 = green, 1 = red, 2 = error while running it.

## 2. Interpret each failure

For each failure: explain what it means on that page and **propose the fix as a diff**. Apply nothing without OK.

| Type | Usual fix |
|---|---|
| `frontmatter` | Complete or correct the indicated field (format in `CLAUDE.md`). |
| `category` | Use a category from `CATEGORIAS["en"]`; if another one is truly needed, propose the change in `scripts/lint.py` as a separate decision. |
| `broken_link` | Correct the name, or turn it into `[[pending:x]]` if the page does not exist yet. |
| `orphan` | Link it from the pages with a real relationship (and reciprocally); if it has none, ask whether to archive it. |
| `not_reciprocal` | Add the link back in the target page (or remove the outgoing one if the relationship was not real). |
| `expired` | Review the content against its sources; update `date` and `expires` (and `confidence` if it changes). |
| `index_missing` / `index_extra` | Add the page to the index / remove or correct the index line. |
| `raw_modified` | **Never** fixed by editing `raw/` or the hash. Ask the user: restore the original, or treat the new version as a new source (another dated name) and ingest it. |
| `raw_missing` | Ask the user: restore the file, or archive the pages that depended on it. |
| `missing_source` | Correct the path in `sources`, or ask about the missing file. |

The **warnings** (`raw_unhashed`) point to sources in `raw/` that have not been ingested yet: list them as candidates for `/ingest`.
The `command_without_quadrant` warning flags a command in `.claude/commands/` without its `Quadrant:` line (MAESTRO rule 11): propose adding it as a diff.
The `wiki_larger_than_raw` warning (only with ≥ 100 KB in `raw/`) flags a wiki that weighs more than its sources: find the pages that copy their source and propose summarizing them.

## 3. Judgment review (not programmatic)

Review and report, with a concrete proposal for each finding:

- **Contradictions** between pages (the same claim with different data): quote them side by side with their sources.
- **Stale claims**: pages with an old `date` on fast-moving topics, or with an `expires` date coming up.
- **Gaps**: `[[pending:x]]` links that could already be promoted (find them with `grep -rn "pending:" wiki/`); concepts or entities mentioned in several pages without a page of their own.
- **Rules without an automatic check**: a "Skeptical pass" section in every source page; a `raw/` citation on each claim; a closing confidence line; claims > 0.7 without a refutation attempt; the `YYYY-MM-DD-` prefix in `raw/`; kebab-case names without accents.

## 4. Log

```bash
python3 scripts/log.py . LINT "<GREEN | RED N failures>; <fixes applied>; <judgment findings>"
```

If you applied fixes, run `python3 scripts/lint.py .` again and report the final state.
