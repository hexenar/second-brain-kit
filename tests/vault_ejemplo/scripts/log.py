#!/usr/bin/env python3
"""Registra una operación en wiki/log.md (solo añade al final; nunca reescribe)
y, con --raw, guarda el sha256 de cada fuente la primera vez que se ingiere.

Uso:    python3 scripts/log.py <vault> INGEST|QUERY|LINT "descripción" [--raw raw/archivo ...] [--fecha AAAA-MM-DD] [--lang es|en]
Salida: exit 0 si registró; 2 si hubo un error (y en ese caso no escribe nada).
Idioma de los mensajes: --lang si se da; si no, el de .second-brain.json del vault; si no, español.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import re
import sys
from pathlib import Path

# Las operaciones son las mismas palabras en los dos idiomas.
OPERACIONES = ("INGEST", "QUERY", "LINT")
IDIOMAS = ("es", "en")
MARCADOR_IDIOMA = ".second-brain.json"

TEXTOS = {
    "es": {
        "operacion": "operación '{op}' no válida (usa: {lista})",
        "fecha": "fecha inválida '{texto}' (usa AAAA-MM-DD)",
        "vacia": "la descripción está vacía",
        "sin_log": "no existe {log} (¿es la carpeta de un vault?)",
        "sin_archivo": "no existe el archivo {texto}",
        "fuera": "{texto} está fuera del vault",
        "no_raw": "{texto} no está dentro de raw/",
        "hashes_json": "raw/.hashes.json no es JSON válido; restáuralo antes de seguir",
        "ya_registrado": "Hash ya registrado (se conserva el original): {rel}",
        "registrado": "Hash registrado: {rel}",
        "linea": "Registrado en wiki/log.md: {linea}",
    },
    "en": {
        "operacion": "operation '{op}' is not valid (use: {lista})",
        "fecha": "invalid date '{texto}' (use YYYY-MM-DD)",
        "vacia": "the description is empty",
        "sin_log": "{log} does not exist (is this a vault folder?)",
        "sin_archivo": "file {texto} does not exist",
        "fuera": "{texto} is outside the vault",
        "no_raw": "{texto} is not inside raw/",
        "hashes_json": "raw/.hashes.json is not valid JSON; restore it before continuing",
        "ya_registrado": "Hash already registered (the original is kept): {rel}",
        "registrado": "Hash registered: {rel}",
        "linea": "Logged in wiki/log.md: {linea}",
    },
}


def idioma_vault(vault: Path, forzado=None) -> str:
    """--lang si se dio; si no, el de .second-brain.json; si no, "es" (vaults sin marcador)."""
    if forzado:
        return forzado
    try:
        idioma = json.loads((vault / MARCADOR_IDIOMA).read_text(encoding="utf-8")).get("lang")
    except (OSError, ValueError, AttributeError):
        return "es"
    return idioma if idioma in IDIOMAS else "es"


def error(mensaje: str) -> None:
    print(f"error: {mensaje}", file=sys.stderr)
    sys.exit(2)


def leer_fecha(texto: str | None, T: dict) -> str:
    if texto is None:
        return dt.date.today().isoformat()
    try:
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", texto):
            raise ValueError
        return dt.date.fromisoformat(texto).isoformat()
    except ValueError:
        error(T["fecha"].format(texto=texto))


def main() -> int:
    ap = argparse.ArgumentParser(description="Añade una línea a wiki/log.md y registra hashes de raw/.")
    ap.add_argument("vault", help="carpeta del vault")
    ap.add_argument("operacion", help="INGEST, QUERY o LINT")
    ap.add_argument("descripcion", help="descripción breve (una línea)")
    ap.add_argument("--raw", nargs="+", action="extend", default=[], metavar="raw/ARCHIVO",
                    help="fuentes ingeridas: registra su sha256 si aún no lo está")
    ap.add_argument("--fecha", help="fecha AAAA-MM-DD (por defecto, hoy)")
    ap.add_argument("--lang", choices=IDIOMAS,
                    help=f"idioma de los mensajes (por defecto, el de {MARCADOR_IDIOMA}; si no hay, es)")
    args = ap.parse_args()

    vault = Path(args.vault)
    T = TEXTOS[idioma_vault(vault, args.lang)]
    if args.operacion not in OPERACIONES:
        error(T["operacion"].format(op=args.operacion, lista=", ".join(OPERACIONES)))
    fecha = leer_fecha(args.fecha, T)
    descripcion = re.sub(r"\r\n|\r|\n", " ", args.descripcion).strip()
    if not descripcion:
        error(T["vacia"])

    log = vault / "wiki" / "log.md"
    if not log.is_file():
        error(T["sin_log"].format(log=log))

    # Se valida todo antes de escribir, para no dejar un registro a medias.
    fuentes = []
    raiz = vault.resolve()
    for texto in args.raw:
        ruta = Path(texto) if Path(texto).is_absolute() else vault / texto
        if not ruta.is_file():
            error(T["sin_archivo"].format(texto=texto))
        try:
            rel = ruta.resolve().relative_to(raiz).as_posix()
        except ValueError:
            error(T["fuera"].format(texto=texto))
        if not rel.startswith("raw/"):
            error(T["no_raw"].format(texto=texto))
        fuentes.append((rel, ruta))

    registro = vault / "raw" / ".hashes.json"
    hashes = {}
    if registro.is_file():
        try:
            hashes = json.loads(registro.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            error(T["hashes_json"])

    # El primer hash es la referencia de inmutabilidad: nunca se sobrescribe.
    nuevos = 0
    for rel, ruta in fuentes:
        if rel in hashes:
            print(T["ya_registrado"].format(rel=rel))
        else:
            hashes[rel] = hashlib.sha256(ruta.read_bytes()).hexdigest()
            nuevos += 1
            print(T["registrado"].format(rel=rel))
    if nuevos:
        registro.write_text(json.dumps(hashes, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                            encoding="utf-8")

    linea = f"{fecha} | {args.operacion} | {descripcion}"
    tamano = log.stat().st_size
    separador = b""
    if tamano:
        with log.open("rb") as f:
            f.seek(tamano - 1)
            if f.read(1) != b"\n":
                separador = b"\n"
    with log.open("ab") as f:  # modo append: las líneas previas no se tocan
        f.write(separador + (linea + "\n").encode("utf-8"))
    print(T["linea"].format(linea=linea))
    return 0


if __name__ == "__main__":
    sys.exit(main())
