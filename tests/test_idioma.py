"""Pruebas del modo bilingüe: vaults en inglés (init, lint, log), orden de
resolución del idioma, enlaces pendientes y el aviso de cuadrante (regla 11)."""
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

KIT = Path(__file__).resolve().parents[1]
LINT = KIT / "scripts" / "lint.py"
LOG = KIT / "scripts" / "log.py"
EJEMPLO = KIT / "tests" / "vault_ejemplo"
EJEMPLO_EN = KIT / "tests" / "vault_example_en"
HOY = "2026-09-18"
RAW = "raw/2026-01-01-source.md"

META_EN = {
    "title": '"Test page"',
    "type": "concept",
    "category": "General",
    "sources": f'\n  - "{RAW}"',
    "date": "2026-09-01",
    "confidence": "0.5",
    "expires": "2027-09-01",
}

META_ES = {
    "titulo": '"Página de prueba"',
    "tipo": "concepto",
    "categoria": "General",
    "fuentes": f'\n  - "{RAW}"',
    "fecha": "2026-09-01",
    "confianza": "0.5",
    "caducidad": "2027-09-01",
}


def correr(*args):
    return subprocess.run([sys.executable, *map(str, args)], capture_output=True, text=True)


def escribir(vault: Path, rel: str, cuerpo: str, meta=None, **cambios) -> None:
    """Escribe una página con frontmatter en inglés (o el `meta` dado); None quita el campo."""
    datos = {**(meta or META_EN), **cambios}
    lineas = [f"{clave}: {valor}" for clave, valor in datos.items() if valor is not None]
    ruta = vault / rel
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text("---\n" + "\n".join(lineas) + "\n---\n\n" + cuerpo, encoding="utf-8")


def indice(vault: Path, *nombres: str) -> None:
    lineas = "".join(f"- [[{n}]]\n" for n in nombres)
    (vault / "wiki/index.md").write_text(f"# Index\n\n{lineas}", encoding="utf-8")


def lint(vault: Path, *extra):
    """Corre el lint en JSON; devuelve (exit code, datos)."""
    r = correr(LINT, vault, "--json", "--hoy", HOY, *extra)
    return r.returncode, json.loads(r.stdout)


def ids(datos, clave="failures", campo="type") -> list:
    return sorted(f[campo] for f in datos[clave])


def crear_vault(destino: Path, idioma: str) -> Path:
    """Vault verde en `idioma`: alpha (concepto) <-> beta (fuente), raw registrado."""
    assert correr(KIT / "init_vault.py", destino, "--lang", idioma).returncode == 0
    (destino / RAW).write_text("test source\n", encoding="utf-8")
    assert correr(LOG, destino, "INGEST", "test", "--raw", RAW).returncode == 0
    if idioma == "en":
        escribir(destino, "wiki/concepts/alpha.md", "# Alpha\n\nSee [[beta]].\n")
        escribir(destino, "wiki/sources/beta.md", "# Beta\n\nSee [[alpha]].\n", type="source")
    else:
        escribir(destino, "wiki/conceptos/alpha.md", "# Alpha\n\nVer [[beta]].\n", META_ES)
        escribir(destino, "wiki/fuentes/beta.md", "# Beta\n\nVer [[alpha]].\n", META_ES, tipo="fuente")
    indice(destino, "alpha", "beta")
    return destino


@pytest.fixture
def vault_en(tmp_path):
    return crear_vault(tmp_path / "en", "en")


@pytest.fixture
def vault_es(tmp_path):
    return crear_vault(tmp_path / "es", "es")


# --- lint en inglés ---------------------------------------------------------------------

def test_en_verde_json(vault_en):
    codigo, datos = lint(vault_en)
    assert codigo == 0
    assert datos == {"status": "GREEN", "failures": [], "warnings": [], "pages": 2}


def test_en_verde_texto(vault_en):
    r = correr(LINT, vault_en, "--hoy", HOY)
    assert r.returncode == 0, r.stdout
    assert r.stdout.splitlines()[0] == "LINT: GREEN (0 failures)"
    assert "Warnings: none" in r.stdout


def test_en_rojo_texto(vault_en):
    escribir(vault_en, "wiki/concepts/alpha.md", "See [[beta]] and [[ghost]].\n", category="Cooking")
    r = correr(LINT, vault_en, "--hoy", HOY)
    assert r.returncode == 1
    lineas = r.stdout.splitlines()
    assert lineas[0] == "LINT: RED (2 failures)"
    assert "[category] 1" in lineas
    assert "[broken_link] 1" in lineas
    assert "is not in the closed list" in r.stdout
    assert "does not match any page in wiki/" in r.stdout


def _otra_fuente_desaparecida(v):
    otra = "raw/2026-01-02-other.md"
    (v / otra).write_text("other\n", encoding="utf-8")
    assert correr(LOG, v, "INGEST", "other", "--raw", otra).returncode == 0
    (v / otra).unlink()


ROTURAS = {
    "frontmatter": lambda v: escribir(v, "wiki/concepts/alpha.md", "See [[beta]].\n", confidence="2"),
    "category": lambda v: escribir(v, "wiki/concepts/alpha.md", "See [[beta]].\n", category="Cooking"),
    "broken_link": lambda v: escribir(v, "wiki/concepts/alpha.md", "See [[beta]] and [[ghost]].\n"),
    "orphan": lambda v: (escribir(v, "wiki/concepts/gamma.md", "# Gamma\n"),
                         indice(v, "alpha", "beta", "gamma")),
    "not_reciprocal": lambda v: (escribir(v, "wiki/concepts/alpha.md", "See [[beta]] and [[gamma]].\n"),
                                 escribir(v, "wiki/concepts/gamma.md", "# Gamma, no link back\n"),
                                 indice(v, "alpha", "beta", "gamma")),
    "expired": lambda v: escribir(v, "wiki/concepts/alpha.md", "See [[beta]].\n", expires="2026-09-17"),
    "index_missing": lambda v: indice(v, "alpha"),
    "index_extra": lambda v: indice(v, "alpha", "beta", "ghost"),
    "raw_modified": lambda v: (v / RAW).write_text("changed\n", encoding="utf-8"),
    "raw_missing": _otra_fuente_desaparecida,
    "missing_source": lambda v: escribir(v, "wiki/concepts/alpha.md", "See [[beta]].\n",
                                         sources=f'\n  - "{RAW}"\n  - "raw/does-not-exist.md"'),
}


@pytest.mark.parametrize("esperado", sorted(ROTURAS))
def test_en_ids_de_fallo(vault_en, esperado):
    ROTURAS[esperado](vault_en)
    codigo, datos = lint(vault_en)
    assert codigo == 1
    assert datos["status"] == "RED"
    assert ids(datos) == [esperado]
    assert set(datos["failures"][0]) == {"type", "file", "detail"}


def test_en_aviso_raw_unhashed(vault_en):
    (vault_en / "raw/2026-01-03-new.md").write_text("new\n", encoding="utf-8")
    codigo, datos = lint(vault_en)
    assert codigo == 0
    assert datos["warnings"] == [{"type": "raw_unhashed", "file": "raw/2026-01-03-new.md",
                                  "detail": "no hash in raw/.hashes.json; it is registered on ingest "
                                            "(scripts/log.py --raw)"}]


def test_en_hoy_invalida(vault_en):
    r = correr(LINT, vault_en, "--hoy", "18/09/2026")
    assert r.returncode == 2
    assert "invalid date '18/09/2026'" in r.stderr


def test_en_no_es_vault(tmp_path):
    r = correr(LINT, tmp_path, "--lang", "en")
    assert r.returncode == 2
    assert "does not look like a vault" in r.stderr


# --- orden de resolución: --lang > .second-brain.json > es -----------------------------

def test_marcador_en_valida_en_ingles(vault_es):
    # Páginas con campos en español dentro de un vault marcado en inglés: el marcador manda.
    (vault_es / ".second-brain.json").write_text('{"lang": "en"}\n', encoding="utf-8")
    codigo, datos = lint(vault_es)
    assert codigo == 1
    assert datos["status"] == "RED"
    assert set(ids(datos)) == {"frontmatter"}


def test_flag_gana_al_marcador(vault_es):
    (vault_es / ".second-brain.json").write_text('{"lang": "en"}\n', encoding="utf-8")
    codigo, datos = lint(vault_es, "--lang", "es")
    assert codigo == 0
    assert datos == {"estado": "VERDE", "fallos": [], "avisos": [], "paginas": 2}


def test_flag_en_sobre_vault_es(vault_es):
    codigo, datos = lint(vault_es, "--lang", "en")
    assert codigo == 1
    assert "status" in datos and "estado" not in datos


@pytest.mark.parametrize("marcador", [None, "no es json", '{"lang": "fr"}', '["en"]'])
def test_sin_marcador_valido_es_espanol(vault_es, marcador):
    ruta = vault_es / ".second-brain.json"
    if marcador is None:
        ruta.unlink()
    else:
        ruta.write_text(marcador + "\n", encoding="utf-8")
    codigo, datos = lint(vault_es)
    assert codigo == 0
    assert datos["estado"] == "VERDE"


# --- enlaces pendientes: los dos prefijos valen en los dos idiomas ---------------------

@pytest.mark.parametrize("prefijo", ["pending:", "pendiente:"])
def test_pendientes_en(vault_en, prefijo):
    escribir(vault_en, "wiki/concepts/alpha.md", f"See [[beta]] and [[{prefijo}gamma]].\n")
    codigo, datos = lint(vault_en)
    assert (codigo, datos["failures"]) == (0, [])


@pytest.mark.parametrize("prefijo", ["pending:", "pendiente:"])
def test_pendientes_es(vault_es, prefijo):
    escribir(vault_es, "wiki/conceptos/alpha.md", f"Ver [[beta]] y [[{prefijo}gamma]].\n", META_ES)
    codigo, datos = lint(vault_es)
    assert (codigo, datos["fallos"]) == (0, [])


# --- aviso de cuadrante (regla MAESTRO 11) ----------------------------------------------

def quitar_linea(ruta: Path, prefijo: str) -> None:
    lineas = ruta.read_text(encoding="utf-8").splitlines(keepends=True)
    restantes = [l for l in lineas if not l.startswith(prefijo)]
    assert len(restantes) == len(lineas) - 1
    ruta.write_text("".join(restantes), encoding="utf-8")


def test_cuadrante_en(vault_en):
    quitar_linea(vault_en / ".claude/commands/query.md", "Quadrant:")
    codigo, datos = lint(vault_en)
    assert codigo == 0 and datos["status"] == "GREEN"
    assert datos["warnings"] == [{"type": "command_without_quadrant", "file": ".claude/commands/query.md",
                                  "detail": "does not declare its quadrant: no line starting with "
                                            "\"Quadrant:\" (MAESTRO rule 11)"}]


def test_cuadrante_es(vault_es):
    quitar_linea(vault_es / ".claude/commands/ingest.md", "Cuadrante:")
    codigo, datos = lint(vault_es)
    assert codigo == 0 and datos["estado"] == "VERDE"
    assert ids(datos, "avisos", "tipo") == ["comando_sin_cuadrante"]
    assert datos["avisos"][0]["archivo"] == ".claude/commands/ingest.md"
    r = correr(LINT, vault_es, "--hoy", HOY)
    assert r.stdout.splitlines()[0] == "LINT: VERDE (0 fallos)"
    assert "  - .claude/commands/ingest.md: no declara su cuadrante" in r.stdout


def test_cuadrante_no_cambia_el_veredicto_rojo(vault_en):
    quitar_linea(vault_en / ".claude/commands/lint.md", "Quadrant:")
    indice(vault_en, "alpha")
    codigo, datos = lint(vault_en)
    assert codigo == 1
    assert ids(datos) == ["index_missing"]
    assert ids(datos, "warnings") == ["command_without_quadrant"]


def test_cuadrante_en_otro_idioma_no_cuenta(vault_en):
    # Un vault en inglés exige "Quadrant:"; la línea en español no la sustituye.
    ruta = vault_en / ".claude/commands/query.md"
    ruta.write_text(ruta.read_text(encoding="utf-8").replace("Quadrant:", "Cuadrante:"), encoding="utf-8")
    _, datos = lint(vault_en)
    assert ids(datos, "warnings") == ["command_without_quadrant"]


def test_sin_carpeta_de_comandos_no_avisa(vault_en):
    shutil.rmtree(vault_en / ".claude")
    codigo, datos = lint(vault_en)
    assert (codigo, datos["warnings"]) == (0, [])


# --- vault de ejemplo en inglés -----------------------------------------------------------

def test_vault_example_en_verde():
    r = correr(LINT, EJEMPLO_EN, "--hoy", HOY)
    assert r.returncode == 0, r.stdout
    assert r.stdout.splitlines()[0] == "LINT: GREEN (0 failures)"
    assert "Warnings: none" in r.stdout


def test_vault_example_en_scripts_al_dia():
    for script in ("lint.py", "log.py"):
        assert (EJEMPLO_EN / "scripts" / script).read_bytes() == (KIT / "scripts" / script).read_bytes()


@pytest.mark.parametrize("plantilla, ejemplo", [("plantilla", EJEMPLO), ("plantilla-en", EJEMPLO_EN)])
def test_vaults_de_ejemplo_siguen_su_plantilla(plantilla, ejemplo):
    """CLAUDE.md (salvo el título) y los comandos del ejemplo son los de su plantilla."""
    origen = KIT / plantilla
    sin_titulo = lambda ruta: ruta.read_bytes().split(b"\n", 1)[1]
    assert sin_titulo(ejemplo / "CLAUDE.md") == sin_titulo(origen / "CLAUDE.md")
    for comando in ("ingest.md", "query.md", "lint.md"):
        rel = Path(".claude/commands") / comando
        assert (ejemplo / rel).read_bytes() == (origen / rel).read_bytes(), rel


def cambiar(ruta: Path, viejo: str, nuevo: str) -> None:
    texto = ruta.read_text(encoding="utf-8")
    assert texto.count(viejo) == 1, viejo
    ruta.write_text(texto.replace(viejo, nuevo), encoding="utf-8")


def test_vault_example_en_con_sus_3_defectos(tmp_path):
    """Mismo ejercicio que el ejemplo en español: broken_link, orphan y expired."""
    copia = tmp_path / "example"
    shutil.copytree(EJEMPLO_EN, copia)
    concepto = copia / "wiki/concepts/spaced-repetition.md"
    entidad = copia / "wiki/entities/example-team.md"
    fuente = copia / "wiki/sources/article-spaced-repetition.md"
    cambiar(concepto, "[[pending:forgetting-curve]]", "[[forgetting-curve]]")
    cambiar(concepto, "- [[example-team]] — team that is trying it "
                      "(raw/2026-09-02-example-team-notes.md).\n", "")
    cambiar(entidad, "## Related\n\n- [[spaced-repetition]] — method the team decided "
                     "to try (raw/2026-09-02-example-team-notes.md).\n\n", "")
    cambiar(fuente, "expires: 2030-12-31", "expires: 2026-01-31")

    codigo, datos = lint(copia)
    assert codigo == 1
    assert ids(datos) == ["broken_link", "expired", "orphan"]
    archivos = {f["type"]: f["file"] for f in datos["failures"]}
    assert archivos == {
        "broken_link": "wiki/concepts/spaced-repetition.md",
        "orphan": "wiki/entities/example-team.md",
        "expired": "wiki/sources/article-spaced-repetition.md",
    }


# --- log.py en inglés -----------------------------------------------------------------------

@pytest.fixture
def vacio_en(tmp_path):
    destino = tmp_path / "log-en"
    assert correr(KIT / "init_vault.py", destino, "--lang", "en").returncode == 0
    return destino


def test_log_en_mensajes_de_registro(vacio_en):
    fuente = "raw/2026-09-18-source.md"
    (vacio_en / fuente).write_text("original\n", encoding="utf-8")
    r = correr(LOG, vacio_en, "INGEST", "first", "--raw", fuente, "--fecha", "2026-09-18")
    assert r.returncode == 0, r.stderr
    assert f"Hash registered: {fuente}" in r.stdout
    assert "Logged in wiki/log.md: 2026-09-18 | INGEST | first" in r.stdout
    assert (vacio_en / "wiki/log.md").read_text(encoding="utf-8").endswith(
        "\n2026-09-18 | INGEST | first\n")

    r = correr(LOG, vacio_en, "INGEST", "second", "--raw", fuente)
    assert r.returncode == 0, r.stderr
    assert f"Hash already registered (the original is kept): {fuente}" in r.stdout


@pytest.mark.parametrize("args, mensaje", [
    (("DELETE", "x"), "operation 'DELETE' is not valid"),
    (("LINT", "x", "--fecha", "18/09/2026"), "invalid date '18/09/2026'"),
    (("LINT", "   "), "the description is empty"),
    (("INGEST", "x", "--raw", "raw/missing.md"), "does not exist"),
    (("INGEST", "x", "--raw", "wiki/index.md"), "is not inside raw/"),
])
def test_log_en_errores(vacio_en, args, mensaje):
    antes = (vacio_en / "wiki/log.md").read_bytes()
    r = correr(LOG, vacio_en, *args)
    assert r.returncode == 2
    assert mensaje in r.stderr
    assert (vacio_en / "wiki/log.md").read_bytes() == antes


def test_log_flag_es_sobre_vault_en(vacio_en):
    fuente = "raw/2026-09-18-source.md"
    (vacio_en / fuente).write_text("original\n", encoding="utf-8")
    r = correr(LOG, vacio_en, "INGEST", "x", "--raw", fuente, "--lang", "es")
    assert r.returncode == 0, r.stderr
    assert "Hash registrado" in r.stdout and "registered" not in r.stdout


def test_log_en_sin_vault(tmp_path):
    r = correr(LOG, tmp_path, "LINT", "x", "--lang", "en")
    assert r.returncode == 2
    assert "is this a vault folder?" in r.stderr
