# Log de operaciones

Registro **append-only**: solo se añaden líneas al final; nunca se editan ni se borran las anteriores.
Escribe siempre con `python3 scripts/log.py . OP "descripción"` (OP = INGEST, QUERY o LINT).
Formato de cada línea: `AAAA-MM-DD | OP | descripción`

