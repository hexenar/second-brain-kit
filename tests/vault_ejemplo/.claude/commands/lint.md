---
description: Revisa la salud de la wiki (lint programático + revisión a juicio) y propone arreglos como diff
argument-hint: "[foco opcional: página o tema]"
---

# LINT

Operación declarada: **LINT**. Sigue `CLAUDE.md` en todo.
Cuadrante: **Rutina** · define, actúa y aprende: el script (`scripts/lint.py`); el humano revisa si sale ROJO

Foco indicado por el usuario (puede estar vacío): $ARGUMENTS
El lint programático corre siempre sobre toda la wiki; el foco solo prioriza la revisión a juicio.

## 1. Lint programático

```bash
python3 scripts/lint.py .
python3 scripts/lint.py . --json     # si necesitas procesar la lista de fallos
```

Primera línea: `LINT: VERDE (0 fallos)` o `LINT: ROJO (N fallos)`. Exit 0 = verde, 1 = rojo, 2 = error al correrlo.

## 2. Interpretar cada fallo

Para cada fallo: explica qué significa en esa página y **propón el arreglo como diff**. No apliques nada sin OK.

| Tipo | Arreglo habitual |
|---|---|
| `frontmatter` | Completar o corregir el campo indicado (formato en `CLAUDE.md`). |
| `categoria` | Usar una categoría de `CATEGORIAS`; si de verdad hace falta otra, proponer el cambio en `scripts/lint.py` como decisión aparte. |
| `enlace_roto` | Corregir el nombre, o convertirlo en `[[pendiente:x]]` si la página aún no existe. |
| `huerfana` | Enlazarla desde las páginas con relación real (y recíproco); si no tiene ninguna, preguntar si se archiva. |
| `no_reciproco` | Añadir el enlace de vuelta en la página destino (o quitar el de ida si la relación no era real). |
| `caducada` | Revisar el contenido contra sus fuentes; actualizar `fecha` y `caducidad` (y `confianza` si cambia). |
| `index_falta` / `index_sobra` | Añadir la página al índice / quitar o corregir la línea del índice. |
| `raw_modificado` | **Nunca** se arregla editando `raw/` ni el hash. Preguntar al usuario: restaurar el original, o tratar la versión nueva como fuente nueva (otro nombre con fecha) e ingerirla. |
| `raw_desaparecido` | Preguntar al usuario: restaurar el archivo, o archivar las páginas que dependían de él. |
| `fuente_inexistente` | Corregir la ruta en `fuentes`, o preguntar por el archivo que falta. |

Los **avisos** (`raw_sin_hash`) indican fuentes en `raw/` que aún no se han ingerido: lístalas como candidatas a `/ingest`.
El aviso `comando_sin_cuadrante` señala un comando de `.claude/commands/` sin su línea `Cuadrante:` (regla MAESTRO 11): propón añadirla como diff.
El aviso `wiki_mayor_que_raw` (solo con ≥ 100 KB en `raw/`) señala una wiki que pesa más que sus fuentes: busca las páginas que copian la fuente y propón resumirlas.

## 3. Revisión a juicio (no programática)

Revisa y reporta, con propuesta concreta para cada hallazgo:

- **Contradicciones** entre páginas (misma afirmación con datos distintos): cítalas lado a lado con sus fuentes.
- **Afirmaciones caducas**: páginas con `fecha` antigua en temas que cambian rápido, o con `caducidad` próxima.
- **Huecos**: `[[pendiente:x]]` que ya podrían promoverse (búscalos con `grep -rn "pendiente:" wiki/`); conceptos o entidades mencionados en varias páginas sin página propia.
- **Reglas sin chequeo automático**: sección «Paso escéptico» en cada página de fuente; cita `raw/` en las afirmaciones; línea final de confianza; claims > 0.7 sin intento de refutación; prefijo `AAAA-MM-DD-` en `raw/`; nombres kebab-case sin acentos.

## 4. Registrar

```bash
python3 scripts/log.py . LINT "<VERDE | ROJO N fallos>; <arreglos aplicados>; <hallazgos a juicio>"
```

Si aplicaste arreglos, vuelve a correr `python3 scripts/lint.py .` y reporta el estado final.
