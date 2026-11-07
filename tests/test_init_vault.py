"""Pruebas de init_vault.py (se invoca como subproceso, igual que lo usaría una persona)."""
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

KIT = Path(__file__).resolve().parents[1]
INIT = KIT / "init_vault.py"

ESPERADOS = {
    ".second-brain.json",
    "CLAUDE.md",
    ".claude/commands/ingest.md",
    ".claude/commands/query.md",
    ".claude/commands/lint.md",
    ".claude/commands/consolidar.md",
    "raw/.gitkeep",
    "raw/.hashes.json",
    "wiki/index.md",
    "wiki/log.md",
    "wiki/conceptos/.gitkeep",
    "wiki/entidades/.gitkeep",
    "wiki/fuentes/.gitkeep",
    "scripts/lint.py",
    "scripts/log.py",
}
ESPERADOS_EN = {
    ".second-brain.json",
    "CLAUDE.md",
    ".claude/commands/ingest.md",
    ".claude/commands/query.md",
    ".claude/commands/lint.md",
    ".claude/commands/consolidate.md",
    "raw/.gitkeep",
    "raw/.hashes.json",
    "wiki/index.md",
    "wiki/log.md",
    "wiki/concepts/.gitkeep",
    "wiki/entities/.gitkeep",
    "wiki/sources/.gitkeep",
    "scripts/lint.py",
    "scripts/log.py",
}


def correr(*args):
    return subprocess.run([sys.executable, *map(str, args)], capture_output=True, text=True)


def archivos(ruta: Path) -> set:
    return {p.relative_to(ruta).as_posix() for p in ruta.rglob("*") if p.is_file()}


def test_estructura_completa_con_ocultos_y_scripts(tmp_path):
    destino = tmp_path / "mi-wiki"
    r = correr(INIT, destino)
    assert r.returncode == 0, r.stderr
    assert archivos(destino) == ESPERADOS
    assert json.loads((destino / "raw/.hashes.json").read_text(encoding="utf-8")) == {}
    for script in ("lint.py", "log.py"):
        assert (destino / "scripts" / script).read_bytes() == (KIT / "scripts" / script).read_bytes()
    # Los archivos sin marcador se copian idénticos.
    for rel in (".claude/commands/ingest.md", ".claude/commands/consolidar.md", "wiki/log.md", "raw/.gitkeep"):
        assert (destino / rel).read_bytes() == (KIT / "plantilla" / rel).read_bytes()


def test_nombre_por_defecto_es_la_carpeta(tmp_path):
    destino = tmp_path / "wiki-de-prueba"
    assert correr(INIT, destino).returncode == 0
    for rel in ("CLAUDE.md", "wiki/index.md"):
        texto = (destino / rel).read_text(encoding="utf-8")
        assert "{{NOMBRE}}" not in texto
        assert "wiki-de-prueba" in texto


def test_nombre_reemplaza_marcador(tmp_path):
    destino = tmp_path / "v"
    assert correr(INIT, destino, "--nombre", "Mi wiki").returncode == 0
    for rel in ("CLAUDE.md", "wiki/index.md"):
        texto = (destino / rel).read_text(encoding="utf-8")
        assert "{{NOMBRE}}" not in texto
        assert texto.startswith("# Mi wiki")


def test_carpeta_existente_vacia_es_valida(tmp_path):
    destino = tmp_path / "vacia"
    destino.mkdir()
    assert correr(INIT, destino).returncode == 0
    assert archivos(destino) == ESPERADOS


def test_aborta_si_no_esta_vacia(tmp_path):
    destino = tmp_path / "ocupada"
    destino.mkdir()
    (destino / "mio.txt").write_text("no tocar\n", encoding="utf-8")
    r = correr(INIT, destino)
    assert r.returncode != 0
    assert "no está vacía" in r.stderr
    assert archivos(destino) == {"mio.txt"}


def test_force_sobrescribe_plantilla_sin_borrar_lo_demas(tmp_path):
    destino = tmp_path / "v"
    assert correr(INIT, destino).returncode == 0
    (destino / "CLAUDE.md").write_text("roto\n", encoding="utf-8")
    (destino / "notas").mkdir()
    (destino / "notas/mia.md").write_text("mía\n", encoding="utf-8")
    registro = '{"raw/2026-01-01-x.md": "abc"}\n'
    (destino / "raw/.hashes.json").write_text(registro, encoding="utf-8")

    r = correr(INIT, destino, "--force", "--nombre", "Reparada")
    assert r.returncode == 0, r.stderr
    assert (destino / "CLAUDE.md").read_text(encoding="utf-8").startswith("# Reparada")
    assert (destino / "notas/mia.md").read_text(encoding="utf-8") == "mía\n"
    # El registro de hashes no es de plantilla: se conserva.
    assert (destino / "raw/.hashes.json").read_text(encoding="utf-8") == registro
    assert ESPERADOS <= archivos(destino)


@pytest.mark.skipif(shutil.which("git") is None, reason="git no está instalado")
def test_git_init(tmp_path):
    destino = tmp_path / "v"
    r = correr(INIT, destino, "--git")
    assert r.returncode == 0, r.stderr
    assert (destino / ".git").is_dir()


def test_marcador_de_idioma_es_por_defecto(tmp_path):
    destino = tmp_path / "v"
    assert correr(INIT, destino).returncode == 0
    assert json.loads((destino / ".second-brain.json").read_text(encoding="utf-8")) == {"lang": "es"}


def test_lang_en_usa_plantilla_en(tmp_path):
    destino = tmp_path / "my-wiki"
    r = correr(INIT, destino, "--lang", "en", "--name", "Test")
    assert r.returncode == 0, r.stderr
    assert archivos(destino) == ESPERADOS_EN
    assert json.loads((destino / ".second-brain.json").read_text(encoding="utf-8")) == {"lang": "en"}
    for rel in ("CLAUDE.md", "wiki/index.md"):
        texto = (destino / rel).read_text(encoding="utf-8")
        assert "{{NAME}}" not in texto
        assert texto.startswith("# Test")
    for rel in (".claude/commands/ingest.md", ".claude/commands/consolidate.md", "wiki/log.md", "raw/.gitkeep"):
        assert (destino / rel).read_bytes() == (KIT / "plantilla-en" / rel).read_bytes()
    assert "MAESTRO rules" in (destino / "CLAUDE.md").read_text(encoding="utf-8")
    assert "created in" in r.stdout and "Next step" in r.stdout


def test_lang_en_mensajes_de_error_en_ingles(tmp_path):
    destino = tmp_path / "busy"
    destino.mkdir()
    (destino / "mine.txt").write_text("keep\n", encoding="utf-8")
    r = correr(INIT, destino, "--lang", "en")
    assert r.returncode == 1
    assert "is not empty" in r.stderr
    assert archivos(destino) == {"mine.txt"}


def test_force_reescribe_el_marcador_de_idioma(tmp_path):
    destino = tmp_path / "v"
    assert correr(INIT, destino).returncode == 0
    assert correr(INIT, destino, "--force", "--lang", "en").returncode == 0
    assert json.loads((destino / ".second-brain.json").read_text(encoding="utf-8")) == {"lang": "en"}


@pytest.mark.parametrize("lang, comando", [("es", "consolidar.md"), ("en", "consolidate.md")])
def test_vault_nuevo_trae_consolidar_con_su_cuadrante(tmp_path, lang, comando):
    """El vault nuevo trae el comando de consolidación y el lint no avisa de cuadrante faltante."""
    destino = tmp_path / "v"
    assert correr(INIT, destino, "--lang", lang).returncode == 0
    assert (destino / ".claude/commands" / comando).is_file()
    r = correr(destino / "scripts/lint.py", destino, "--json")
    assert r.returncode == 0, r.stdout
    datos = json.loads(r.stdout)
    avisos = datos["avisos"] if lang == "es" else datos["warnings"]
    assert avisos == []
