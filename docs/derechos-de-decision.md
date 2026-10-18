# Quién decide qué: el kit sobre la matriz de decisiones IA

Este documento pone las operaciones del kit sobre un marco publicado: la **matriz de decisiones IA** de I. Sebastian, P. Weill, T. Haskamp y J. vom Brocke, «Designing Decision Rights for AI» (MIT Sloan, 2026). Aquí se resume con palabras propias; para el original, búscalo por título y autores. La clasificación de las operaciones del kit es nuestra, no de los autores.

## El marco en breve

Cada decisión tiene tres partes:

| Parte | Qué es |
|---|---|
| **Definir** | Plantear la decisión: qué se pregunta y con qué criterios. |
| **Actuar** | Tomar la acción o recomendarla. |
| **Aprender** | Hacerse dueño del resultado y mejorarlo. |

Y tres participantes posibles para cada parte: **humano**, **humano con IA** o **IA**.

Dos ejes ordenan las decisiones: **ambigüedad** (¿está claro qué hay que decidir?) y **riesgo** (¿cuánto cuesta equivocarse?). Salen cuatro cuadrantes:

| Cuadrante | Ambigüedad · riesgo | Enfoque | Definir | Actuar | Aprender |
|---|---|---|---|---|---|
| **Exploratorio** | alta · bajo | Habilitar: experimentar para aprender rápido | humano con IA | IA | humano |
| **Estratégico** | alta · alto | Liderar con supervisión continua | humano con IA | humano con IA | humano |
| **Rutina** | baja · bajo | Automatizar y vigilar | IA | IA | IA |
| **Consecuencial** | baja · alto | Gestionar para asegurar fiabilidad | IA | IA | humano |

## El kit sobre la matriz

| Operación del kit | Cuadrante | Definir | Actuar | Aprender | Diferencia con el marco |
|---|---|---|---|---|---|
| `/query` | Exploratorio | humano con IA (la pregunta) | IA (responde solo desde la wiki) | humano (decide si se guarda como síntesis) | Ninguna |
| `/lint` | Rutina | **script** (reglas fijas en `lint.py`) | **script** | **script** (VERDE/ROJO); el humano solo mira si sale ROJO | El que actúa es un script, no un modelo |
| `/ingest` | Consecuencial: todo lo demás se apoya en la wiki | humano con IA (plan de 5 pasos y pregunta) | humano con IA (los cambios a páginas existentes llegan como diff para aprobar) | humano + script (lint en VERDE y log) | Más conservador, a propósito |
| `CLAUDE.md`, categorías, reglas nuevas | Estratégico | humano con IA | humano | humano | Ninguna; la regla 9 obliga a que cada regla nazca con su chequeo |

## Lo que el marco no trae y el kit añade

1. **Un cuarto participante: la regla o el script.** Cuando el resultado tiene que salir igual cada vez y poder auditarse, no decide un modelo de lenguaje. En el kit, el lint y el registro sha256 de `raw/` son código.
2. **Un candado de salida.** Además del riesgo cuenta si algo sale o se borra: `raw/` es inmutable, `wiki/log.md` solo crece y las páginas se archivan en vez de borrarse. Nada de eso depende del cuadrante.
3. **Cada operación declara su cuadrante.** Cada comando de `.claude/commands/` dice en una línea en qué cuadrante está y quién define, actúa y aprende. Así el reparto queda escrito y no depende de la memoria de nadie. El lint avisa si un comando no lo declara (regla MAESTRO 11).

## Cómo usarlo al crear una operación nueva

1. Ubícala en la matriz: ¿está claro qué hay que decidir? ¿cuánto cuesta equivocarse?
2. Si el resultado debe ser reproducible, que lo haga un script. El modelo redacta y explica.
3. Escribe la línea `Cuadrante:` en el comando, con quién define, actúa y aprende.
4. Si es consecuencial, que los cambios lleguen como diff para aprobar y que termine con un chequeo automático.
