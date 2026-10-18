"""Pruebas de empaquetar.py: el archivo único debe permitir reconstruir el kit
byte a byte y no debe contener rutas personales."""
import hashlib
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

KIT = Path(__file__).resolve().parents[1]
EXCLUIR = {".venv", "__pycache__", ".pytest_cache", ".git", ".DS_Store"}


def esperados(raiz: Path) -> list:
    """Archivos que el paquete debe contener, calculados aparte de empaquetar.py."""
    salida = []
    for carpeta, subcarpetas, archivos in os.walk(raiz):
        rel = Path(carpeta).relative_to(raiz)
        subcarpetas[:] = [d for d in subcarpetas
                          if d not in EXCLUIR and not (rel == Path(".") and d == "dist")]
        salida += [(rel / n).as_posix() for n in archivos
                   if n not in EXCLUIR and not n.endswith(".bak") and ".bak-" not in n]
    return sorted(salida)


def reconstruir(md: str, destino: Path, seccion: str = "## Archivos\n") -> list:
    """Recrea en `destino` los archivos de la sección «## Archivos» (o `seccion`) del paquete.

    Es el mismo procedimiento que se le pide a Claude Code: tras `### ruta`, el
    contenido es lo que hay entre la cerca de apertura y su cierre idéntico.
    """
    lineas = md.splitlines(keepends=True)
    i = lineas.index(seccion) + 1
    rutas = []
    while i < len(lineas):
        if lineas[i].startswith("### "):
            rel = lineas[i][4:].rstrip("\n")
            i += 1
            while not lineas[i].strip():
                i += 1
            apertura = re.fullmatch(r"(`{3,})([\w+-]*)\n", lineas[i])
            assert apertura, f"cerca de apertura inválida para {rel}: {lineas[i]!r}"
            cierre = apertura.group(1) + "\n"
            i += 1
            inicio = i
            while lineas[i] != cierre:
                i += 1
            ruta = destino / rel
            ruta.parent.mkdir(parents=True, exist_ok=True)
            ruta.write_bytes("".join(lineas[inicio:i]).encode("utf-8"))
            rutas.append(rel)
        i += 1
    return rutas


@pytest.fixture(scope="module")
def paquete(tmp_path_factory):
    salida = tmp_path_factory.mktemp("dist") / "INSTRUCTIVO_second-brain-kit.md"
    r = subprocess.run([sys.executable, str(KIT / "empaquetar.py"), "--salida", str(salida)],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    return salida.read_text(encoding="utf-8")


def test_roundtrip_byte_a_byte(paquete, tmp_path):
    rutas = reconstruir(paquete, tmp_path)
    assert sorted(rutas) == esperados(KIT)
    for rel in rutas:
        assert (tmp_path / rel).read_bytes() == (KIT / rel).read_bytes(), rel


def test_incluye_ocultos_y_excluye_generados(paquete, tmp_path):
    rutas = set(reconstruir(paquete, tmp_path))
    for oculto in ("plantilla/.claude/commands/ingest.md", "plantilla/raw/.gitkeep",
                   "tests/vault_ejemplo/raw/.hashes.json"):
        assert oculto in rutas
    for rel in rutas:
        partes = set(Path(rel).parts)
        assert not partes & EXCLUIR, rel
        assert not rel.startswith("dist/"), rel


def test_manifiesto_coincide(paquete):
    filas = re.findall(r"^\| `([^`]+)` \| (\d+) \| `([0-9a-f]{64})` \|$", paquete, re.M)
    assert sorted(f[0] for f in filas) == esperados(KIT)
    for rel, tamano, sha in filas:
        datos = (KIT / rel).read_bytes()
        assert int(tamano) == len(datos)
        assert sha == hashlib.sha256(datos).hexdigest()


def test_empieza_con_instrucciones_para_claude_code(paquete):
    assert paquete.startswith("# INSTRUCTIVO")
    assert "Si eres Claude Code y el usuario te pasó este archivo" in paquete[:2000]


def test_sin_rutas_personales(paquete):
    # La cadena se arma por partes para que este archivo (que va dentro del paquete) no la contenga.
    assert "/" + "Users" + "/" not in paquete
    inicio = str(Path.home())
    if len(inicio) > 1:
        assert inicio not in paquete


# --- Paquete en inglés (--lang en) ---------------------------------------------------------

@pytest.fixture(scope="module")
def paquete_en(tmp_path_factory):
    salida = tmp_path_factory.mktemp("dist-en") / "INSTRUCTIONS_second-brain-kit_en.md"
    r = subprocess.run([sys.executable, str(KIT / "empaquetar.py"), "--lang", "en",
                        "--salida", str(salida)], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    return salida.read_text(encoding="utf-8")


def test_en_roundtrip_sha256(paquete_en, tmp_path):
    rutas = reconstruir(paquete_en, tmp_path, "## Files\n")
    assert sorted(rutas) == esperados(KIT)
    for rel in rutas:
        assert (hashlib.sha256((tmp_path / rel).read_bytes()).hexdigest()
                == hashlib.sha256((KIT / rel).read_bytes()).hexdigest()), rel


def test_en_mismos_archivos_que_el_espanol(paquete, paquete_en, tmp_path):
    assert (sorted(reconstruir(paquete_en, tmp_path / "en", "## Files\n"))
            == sorted(reconstruir(paquete, tmp_path / "es")))


def test_en_manifiesto_coincide(paquete_en):
    filas = re.findall(r"^\| `([^`]+)` \| (\d+) \| `([0-9a-f]{64})` \|$", paquete_en, re.M)
    assert sorted(f[0] for f in filas) == esperados(KIT)
    for rel, tamano, sha in filas:
        datos = (KIT / rel).read_bytes()
        assert int(tamano) == len(datos)
        assert sha == hashlib.sha256(datos).hexdigest()


def test_en_encabezado_y_readme(paquete_en):
    assert paquete_en.startswith("# INSTRUCTIONS")
    assert "If you are Claude Code and the user gave you this file" in paquete_en[:2000]
    assert "tests/vault_example_en" in paquete_en[:4000]
    assert "`LINT: GREEN (0 failures)`" in paquete_en[:4000]
    readme = (KIT / "README.en.md").read_text(encoding="utf-8")
    assert readme in paquete_en


def test_incluye_ocultos_nuevos(paquete, paquete_en, tmp_path):
    for md, seccion, carpeta in ((paquete, "## Archivos\n", "es"), (paquete_en, "## Files\n", "en")):
        rutas = set(reconstruir(md, tmp_path / carpeta, seccion))
        for oculto in (".gitignore", "plantilla-en/.claude/commands/ingest.md",
                       "tests/vault_ejemplo/.second-brain.json",
                       "tests/vault_example_en/.second-brain.json",
                       "tests/vault_example_en/raw/.hashes.json"):
            assert oculto in rutas, (carpeta, oculto)


def test_en_sin_rutas_personales(paquete_en):
    assert "/" + "Users" + "/" not in paquete_en
    inicio = str(Path.home())
    if len(inicio) > 1:
        assert inicio not in paquete_en
