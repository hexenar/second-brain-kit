"""Pruebas de scripts/lint.py: un caso por tipo de fallo, formatos de enlace,
salida JSON/texto, exit codes y el vault de ejemplo."""
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

KIT = Path(__file__).resolve().parents[1]
LINT = KIT / "scripts" / "lint.py"
EJEMPLO = KIT / "tests" / "vault_ejemplo"
HOY = "2026-09-18"
RAW = "raw/2026-01-01-fuente.md"

META_BASE = {
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


def escribir(vault: Path, rel: str, cuerpo: str, **cambios) -> None:
    """Escribe una página con el frontmatter base; un valor None quita el campo."""
    meta = {**META_BASE, **cambios}
    lineas = [f"{clave}: {valor}" for clave, valor in meta.items() if valor is not None]
    ruta = vault / rel
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text("---\n" + "\n".join(lineas) + "\n---\n\n" + cuerpo, encoding="utf-8")


def indice(vault: Path, *nombres: str) -> None:
    lineas = "".join(f"- [[{n}]]\n" for n in nombres)
    (vault / "wiki/index.md").write_text(f"# Índice\n\n{lineas}", encoding="utf-8")


def lint(vault: Path, *extra):
    """Corre el lint en JSON; devuelve (exit code, datos)."""
    r = correr(LINT, vault, "--json", "--hoy", HOY, *extra)
    return r.returncode, json.loads(r.stdout)


def tipos(datos) -> list:
    return sorted(f["tipo"] for f in datos["fallos"])


@pytest.fixture
def vault(tmp_path):
    """Vault VERDE: alfa (concepto) <-> beta (fuente), ambas en el índice, raw registrado."""
    destino = tmp_path / "v"
    assert correr(KIT / "init_vault.py", destino).returncode == 0
    (destino / RAW).write_text("fuente de prueba\n", encoding="utf-8")
    assert correr(KIT / "scripts/log.py", destino, "INGEST", "prueba", "--raw", RAW).returncode == 0
    escribir(destino, "wiki/conceptos/alfa.md", "# Alfa\n\nVer [[beta]].\n")
    escribir(destino, "wiki/fuentes/beta.md", "# Beta\n\nVer [[alfa]].\n", tipo="fuente")
    indice(destino, "alfa", "beta")
    return destino


# --- Vault base -----------------------------------------------------------------

def test_base_verde(vault):
    codigo, datos = lint(vault)
    assert codigo == 0
    assert datos == {"estado": "VERDE", "fallos": [], "avisos": [], "paginas": 2}


# --- 1. frontmatter ----------------------------------------------------------------

def test_frontmatter_falta(vault):
    (vault / "wiki/conceptos/alfa.md").write_text("# Alfa\n\nVer [[beta]].\n", encoding="utf-8")
    codigo, datos = lint(vault)
    assert codigo == 1
    assert tipos(datos) == ["frontmatter"]


def test_frontmatter_yaml_invalido(vault):
    escribir(vault, "wiki/conceptos/alfa.md", "Ver [[beta]].\n", titulo="[sin cerrar")
    _, datos = lint(vault)
    assert tipos(datos) == ["frontmatter"]
    assert "YAML inválido" in datos["fallos"][0]["detalle"]


@pytest.mark.parametrize("campo", list(META_BASE))
def test_frontmatter_campo_ausente(vault, campo):
    escribir(vault, "wiki/conceptos/alfa.md", "Ver [[beta]].\n", **{campo: None})
    _, datos = lint(vault)
    assert tipos(datos) == ["frontmatter"]
    assert datos["fallos"][0]["detalle"].endswith(campo)


@pytest.mark.parametrize("campo,valor", [("titulo", '""'), ("fuentes", "[]"), ("categoria", "")])
def test_frontmatter_campo_vacio(vault, campo, valor):
    escribir(vault, "wiki/conceptos/alfa.md", "Ver [[beta]].\n", **{campo: valor})
    _, datos = lint(vault)
    assert tipos(datos) == ["frontmatter"]


def test_frontmatter_tipo_invalido(vault):
    escribir(vault, "wiki/conceptos/alfa.md", "Ver [[beta]].\n", tipo="nota")
    _, datos = lint(vault)
    assert tipos(datos) == ["frontmatter"]


@pytest.mark.parametrize("valor", ['"alta"', "1.5", "-0.1", "true"])
def test_frontmatter_confianza_invalida(vault, valor):
    escribir(vault, "wiki/conceptos/alfa.md", "Ver [[beta]].\n", confianza=valor)
    _, datos = lint(vault)
    assert tipos(datos) == ["frontmatter"]


@pytest.mark.parametrize("valor", ["0", "1", "0.95"])
def test_frontmatter_confianza_valida(vault, valor):
    escribir(vault, "wiki/conceptos/alfa.md", "Ver [[beta]].\n", confianza=valor)
    assert lint(vault)[0] == 0


@pytest.mark.parametrize("campo", ["fecha", "caducidad"])
@pytest.mark.parametrize("valor", ['"18/09/2026"', '"2026-13-01"', "2026-09-18 10:00", "2026-02-30"])
def test_frontmatter_fecha_invalida(vault, campo, valor):
    escribir(vault, "wiki/conceptos/alfa.md", "Ver [[beta]].\n", **{campo: valor})
    _, datos = lint(vault)
    assert tipos(datos) == ["frontmatter"]


def test_frontmatter_fecha_como_texto_es_valida(vault):
    escribir(vault, "wiki/conceptos/alfa.md", "Ver [[beta]].\n",
             fecha='"2026-09-01"', caducidad='"2027-09-01"')
    assert lint(vault)[0] == 0


# --- 2. categoria -----------------------------------------------------------------------

def test_categoria_fuera_de_lista(vault):
    escribir(vault, "wiki/conceptos/alfa.md", "Ver [[beta]].\n", categoria="Cocina")
    _, datos = lint(vault)
    assert tipos(datos) == ["categoria"]


# --- 3. enlace_roto -----------------------------------------------------------------

def test_enlace_roto(vault):
    escribir(vault, "wiki/conceptos/alfa.md", "Ver [[beta]] y [[no-existe]].\n")
    _, datos = lint(vault)
    assert tipos(datos) == ["enlace_roto"]
    assert datos["fallos"][0]["archivo"] == "wiki/conceptos/alfa.md"


def test_enlace_roto_repetido_se_reporta_una_vez(vault):
    escribir(vault, "wiki/conceptos/alfa.md",
             "Ver [[beta]], [[no-existe]], [[no-existe|otra]] y [[no-existe#x]].\n",
             relacionado='"[[no-existe]]"')
    _, datos = lint(vault)
    assert tipos(datos) == ["enlace_roto"]


def test_pendiente_no_es_roto(vault):
    escribir(vault, "wiki/conceptos/alfa.md", "Ver [[beta]] y [[pendiente:tema-futuro]].\n")
    assert lint(vault)[0] == 0


def test_pendiente_no_cuenta_como_enlace(vault):
    escribir(vault, "wiki/conceptos/alfa.md", "Ver [[beta]] y [[pendiente:gamma]].\n")
    escribir(vault, "wiki/conceptos/gamma.md", "# Gamma\n")
    indice(vault, "alfa", "beta", "gamma")
    _, datos = lint(vault)
    assert tipos(datos) == ["huerfana"]


def test_alias_y_seccion_resuelven(vault):
    escribir(vault, "wiki/conceptos/alfa.md", "Ver [[beta|la beta]] y [[beta#Resumen]].\n")
    assert lint(vault)[0] == 0


def test_enlaces_del_frontmatter_cuentan(vault):
    escribir(vault, "wiki/conceptos/alfa.md", "Ver [[beta]].\n", relacionado='"[[gamma]]"')
    escribir(vault, "wiki/conceptos/gamma.md", "Ver [[alfa]].\n")
    indice(vault, "alfa", "beta", "gamma")
    assert lint(vault)[0] == 0


def test_enlace_dentro_de_codigo_no_cuenta(vault):
    escribir(vault, "wiki/conceptos/alfa.md", "Ver [[beta]]. Sintaxis: `[[no-existe]]`.\n")
    assert lint(vault)[0] == 0


# --- 4. huerfana ---------------------------------------------------------------------------

def test_huerfana_aunque_este_en_el_indice(vault):
    escribir(vault, "wiki/conceptos/gamma.md", "# Gamma, sin enlaces\n")
    indice(vault, "alfa", "beta", "gamma")
    _, datos = lint(vault)
    assert tipos(datos) == ["huerfana"]
    assert datos["fallos"][0]["archivo"] == "wiki/conceptos/gamma.md"


# --- 5. no_reciproco ---------------------------------------------------------------------------

def test_no_reciproco(vault):
    escribir(vault, "wiki/conceptos/alfa.md", "Ver [[beta]] y [[gamma]].\n")
    escribir(vault, "wiki/conceptos/gamma.md", "# Gamma, sin enlace de vuelta\n")
    indice(vault, "alfa", "beta", "gamma")
    _, datos = lint(vault)
    assert tipos(datos) == ["no_reciproco"]
    assert datos["fallos"][0]["archivo"] == "wiki/conceptos/alfa.md"


# --- 6. caducada -----------------------------------------------------------------------

def test_caducada(vault):
    escribir(vault, "wiki/conceptos/alfa.md", "Ver [[beta]].\n", caducidad="2026-09-17")
    _, datos = lint(vault)
    assert tipos(datos) == ["caducada"]


def test_caduca_hoy_no_es_caducada(vault):
    escribir(vault, "wiki/conceptos/alfa.md", "Ver [[beta]].\n", caducidad=HOY)
    assert lint(vault)[0] == 0


# --- 7. index_falta / index_sobra ---------------------------------------------------------

def test_index_falta(vault):
    escribir(vault, "wiki/conceptos/alfa.md", "Ver [[beta]] y [[gamma]].\n")
    escribir(vault, "wiki/conceptos/gamma.md", "Ver [[alfa]].\n")
    _, datos = lint(vault)
    assert tipos(datos) == ["index_falta"]
    assert datos["fallos"][0]["archivo"] == "wiki/conceptos/gamma.md"


def test_index_sobra(vault):
    indice(vault, "alfa", "beta", "fantasma")
    _, datos = lint(vault)
    assert tipos(datos) == ["index_sobra"]


# --- 8. raw_modificado / raw_desaparecido ---------------------------------------------

def test_raw_modificado(vault):
    with (vault / RAW).open("a", encoding="utf-8") as f:
        f.write("cambio\n")
    _, datos = lint(vault)
    assert tipos(datos) == ["raw_modificado"]


def test_raw_desaparecido(vault):
    otra = "raw/2026-01-02-otra.md"
    (vault / otra).write_text("otra\n", encoding="utf-8")
    assert correr(KIT / "scripts/log.py", vault, "INGEST", "otra", "--raw", otra).returncode == 0
    (vault / otra).unlink()
    _, datos = lint(vault)
    assert tipos(datos) == ["raw_desaparecido"]


# --- 9. fuente_inexistente ----------------------------------------------------------------

def test_fuente_inexistente(vault):
    escribir(vault, "wiki/conceptos/alfa.md", "Ver [[beta]].\n",
             fuentes=f'\n  - "{RAW}"\n  - "raw/no-existe.md"')
    _, datos = lint(vault)
    assert tipos(datos) == ["fuente_inexistente"]


# --- Avisos -------------------------------------------------------------------------------

def test_raw_sin_hash_es_aviso_no_fallo(vault):
    (vault / "raw/2026-09-18-nueva.md").write_text("sin ingerir\n", encoding="utf-8")
    codigo, datos = lint(vault)
    assert codigo == 0
    assert datos["fallos"] == []
    assert [a["tipo"] for a in datos["avisos"]] == ["raw_sin_hash"]
    assert datos["avisos"][0]["archivo"] == "raw/2026-09-18-nueva.md"


# --- Salida y exit codes --------------------------------------------------------------------

def test_json_valido_y_estructura(vault):
    escribir(vault, "wiki/conceptos/alfa.md", "Ver [[beta]] y [[no-existe]].\n", categoria="Cocina")
    codigo, datos = lint(vault)
    assert codigo == 1
    assert set(datos) == {"estado", "fallos", "avisos", "paginas"}
    assert datos["estado"] == "ROJO"
    assert datos["paginas"] == 2
    for fallo in datos["fallos"]:
        assert set(fallo) == {"tipo", "archivo", "detalle"}


def test_salida_texto_y_exit_codes(vault):
    r = correr(LINT, vault, "--hoy", HOY)
    assert r.returncode == 0
    assert r.stdout.splitlines()[0] == "LINT: VERDE (0 fallos)"

    escribir(vault, "wiki/conceptos/alfa.md", "Ver [[beta]] y [[no-existe]].\n", categoria="Cocina")
    r = correr(LINT, vault, "--hoy", HOY)
    assert r.returncode == 1
    assert r.stdout.splitlines()[0] == "LINT: ROJO (2 fallos)"
    assert "[categoria] 1" in r.stdout and "[enlace_roto] 1" in r.stdout


def test_error_si_no_es_vault(tmp_path):
    assert correr(LINT, tmp_path).returncode == 2


# --- Vault de ejemplo ------------------------------------------------------------------------

def test_vault_ejemplo_verde():
    r = correr(LINT, EJEMPLO, "--hoy", HOY)
    assert r.returncode == 0, r.stdout
    assert r.stdout.splitlines()[0] == "LINT: VERDE (0 fallos)"
    assert "Avisos: ninguno" in r.stdout


def test_vault_ejemplo_scripts_al_dia():
    for script in ("lint.py", "log.py"):
        assert (EJEMPLO / "scripts" / script).read_bytes() == (KIT / "scripts" / script).read_bytes()


def cambiar(ruta: Path, viejo: str, nuevo: str) -> None:
    texto = ruta.read_text(encoding="utf-8")
    assert texto.count(viejo) == 1, viejo
    ruta.write_text(texto.replace(viejo, nuevo), encoding="utf-8")


def test_vault_ejemplo_con_sus_3_defectos(tmp_path):
    """Reproduce el estado inicial del ejemplo: enlace roto, huérfana y caducada."""
    copia = tmp_path / "ejemplo"
    shutil.copytree(EJEMPLO, copia)
    concepto = copia / "wiki/conceptos/repaso-espaciado.md"
    entidad = copia / "wiki/entidades/equipo-ejemplo.md"
    fuente = copia / "wiki/fuentes/articulo-repaso-espaciado.md"
    cambiar(concepto, "[[pendiente:curva-del-olvido]]", "[[curva-del-olvido]]")
    cambiar(concepto, "- [[equipo-ejemplo]] — equipo que lo está probando "
                      "(raw/2026-09-02-ejemplo-notas-equipo.md).\n", "")
    cambiar(entidad, "## Relacionado\n\n- [[repaso-espaciado]] — método que el equipo decidió "
                     "probar (raw/2026-09-02-ejemplo-notas-equipo.md).\n\n", "")
    cambiar(fuente, "caducidad: 2030-12-31", "caducidad: 2026-01-31")

    codigo, datos = lint(copia)
    assert codigo == 1
    assert tipos(datos) == ["caducada", "enlace_roto", "huerfana"]
    archivos = {f["tipo"]: f["archivo"] for f in datos["fallos"]}
    assert archivos == {
        "enlace_roto": "wiki/conceptos/repaso-espaciado.md",
        "huerfana": "wiki/entidades/equipo-ejemplo.md",
        "caducada": "wiki/fuentes/articulo-repaso-espaciado.md",
    }
