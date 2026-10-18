# Operations log

An **append-only** record: lines are only added at the end; earlier ones are never edited or deleted.
Always write with `python3 scripts/log.py . OP "description"` (OP = INGEST, QUERY or LINT).
Format of each line: `YYYY-MM-DD | OP | description`

2026-09-18 | INGEST | 2026-09-01-example-article-spaced-repetition: source [[article-spaced-repetition]], concept [[spaced-repetition]]
2026-09-18 | INGEST | 2026-09-02-example-team-notes: entity [[example-team]]
2026-09-18 | LINT | RED 3 failures: broken_link [[forgetting-curve]] in spaced-repetition, orphan example-team, expired article-spaced-repetition
2026-09-18 | LINT | fixes: [[forgetting-curve]] becomes pending; reciprocal link spaced-repetition <-> example-team; expires of article-spaced-repetition reviewed to 2030-12-31 → GREEN 0 failures
