#!/usr/bin/env python3
"""Empaqueta el kit en UN solo archivo markdown autocontenido, pensado para
pasárselo a Claude Code y que lo reconstruya byte a byte.

Uso: python3 empaquetar.py [--lang es|en] [--salida RUTA]
     (por defecto: dist/INSTRUCTIVO_second-brain-kit.md; con --lang en,
     dist/INSTRUCTIONS_second-brain-kit_en.md)

Los dos idiomas llevan exactamente los mismos archivos; cambian el encabezado
para Claude Code y el README que va como sección para humanos.
"""
from __future__ import annotations

import argparse
import hashlib
import os
import re
import sys
from pathlib import Path

KIT = Path(__file__).resolve().parent
SALIDAS = {"es": KIT / "dist" / "INSTRUCTIVO_second-brain-kit.md",
           "en": KIT / "dist" / "INSTRUCTIONS_second-brain-kit_en.md"}
READMES = {"es": "README.md", "en": "README.en.md"}
EXCLUIR = {".venv", "__pycache__", ".pytest_cache", ".git", ".DS_Store"}
LENGUAJES = {".py": "python", ".md": "markdown", ".json": "json", ".sh": "bash",
             ".yml": "yaml", ".yaml": "yaml", ".txt": "text"}

ENCABEZADO = """\
# INSTRUCTIVO — second-brain-kit (paquete en un solo archivo)

> **Si eres Claude Code y el usuario te pasó este archivo:**
>
> 1. Pregunta en qué carpeta crear `second-brain-kit/` (por defecto, el directorio actual). Si `second-brain-kit/` ya existe y no está vacía, aborta salvo confirmación explícita del usuario.
> 2. Escribe cada archivo del bloque «Archivos» byte por byte, sin modificar nada (ni espacios, ni saltos de línea, ni «mejoras»).
> 3. Crea un entorno virtual con Python 3.10+ e instala `pyyaml pytest`.
> 4. Corre `pytest` y `scripts/lint.py tests/vault_ejemplo`, y muestra los resultados al usuario.
> 5. Luego guía al usuario por el «Arranque en 30 minutos» del README, paso a paso, esperando su confirmación entre pasos.

## Detalles para reconstruir (paso 2)

- La sección `## Archivos` es la última de este documento. Cada archivo empieza con una línea `### ruta/relativa` seguida de un bloque de código cercado.
- El contenido del archivo es **exactamente** el texto entre la línea de apertura (N comillas invertidas + lenguaje) y la línea de cierre (las mismas N comillas invertidas, solas). Cada cerca es más larga que cualquier racha de comillas invertidas o tildes del archivo, así que las cercas internas (```` ``` ````) son contenido, no cierre.
- Los archivos vacíos (`.gitkeep`) tienen el bloque vacío. Todo archivo no vacío termina en salto de línea.
- Incluye archivos ocultos (`.claude/`, `.gitkeep`, `.hashes.json`, `.gitignore`, `.second-brain.json`): créalos también.
- Lo más fiable es escribir un script de Python de un solo uso que lea este archivo y cree los archivos, en vez de copiarlos a mano; después comprueba bytes y sha256 contra el manifiesto de la sección «Archivos».
- Pasos 3 y 4 (macOS/Linux; en Windows usa `.venv\\Scripts\\` en lugar de `.venv/bin/`):

```bash
cd second-brain-kit
python3 -m venv .venv
.venv/bin/pip install pyyaml pytest
.venv/bin/pytest -q
.venv/bin/python scripts/lint.py tests/vault_ejemplo
```

Resultado esperado: todas las pruebas pasan y el lint del vault de ejemplo da `LINT: VERDE (0 fallos)`.
"""

ENCABEZADO_EN = """\
# INSTRUCTIONS — second-brain-kit (single-file package)

> **If you are Claude Code and the user gave you this file:**
>
> 1. Ask in which folder to create `second-brain-kit/` (by default, the current directory). If `second-brain-kit/` already exists and is not empty, abort unless the user explicitly confirms.
> 2. Write every file in the "Files" block byte for byte, without changing anything (no spaces, no line breaks, no "improvements").
> 3. Create a virtual environment with Python 3.10+ and install `pyyaml pytest`.
> 4. Run `pytest` and `scripts/lint.py tests/vault_example_en`, and show the results to the user.
> 5. Then guide the user through the README's "Start in 30 minutes", step by step, waiting for their confirmation between steps.

## Rebuild details (step 2)

- The `## Files` section is the last one in this document. Each file starts with a `### relative/path` line followed by a fenced code block.
- The file's content is **exactly** the text between the opening line (N backticks + language) and the closing line (the same N backticks, alone). Each fence is longer than any run of backticks or tildes in the file, so inner fences (```` ``` ````) are content, not a closing fence.
- Empty files (`.gitkeep`) have an empty block. Every non-empty file ends with a line break.
- Hidden files are included (`.claude/`, `.gitkeep`, `.hashes.json`, `.gitignore`, `.second-brain.json`): create them too.
- The most reliable way is to write a one-off Python script that reads this file and creates the files, instead of copying them by hand; then check bytes and sha256 against the manifest in the "Files" section.
- Steps 3 and 4 (macOS/Linux; on Windows use `.venv\\Scripts\\` instead of `.venv/bin/`):

```bash
cd second-brain-kit
python3 -m venv .venv
.venv/bin/pip install pyyaml pytest
.venv/bin/pytest -q
.venv/bin/python scripts/lint.py tests/vault_example_en
```

Expected result: all tests pass and the lint of the example vault gives `LINT: GREEN (0 failures)`.
"""

# Textos del paquete por idioma; los archivos y el manifiesto no cambian.
PAQUETE = {
    "es": {"encabezado": ENCABEZADO,
           "humanos": "<!-- Sección para humanos: copia literal del README.md del kit. -->\n\n",
           "seccion": "## Archivos\n\n",
           "manifiesto": "{n} archivos. Manifiesto para verificar la reconstrucción:\n\n",
           "tabla": "| Archivo | Bytes | sha256 |\n|---|---|---|\n"},
    "en": {"encabezado": ENCABEZADO_EN,
           "humanos": "<!-- Section for humans: literal copy of the kit's README.en.md. -->\n\n",
           "seccion": "## Files\n\n",
           "manifiesto": "{n} files. Manifest to verify the rebuild:\n\n",
           "tabla": "| File | Bytes | sha256 |\n|---|---|---|\n"},
}


def archivos_kit(raiz: Path = KIT) -> list:
    """Rutas relativas (posix) de los archivos que entran en el paquete."""
    salida = []
    for carpeta, subcarpetas, archivos in os.walk(raiz):
        rel = Path(carpeta).relative_to(raiz)
        subcarpetas[:] = [d for d in subcarpetas
                          if d not in EXCLUIR and not (rel == Path(".") and d == "dist")]
        for nombre in archivos:
            if nombre in EXCLUIR or nombre.endswith(".bak") or ".bak-" in nombre:
                continue
            salida.append((rel / nombre).as_posix())
    return sorted(salida)


def cerca(texto: str) -> str:
    """Cerca de comillas invertidas más larga que cualquier racha de ` o ~ del texto."""
    rachas = [len(m.group(0)) for m in re.finditer(r"`+|~+", texto)]
    return "`" * max(3, max(rachas, default=0) + 1)


def construir(raiz: Path = KIT, idioma: str = "es") -> str:
    """Devuelve el markdown completo del paquete en el idioma pedido."""
    rutas = archivos_kit(raiz)
    manifiesto, bloques = [], []
    for rel in rutas:
        datos = (raiz / rel).read_bytes()
        try:
            texto = datos.decode("utf-8")
        except UnicodeDecodeError:
            sys.exit(f"error: {rel} no es texto UTF-8; el paquete solo admite archivos de texto")
        if texto and not texto.endswith("\n"):
            sys.exit(f"error: {rel} no termina en salto de línea; añádelo y vuelve a empaquetar")
        manifiesto.append(f"| `{rel}` | {len(datos)} | `{hashlib.sha256(datos).hexdigest()}` |")
        f = cerca(texto)
        bloques.append(f"### {rel}\n\n{f}{LENGUAJES.get(Path(rel).suffix, '')}\n{texto}{f}\n")

    P = PAQUETE[idioma]
    readme = (raiz / READMES[idioma]).read_text(encoding="utf-8")
    partes = [
        P["encabezado"],
        "\n---\n\n",
        P["humanos"],
        readme,
        "\n---\n\n",
        P["seccion"],
        P["manifiesto"].format(n=len(rutas)),
        P["tabla"],
        "\n".join(manifiesto) + "\n\n",
        "\n".join(bloques),
    ]
    return "".join(partes)


def main() -> int:
    ap = argparse.ArgumentParser(description="Genera el instructivo de un solo archivo del kit.")
    ap.add_argument("--lang", choices=sorted(SALIDAS), default="es",
                    help="idioma del paquete: es (README.md, por defecto) o en (README.en.md)")
    ap.add_argument("--salida", type=Path, help="ruta del .md de salida (por defecto, la de dist/ del idioma)")
    args = ap.parse_args()
    salida = args.salida or SALIDAS[args.lang]
    contenido = construir(KIT, args.lang)
    salida.parent.mkdir(parents=True, exist_ok=True)
    salida.write_bytes(contenido.encode("utf-8"))
    print(f"Paquete generado: {salida} ({len(archivos_kit())} archivos, "
          f"{salida.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
