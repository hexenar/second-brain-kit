---
description: Responde una pregunta SOLO con lo que está en la wiki, con citas y confianza explícita
argument-hint: <pregunta>
---

# QUERY: $ARGUMENTS

Operación declarada: **QUERY**. Sigue `CLAUDE.md` en todo.
Cuadrante: **Exploratorio** · define: humano con IA · actúa: IA · aprende: humano

1. **Lee `wiki/index.md` primero.** Elige las páginas relevantes a partir del índice y lee solo esas (sigue sus enlaces si hace falta). No barras carpetas.
2. **Responde solo desde la wiki.** Cada afirmación lleva la página de donde sale (`[[pagina]]`) y la fuente de `raw/` que esa página cita. No añadas nada de memoria (regla MAESTRO 10).
3. **Si la wiki no lo cubre** (del todo o en parte), dilo explícitamente: «la wiki no cubre X». Si ayuda, sugiere qué tipo de fuente habría que meter en `raw/` e ingerir.
4. **Señala tensiones**: contradicciones entre páginas, páginas caducadas o con confianza baja que sostengan la respuesta.
5. **Cierra con la confianza**: `**Confianza:** X — motivo` (con «fuente única: raw/...» si todo descansa en una sola fuente).
6. **Ofrece guardarla** como página `tipo: sintesis` en `wiki/` (raíz). Solo si el usuario acepta:
   - nombre kebab-case sin acentos; frontmatter completo; `fuentes` = las `raw/` de las páginas usadas;
   - enlaces a las páginas usadas y, en cada una, el enlace de vuelta (como diff, con OK);
   - añádela a `wiki/index.md` → «## Síntesis»;
   - corre `python3 scripts/lint.py .` y deja el resultado en VERDE.
7. **Registra**:

```bash
python3 scripts/log.py . QUERY "<pregunta resumida> → <respondida | no cubierta | guardada como [[pagina]]>"
```
