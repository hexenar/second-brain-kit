# Log de operaciones

Registro **append-only**: solo se añaden líneas al final; nunca se editan ni se borran las anteriores.
Escribe siempre con `python3 scripts/log.py . OP "descripción"` (OP = INGEST, QUERY o LINT).
Formato de cada línea: `AAAA-MM-DD | OP | descripción`

2026-09-18 | INGEST | 2026-09-01-ejemplo-articulo-repaso-espaciado: fuente [[articulo-repaso-espaciado]], concepto [[repaso-espaciado]]
2026-09-18 | INGEST | 2026-09-02-ejemplo-notas-equipo: entidad [[equipo-ejemplo]]
2026-09-18 | LINT | ROJO 3 fallos: enlace_roto [[curva-del-olvido]] en repaso-espaciado, huerfana equipo-ejemplo, caducada articulo-repaso-espaciado
2026-09-18 | LINT | arreglos: [[curva-del-olvido]] pasa a pendiente; enlace recíproco repaso-espaciado <-> equipo-ejemplo; caducidad de articulo-repaso-espaciado revisada a 2030-12-31 → VERDE 0 fallos
