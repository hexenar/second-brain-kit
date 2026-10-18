# Operations log

An **append-only** record: lines are only added at the end; earlier ones are never edited or deleted.
Always write with `python3 scripts/log.py . OP "description"` (OP = INGEST, QUERY or LINT).
Format of each line: `YYYY-MM-DD | OP | description`

