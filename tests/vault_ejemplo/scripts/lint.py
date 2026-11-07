#!/usr/bin/env python3
"""Lint de la wiki: frontmatter, categorías, enlaces, huérfanas, reciprocidad,
caducidad, índice, integridad de raw/, cuadrante declarado en cada comando y
tamaño de la wiki frente a sus fuentes.

Uso:    python3 scripts/lint.py [vault] [--json] [--hoy AAAA-MM-DD] [--lang es|en]
Salida: exit 0 si VERDE (sin fallos), 1 si ROJO (hay fallos), 2 si error de uso.
Idioma: --lang si se da; si no, el de .second-brain.json del vault; si no, español.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import re
import sys
from pathlib import Path

try:
    import yaml
except ImportError:  # se avisa en main(), cuando ya se sabe el idioma del vault
    yaml = None

# --- Configuración por idioma (se edita a propósito, nunca de pasada) ----------
# Lista cerrada de categorías: una categoría nueva se añade AQUÍ, de forma
# deliberada, para que la taxonomía no crezca sola con cada ingesta.
CATEGORIAS = {
    "es": ["IA", "Medicina", "Negocio", "Metodo", "General"],
    "en": ["AI", "Medicine", "Business", "Method", "General"],
}
TIPOS = {
    "es": ["concepto", "entidad", "fuente", "sintesis"],
    "en": ["concept", "entity", "source", "synthesis"],
}
# Mismo orden en los dos idiomas: revisar_meta los desempaqueta por posición.
CAMPOS_OBLIGATORIOS = {
    "es": ["titulo", "tipo", "categoria", "fuentes", "fecha", "confianza", "caducidad"],
    "en": ["title", "type", "category", "sources", "date", "confidence", "expires"],
}
# Marca de página archivada (regla MAESTRO 6). Vive aquí para que la convención
# de cada idioma esté en un solo sitio; ningún chequeo trata distinto esas páginas.
MARCA_ARCHIVO = {"es": ("estado", "archivo"), "en": ("status", "archived")}
# Una wiki que pesa más que sus fuentes probablemente copia en vez de destilar
# (Anthropic, «The components of agent memory», 2026: 115 KB de fuentes → 203 KB de wiki).
UMBRAL_TAMANO_WIKI = 1.0
# Con menos de ~100 KB de fuentes la razón no informa: las páginas de concepto y
# entidad agregan varias fuentes, así que una wiki pequeña suele pesar más que raw/.
MINIMO_RAW_KB = 100
# -----------------------------------------------------------------------------

IDIOMAS = ("es", "en")
MARCADOR_IDIOMA = ".second-brain.json"

# Orden en que se agrupan los fallos en el reporte (ids internos, en español).
TIPOS_FALLO = [
    "frontmatter", "categoria", "enlace_roto", "huerfana", "no_reciproco",
    "caducada", "index_falta", "index_sobra", "raw_modificado",
    "raw_desaparecido", "fuente_inexistente",
]
# Id que ve el usuario de un vault en inglés; en español se usa el id interno.
IDS_EN = {
    "frontmatter": "frontmatter", "categoria": "category", "enlace_roto": "broken_link",
    "huerfana": "orphan", "no_reciproco": "not_reciprocal", "caducada": "expired",
    "index_falta": "index_missing", "index_sobra": "index_extra",
    "raw_modificado": "raw_modified", "raw_desaparecido": "raw_missing",
    "fuente_inexistente": "missing_source", "raw_sin_hash": "raw_unhashed",
    "comando_sin_cuadrante": "command_without_quadrant", "wiki_mayor_que_raw": "wiki_larger_than_raw",
}
# Claves del JSON de un vault en inglés (en español se conservan las de siempre).
CLAVES_EN = {"estado": "status", "fallos": "failures", "avisos": "warnings", "paginas": "pages",
             "tipo": "type", "archivo": "file", "detalle": "detail"}

TEXTOS = {
    "es": {
        "VERDE": "VERDE", "ROJO": "ROJO", "fallo": ("fallo", "fallos"),
        "cabecera": "Vault: {vault} · páginas: {paginas} · hoy: {hoy}",
        "avisos": "Avisos (no cambian el resultado): {n}",
        "sin_avisos": "Avisos: ninguno",
        "prefijo_cuadrante": "Cuadrante:",
        "sin_frontmatter": "falta el bloque de frontmatter YAML (--- ... ---) al inicio",
        "yaml_invalido": "YAML inválido: {e}",
        "no_es_mapa": "el frontmatter debe ser un mapa de campos (clave: valor)",
        "campo_vacio": "campo obligatorio ausente o vacío: {campo}",
        "tipo_invalido": "tipo '{valor}' no válido (usa: {lista})",
        "categoria": "categoría '{valor}' fuera de la lista cerrada ({lista}); "
                     "para añadir una, edita CATEGORIAS en scripts/lint.py",
        "confianza_no_numero": "confianza debe ser un número entre 0 y 1 (valor: {valor!r})",
        "confianza_rango": "confianza {valor} fuera del rango [0, 1]",
        "fecha_formato": "{campo} debe tener formato AAAA-MM-DD (valor: {valor!r})",
        "caducada": "caducidad {fecha} anterior a hoy ({hoy})",
        "fuentes_lista": "fuentes debe ser una lista (- raw/...)",
        "fuente_inexistente": "{fuente} no existe en disco",
        "enlace_roto": "[[{destino}]] no corresponde a ninguna página de wiki/",
        "huerfana": "ninguna otra página enlaza aquí (los enlaces de index.md y log.md no cuentan)",
        "no_reciproco": "enlaza a [[{destino}]], pero {pagina} no enlaza de vuelta a [[{origen}]]",
        "index_falta": "la página no está enlazada en wiki/index.md",
        "index_sobra": "[[{destino}]] apunta a una página que no existe",
        "hashes_json": "raw/.hashes.json no es JSON válido ({e}); restáuralo desde git o una copia",
        "hashes_objeto": "raw/.hashes.json debe ser un objeto {{\"raw/archivo\": \"sha256\"}}",
        "raw_desaparecido": "registrado en raw/.hashes.json pero ya no existe",
        "raw_modificado": "el contenido cambió desde que se registró (sha256 distinto); raw/ es inmutable",
        "raw_sin_hash": "sin hash en raw/.hashes.json; se registra al ingerirla (scripts/log.py --raw)",
        "sin_cuadrante": "no declara su cuadrante: falta una línea que empiece por «Cuadrante:» "
                         "(regla MAESTRO 11)",
        "wiki_mayor_que_raw": "la wiki pesa {wiki:.1f} KB y sus fuentes {raw:.1f} KB ({ratio:.2f}×): "
                              "una wiki debería destilar, no copiar; revisa páginas que repiten la fuente",
        "sin_yaml": "error: falta PyYAML. Instálalo con: pip install pyyaml",
        "hoy_invalida": "argument --hoy: fecha inválida '{valor}' (usa AAAA-MM-DD)",
        "no_es_vault": "error: {vault} no parece un vault (no tiene carpeta wiki/)",
    },
    "en": {
        "VERDE": "GREEN", "ROJO": "RED", "fallo": ("failure", "failures"),
        "cabecera": "Vault: {vault} · pages: {paginas} · today: {hoy}",
        "avisos": "Warnings (do not change the result): {n}",
        "sin_avisos": "Warnings: none",
        "prefijo_cuadrante": "Quadrant:",
        "sin_frontmatter": "missing YAML frontmatter block (--- ... ---) at the top",
        "yaml_invalido": "invalid YAML: {e}",
        "no_es_mapa": "frontmatter must be a mapping of fields (key: value)",
        "campo_vacio": "required field missing or empty: {campo}",
        "tipo_invalido": "type '{valor}' is not valid (use: {lista})",
        "categoria": "category '{valor}' is not in the closed list ({lista}); "
                     "to add one, edit CATEGORIAS[\"en\"] in scripts/lint.py",
        "confianza_no_numero": "confidence must be a number between 0 and 1 (value: {valor!r})",
        "confianza_rango": "confidence {valor} out of range [0, 1]",
        "fecha_formato": "{campo} must have format YYYY-MM-DD (value: {valor!r})",
        "caducada": "expires {fecha}, before today ({hoy})",
        "fuentes_lista": "sources must be a list (- raw/...)",
        "fuente_inexistente": "{fuente} does not exist on disk",
        "enlace_roto": "[[{destino}]] does not match any page in wiki/",
        "huerfana": "no other page links here (links from index.md and log.md do not count)",
        "no_reciproco": "links to [[{destino}]], but {pagina} does not link back to [[{origen}]]",
        "index_falta": "the page is not linked from wiki/index.md",
        "index_sobra": "[[{destino}]] points to a page that does not exist",
        "hashes_json": "raw/.hashes.json is not valid JSON ({e}); restore it from git or a backup",
        "hashes_objeto": "raw/.hashes.json must be an object {{\"raw/file\": \"sha256\"}}",
        "raw_desaparecido": "registered in raw/.hashes.json but no longer exists",
        "raw_modificado": "content changed since it was registered (different sha256); raw/ is immutable",
        "raw_sin_hash": "no hash in raw/.hashes.json; it is registered on ingest (scripts/log.py --raw)",
        "sin_cuadrante": "does not declare its quadrant: no line starting with \"Quadrant:\" "
                         "(MAESTRO rule 11)",
        "wiki_mayor_que_raw": "the wiki weighs {wiki:.1f} KB and its sources {raw:.1f} KB ({ratio:.2f}×): "
                              "a wiki should distill, not copy; review pages that repeat their source",
        "sin_yaml": "error: PyYAML is missing. Install it with: pip install pyyaml",
        "hoy_invalida": "argument --hoy: invalid date '{valor}' (use YYYY-MM-DD)",
        "no_es_vault": "error: {vault} does not look like a vault (no wiki/ folder)",
    },
}

# Solo se usa regex para SEPARAR el bloque --- ... ---; los campos los lee yaml.
RE_FRONTMATTER = re.compile(r"\A---[ \t]*\r?\n(.*?)^---[ \t]*\r?$", re.S | re.M)
RE_WIKILINK = re.compile(r"\[\[([^\[\]]+?)\]\]")
RE_FECHA = re.compile(r"\d{4}-\d{2}-\d{2}")
# Obsidian no trata como enlace lo que está dentro de código; el lint tampoco.
RE_CODIGO = re.compile(r"(`{3,}|~{3,}).*?\1|`[^`\n]*`", re.S)
# Se aceptan las dos formas en cualquier idioma: una página copiada de un vault
# del otro idioma no debe llenarse de enlaces rotos falsos.
PREFIJOS_PENDIENTE = ("pendiente:", "pending:")


class ErrorLint(Exception):
    """Error que impide correr el lint (no es un fallo de la wiki)."""


def idioma_vault(vault: Path, forzado=None) -> str:
    """--lang si se dio; si no, el de .second-brain.json; si no, "es" (vaults sin marcador)."""
    if forzado:
        return forzado
    try:
        idioma = json.loads((vault / MARCADOR_IDIOMA).read_text(encoding="utf-8")).get("lang")
    except (OSError, ValueError, AttributeError):
        return "es"
    return idioma if idioma in IDIOMAS else "es"


def id_publico(tipo: str, idioma: str) -> str:
    return IDS_EN[tipo] if idioma == "en" else tipo


def oculto(rel: Path) -> bool:
    """True si alguna parte de la ruta empieza por punto (.DS_Store, .obsidian...)."""
    return any(parte.startswith(".") for parte in rel.parts)


def sha256(ruta: Path) -> str:
    return hashlib.sha256(ruta.read_bytes()).hexdigest()


def separar_frontmatter(texto: str):
    """Devuelve (bloque_yaml o None, cuerpo)."""
    m = RE_FRONTMATTER.match(texto)
    if not m:
        return None, texto
    return m.group(1), texto[m.end():]


def destinos(texto: str) -> set:
    """Nombres de archivo (sin extensión) a los que apuntan los [[wikilinks]].

    Acepta [[x|alias]] y [[x#seccion]]; ignora [[pendiente:X]] y [[pending:X]]
    porque son una relación prevista, no un enlace.
    """
    salida = set()
    for crudo in RE_WIKILINK.findall(texto):
        destino = crudo.split("|", 1)[0].rstrip("\\").split("#", 1)[0].strip()
        if not destino or destino.startswith(PREFIJOS_PENDIENTE):
            continue
        destino = destino.rsplit("/", 1)[-1]
        if destino.lower().endswith(".md"):
            destino = destino[:-3]
        salida.add(destino)
    return salida


def esta_vacio(valor) -> bool:
    if valor is None:
        return True
    if isinstance(valor, str):
        return not valor.strip()
    if isinstance(valor, (list, dict)):
        return not valor
    return False


def fecha_valida(valor):
    """Devuelve la fecha si el valor es AAAA-MM-DD (date de YAML o texto); si no, None."""
    if isinstance(valor, dt.datetime):  # 2026-01-01 10:00 no es AAAA-MM-DD
        return None
    if isinstance(valor, dt.date):
        return valor
    if isinstance(valor, str) and RE_FECHA.fullmatch(valor.strip()):
        try:
            return dt.date.fromisoformat(valor.strip())
        except ValueError:
            return None
    return None


def una_linea(texto) -> str:
    return " ".join(str(texto).split())


def revisar_meta(bloque: str, rel: str, vault: Path, hoy: dt.date, fallo, idioma: str) -> None:
    """Chequeos que dependen del frontmatter de una página, con los campos del idioma del vault."""
    T = TEXTOS[idioma]
    try:
        meta = yaml.safe_load(bloque)
    except Exception as e:  # yaml.YAMLError, o ValueError por fechas imposibles
        fallo("frontmatter", rel, T["yaml_invalido"].format(e=una_linea(e)))
        return
    if not isinstance(meta, dict):
        fallo("frontmatter", rel, T["no_es_mapa"])
        return

    obligatorios = CAMPOS_OBLIGATORIOS[idioma]
    _, c_tipo, c_categoria, c_fuentes, c_fecha, c_confianza, c_caducidad = obligatorios
    for campo in obligatorios:
        if esta_vacio(meta.get(campo)):
            fallo("frontmatter", rel, T["campo_vacio"].format(campo=campo))

    tipo = meta.get(c_tipo)
    if not esta_vacio(tipo) and tipo not in TIPOS[idioma]:
        fallo("frontmatter", rel, T["tipo_invalido"].format(valor=tipo, lista=", ".join(TIPOS[idioma])))

    categoria = meta.get(c_categoria)
    if not esta_vacio(categoria) and categoria not in CATEGORIAS[idioma]:
        fallo("categoria", rel,
              T["categoria"].format(valor=categoria, lista=", ".join(CATEGORIAS[idioma])))

    confianza = meta.get(c_confianza)
    if not esta_vacio(confianza):
        if isinstance(confianza, bool) or not isinstance(confianza, (int, float)):
            fallo("frontmatter", rel, T["confianza_no_numero"].format(valor=confianza))
        elif not 0 <= confianza <= 1:
            fallo("frontmatter", rel, T["confianza_rango"].format(valor=confianza))

    for campo in (c_fecha, c_caducidad):
        valor = meta.get(campo)
        if not esta_vacio(valor) and fecha_valida(valor) is None:
            fallo("frontmatter", rel, T["fecha_formato"].format(campo=campo, valor=valor))

    caducidad = fecha_valida(meta.get(c_caducidad))
    if caducidad and caducidad < hoy:
        fallo("caducada", rel, T["caducada"].format(fecha=caducidad.isoformat(), hoy=hoy.isoformat()))

    fuentes = meta.get(c_fuentes)
    if not esta_vacio(fuentes):
        if not isinstance(fuentes, list):
            fallo("frontmatter", rel, T["fuentes_lista"])
        else:
            for fuente in sorted({f.strip() for f in fuentes if isinstance(f, str)}):
                if fuente.startswith("raw/") and not (vault / fuente).exists():
                    fallo("fuente_inexistente", rel, T["fuente_inexistente"].format(fuente=fuente))


def comandos_sin_cuadrante(vault: Path, idioma: str) -> list:
    """Avisos por cada comando de .claude/commands/ sin su línea de cuadrante (regla MAESTRO 11)."""
    carpeta = vault / ".claude" / "commands"
    if not carpeta.is_dir():
        return []
    T = TEXTOS[idioma]
    avisos = []
    for ruta in sorted(carpeta.glob("*.md")):
        if not ruta.is_file() or ruta.name.startswith("."):
            continue
        lineas = ruta.read_text(encoding="utf-8-sig").splitlines()
        if not any(linea.startswith(T["prefijo_cuadrante"]) for linea in lineas):
            avisos.append({"tipo": "comando_sin_cuadrante", "archivo": ruta.relative_to(vault).as_posix(),
                           "detalle": T["sin_cuadrante"]})
    return avisos


def lint(vault: Path, hoy: dt.date, idioma: str = "es") -> dict:
    """Revisa el vault y devuelve {"estado", "fallos", "avisos", "paginas"}.

    Estado, ids y detalles salen en el idioma del vault; las claves del dict son
    siempre estas (a_json las traduce para la salida JSON en inglés).
    """
    T = TEXTOS[idioma]
    wiki = vault / "wiki"
    fallos, avisos, vistos = [], [], set()

    def fallo(tipo, archivo, detalle):
        clave = (tipo, archivo, detalle)
        if clave not in vistos:  # un mismo problema se reporta una sola vez
            vistos.add(clave)
            fallos.append({"tipo": tipo, "archivo": archivo, "detalle": detalle})

    # 1) Páginas: todo .md de wiki/ salvo wiki/index.md y wiki/log.md.
    paginas, salientes = {}, {}
    tam_wiki = 0
    for ruta in sorted(wiki.rglob("*.md")):
        rel_wiki = ruta.relative_to(wiki)
        if not ruta.is_file() or oculto(rel_wiki) or rel_wiki.as_posix() in ("index.md", "log.md"):
            continue
        rel = ruta.relative_to(vault).as_posix()
        tam_wiki += ruta.stat().st_size
        texto = ruta.read_text(encoding="utf-8-sig")
        bloque, cuerpo = separar_frontmatter(texto)
        enlaces = destinos(RE_CODIGO.sub("", cuerpo))
        if bloque is None:
            fallo("frontmatter", rel, T["sin_frontmatter"])
        else:
            enlaces |= destinos(bloque)  # los enlaces del frontmatter también cuentan
            revisar_meta(bloque, rel, vault, hoy, fallo, idioma)
        paginas[ruta.stem] = rel
        salientes[ruta.stem] = enlaces - {ruta.stem}

    # 2) Enlaces: rotos, huérfanas y reciprocidad (resolución por nombre, estilo Obsidian).
    nombres_wiki = {p.name for p in wiki.rglob("*") if p.is_file()}
    existentes = set(paginas) | {"index", "log"} | nombres_wiki
    entrantes = {nombre: set() for nombre in paginas}
    for origen in sorted(paginas):
        for destino in sorted(salientes[origen]):
            if destino not in existentes:
                fallo("enlace_roto", paginas[origen], T["enlace_roto"].format(destino=destino))
            elif destino in paginas:
                entrantes[destino].add(origen)
    for nombre in sorted(paginas):
        if not entrantes[nombre]:
            fallo("huerfana", paginas[nombre], T["huerfana"])
    for origen in sorted(paginas):
        for destino in sorted(salientes[origen]):
            if destino in paginas and origen not in salientes[destino]:
                fallo("no_reciproco", paginas[origen],
                      T["no_reciproco"].format(destino=destino, pagina=paginas[destino], origen=origen))

    # 3) Índice.
    indice = wiki / "index.md"
    en_indice = destinos(RE_CODIGO.sub("", indice.read_text(encoding="utf-8-sig"))) if indice.is_file() else set()
    for nombre in sorted(paginas):
        if nombre not in en_indice:
            fallo("index_falta", paginas[nombre], T["index_falta"])
    for destino in sorted(en_indice):
        if destino not in existentes:
            fallo("index_sobra", "wiki/index.md", T["index_sobra"].format(destino=destino))

    # 4) Integridad de raw/ contra raw/.hashes.json.
    raw = vault / "raw"
    registro = raw / ".hashes.json"
    hashes = {}
    if registro.is_file():
        try:
            hashes = json.loads(registro.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            raise ErrorLint(T["hashes_json"].format(e=e))
        if not isinstance(hashes, dict):
            raise ErrorLint(T["hashes_objeto"].format())
    for rel, registrado in sorted(hashes.items()):
        ruta = vault / rel
        if not ruta.is_file():
            fallo("raw_desaparecido", rel, T["raw_desaparecido"])
        elif sha256(ruta) != registrado:
            fallo("raw_modificado", rel, T["raw_modificado"])
    tam_raw = 0
    if raw.is_dir():
        for ruta in sorted(raw.rglob("*")):
            if ruta.is_file() and not oculto(ruta.relative_to(raw)):
                tam_raw += ruta.stat().st_size
                rel = ruta.relative_to(vault).as_posix()
                if rel not in hashes:
                    avisos.append({"tipo": "raw_sin_hash", "archivo": rel, "detalle": T["raw_sin_hash"]})

    # 5) Tamaño: es aviso, no cambia el resultado.
    if tam_raw >= MINIMO_RAW_KB * 1024 and tam_wiki / tam_raw > UMBRAL_TAMANO_WIKI:
        avisos.append({"tipo": "wiki_mayor_que_raw", "archivo": "wiki/",
                       "detalle": T["wiki_mayor_que_raw"].format(
                           wiki=tam_wiki / 1024, raw=tam_raw / 1024, ratio=tam_wiki / tam_raw)})

    # 6) Cuadrante declarado en cada comando: es aviso, no cambia el resultado.
    avisos += comandos_sin_cuadrante(vault, idioma)

    fallos.sort(key=lambda f: (TIPOS_FALLO.index(f["tipo"]), f["archivo"], f["detalle"]))
    for item in fallos + avisos:
        item["tipo"] = id_publico(item["tipo"], idioma)
    return {"estado": T["ROJO"] if fallos else T["VERDE"], "fallos": fallos,
            "avisos": avisos, "paginas": len(paginas)}


def claves_en(item: dict) -> dict:
    return {CLAVES_EN[clave]: valor for clave, valor in item.items()}


def a_json(res: dict, idioma: str) -> dict:
    """El resultado con las claves del idioma del vault (en español, las de siempre)."""
    if idioma != "en":
        return res
    return {"status": res["estado"], "failures": [claves_en(f) for f in res["fallos"]],
            "warnings": [claves_en(a) for a in res["avisos"]], "pages": res["paginas"]}


def reporte_texto(res: dict, vault: str, hoy: dt.date, idioma: str = "es") -> str:
    T = TEXTOS[idioma]
    n = len(res["fallos"])
    singular, plural = T["fallo"]
    lineas = [f"LINT: {res['estado']} ({n} {singular if n == 1 else plural})",
              T["cabecera"].format(vault=vault, paginas=res["paginas"], hoy=hoy.isoformat())]
    for tipo in TIPOS_FALLO:
        nombre = id_publico(tipo, idioma)
        grupo = [f for f in res["fallos"] if f["tipo"] == nombre]
        if grupo:
            lineas.append("")
            lineas.append(f"[{nombre}] {len(grupo)}")
            lineas.extend(f"  - {f['archivo']}: {f['detalle']}" for f in grupo)
    lineas.append("")
    if res["avisos"]:
        lineas.append(T["avisos"].format(n=len(res["avisos"])))
        lineas.extend(f"  - {a['archivo']}: {a['detalle']}" for a in res["avisos"])
    else:
        lineas.append(T["sin_avisos"])
    return "\n".join(lineas)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Lint de la wiki: VERDE (exit 0) o ROJO (exit 1).")
    ap.add_argument("vault", nargs="?", default=".", help="carpeta del vault (por defecto, la actual)")
    ap.add_argument("--json", action="store_true", help="salida en JSON")
    ap.add_argument("--hoy", help="fecha de referencia AAAA-MM-DD (para pruebas)")
    ap.add_argument("--lang", choices=IDIOMAS,
                    help=f"idioma del vault (por defecto, el de {MARCADOR_IDIOMA}; si no hay, es)")
    args = ap.parse_args(argv)

    vault = Path(args.vault)
    idioma = idioma_vault(vault, args.lang)
    T = TEXTOS[idioma]
    if yaml is None:
        print(T["sin_yaml"], file=sys.stderr)
        return 2
    hoy = dt.date.today()
    if args.hoy is not None:
        hoy = fecha_valida(args.hoy)
        if hoy is None:
            # La fecha se valida aquí y no en argparse porque el mensaje depende del idioma.
            ap.error(T["hoy_invalida"].format(valor=args.hoy))
    if not (vault / "wiki").is_dir():
        print(T["no_es_vault"].format(vault=vault), file=sys.stderr)
        return 2
    try:
        res = lint(vault, hoy, idioma)
    except ErrorLint as e:
        print(f"error: {e}", file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps(a_json(res, idioma), ensure_ascii=False, indent=2))
    else:
        print(reporte_texto(res, args.vault, hoy, idioma))
    return 1 if res["fallos"] else 0


if __name__ == "__main__":
    sys.exit(main())
