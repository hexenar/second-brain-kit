#!/usr/bin/env python3
"""Crea un vault nuevo a partir de plantilla/ (o plantilla-en/) y le copia los scripts.

Uso: python3 init_vault.py <ruta> [--nombre X | --name X] [--lang es|en] [--force] [--git]
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

KIT = Path(__file__).resolve().parent
PLANTILLAS = {"es": KIT / "plantilla", "en": KIT / "plantilla-en"}
MARCADORES = {"es": "{{NOMBRE}}", "en": "{{NAME}}"}
SCRIPTS = ["lint.py", "log.py"]
CON_MARCADOR = {"CLAUDE.md", "wiki/index.md"}
IGNORAR = {".DS_Store", "__pycache__"}
# Lo leen lint.py y log.py para saber en qué idioma validar y responder.
MARCADOR_IDIOMA = ".second-brain.json"

TEXTOS = {
    "es": {
        "no_carpeta": "error: {destino} existe y no es una carpeta",
        "no_vacia": "error: {destino} ya existe y no está vacía. No se tocó nada.\n"
                    "Usa otra ruta, o --force para sobrescribir los archivos de plantilla "
                    "(incluidos wiki/index.md y wiki/log.md) sin borrar lo demás.",
        "creado": "Vault '{nombre}' creado en {destino} ({copiados} archivos).",
        "sin_git": "aviso: git no está instalado; se omitió git init (el vault quedó creado).",
        "git_ok": "Repositorio git inicializado.",
        "git_fallo": "aviso: git init falló ({e}); el vault quedó creado.",
        "siguiente": "Siguiente paso: abre la carpeta en Obsidian, mete fuentes en raw/ "
                     "y ejecuta /ingest desde Claude Code abierto en el vault.",
    },
    "en": {
        "no_carpeta": "error: {destino} exists and is not a folder",
        "no_vacia": "error: {destino} already exists and is not empty. Nothing was touched.\n"
                    "Use another path, or --force to overwrite the template files "
                    "(including wiki/index.md and wiki/log.md) without deleting anything else.",
        "creado": "Vault '{nombre}' created in {destino} ({copiados} files).",
        "sin_git": "warning: git is not installed; git init was skipped (the vault was created).",
        "git_ok": "Git repository initialized.",
        "git_fallo": "warning: git init failed ({e}); the vault was created.",
        "siguiente": "Next step: open the folder in Obsidian, put sources in raw/ "
                     "and run /ingest from Claude Code opened in the vault.",
    },
}


def archivos_plantilla(plantilla: Path):
    """Rutas relativas de todos los archivos de la plantilla, incluidos los ocultos."""
    for ruta in sorted(plantilla.rglob("*")):
        rel = ruta.relative_to(plantilla)
        if ruta.is_file() and not IGNORAR & set(rel.parts) and not ruta.name.endswith(".bak"):
            yield rel


def main() -> int:
    ap = argparse.ArgumentParser(description="Crea un vault (second brain) desde la plantilla del kit.")
    ap.add_argument("ruta", help="carpeta donde crear el vault")
    ap.add_argument("--nombre", "--name", dest="nombre",
                    help="nombre de la wiki (por defecto, el nombre de la carpeta)")
    ap.add_argument("--lang", choices=sorted(PLANTILLAS), default="es",
                    help="idioma del vault: es (plantilla/, por defecto) o en (plantilla-en/)")
    ap.add_argument("--force", action="store_true",
                    help="usar una carpeta no vacía: sobrescribe los archivos de plantilla sin borrar lo demás")
    ap.add_argument("--git", action="store_true", help="ejecutar git init en el vault")
    args = ap.parse_args()

    T = TEXTOS[args.lang]
    plantilla = PLANTILLAS[args.lang]
    marcador = MARCADORES[args.lang]
    destino = Path(args.ruta).expanduser()
    if destino.exists() and not destino.is_dir():
        print(T["no_carpeta"].format(destino=destino), file=sys.stderr)
        return 1
    if destino.is_dir() and any(destino.iterdir()) and not args.force:
        print(T["no_vacia"].format(destino=destino), file=sys.stderr)
        return 1

    nombre = args.nombre or destino.resolve().name
    copiados = 0
    for rel in archivos_plantilla(plantilla):
        salida = destino / rel
        salida.parent.mkdir(parents=True, exist_ok=True)
        if rel.as_posix() in CON_MARCADOR:
            texto = (plantilla / rel).read_text(encoding="utf-8")
            salida.write_text(texto.replace(marcador, nombre), encoding="utf-8")
        else:
            shutil.copyfile(plantilla / rel, salida)
        copiados += 1

    (destino / "scripts").mkdir(parents=True, exist_ok=True)
    for script in SCRIPTS:
        shutil.copyfile(KIT / "scripts" / script, destino / "scripts" / script)
        copiados += 1

    # Se escribe siempre (también con --force): el idioma elegido ahora manda.
    (destino / MARCADOR_IDIOMA).write_text(json.dumps({"lang": args.lang}) + "\n", encoding="utf-8")
    copiados += 1

    # El registro de hashes no es de plantilla: si ya existe (--force), se conserva.
    hashes = destino / "raw" / ".hashes.json"
    if not hashes.exists():
        hashes.write_text("{}\n", encoding="utf-8")
        copiados += 1

    print(T["creado"].format(nombre=nombre, destino=destino, copiados=copiados))

    if args.git:
        if shutil.which("git") is None:
            print(T["sin_git"])
        else:
            r = subprocess.run(["git", "init"], cwd=destino, capture_output=True, text=True)
            if r.returncode == 0:
                print(T["git_ok"])
            else:
                print(T["git_fallo"].format(e=r.stderr.strip()))

    print(T["siguiente"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
