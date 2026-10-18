"""Pruebas de scripts/log.py: formato, append-only y registro de hashes de raw/."""
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

KIT = Path(__file__).resolve().parents[1]
LOG = KIT / "scripts" / "log.py"


def correr(*args):
    return subprocess.run([sys.executable, *map(str, args)], capture_output=True, text=True)


@pytest.fixture
def vault(tmp_path):
    destino = tmp_path / "v"
    r = correr(KIT / "init_vault.py", destino)
    assert r.returncode == 0, r.stderr
    return destino


def leer_log(vault: Path) -> bytes:
    return (vault / "wiki/log.md").read_bytes()


def hashes(vault: Path) -> dict:
    return json.loads((vault / "raw/.hashes.json").read_text(encoding="utf-8"))


def test_formato_exacto_de_linea(vault):
    r = correr(LOG, vault, "QUERY", "¿qué es X?\nsegunda línea\r\ntercera", "--fecha", "2026-09-18")
    assert r.returncode == 0, r.stderr
    assert leer_log(vault).decode("utf-8").endswith(
        "\n2026-09-18 | QUERY | ¿qué es X? segunda línea tercera\n")


def test_append_only_lineas_previas_intactas(vault):
    antes = leer_log(vault)
    assert correr(LOG, vault, "INGEST", "uno", "--fecha", "2026-09-18").returncode == 0
    medio = leer_log(vault)
    assert correr(LOG, vault, "LINT", "dos", "--fecha", "2026-09-19").returncode == 0
    despues = leer_log(vault)
    assert medio == antes + b"2026-09-18 | INGEST | uno\n"
    assert despues == medio + b"2026-09-19 | LINT | dos\n"


def test_antepone_salto_si_falta(vault):
    ruta = vault / "wiki/log.md"
    ruta.write_bytes(b"# Log\n\n2026-01-01 | LINT | previa")
    assert correr(LOG, vault, "LINT", "nueva", "--fecha", "2026-09-18").returncode == 0
    assert ruta.read_bytes() == b"# Log\n\n2026-01-01 | LINT | previa\n2026-09-18 | LINT | nueva\n"


@pytest.mark.parametrize("operacion", ["BORRAR", "ingest", ""])
def test_operacion_invalida(vault, operacion):
    antes = leer_log(vault)
    r = correr(LOG, vault, operacion, "algo")
    assert r.returncode == 2
    assert leer_log(vault) == antes


def test_fecha_invalida(vault):
    antes = leer_log(vault)
    assert correr(LOG, vault, "LINT", "algo", "--fecha", "18/09/2026").returncode == 2
    assert leer_log(vault) == antes


def test_hash_se_registra_una_sola_vez(vault):
    fuente = vault / "raw/2026-09-18-fuente.md"
    fuente.write_text("original\n", encoding="utf-8")
    original = hashlib.sha256(b"original\n").hexdigest()

    r = correr(LOG, vault, "INGEST", "primera", "--raw", "raw/2026-09-18-fuente.md")
    assert r.returncode == 0, r.stderr
    assert hashes(vault) == {"raw/2026-09-18-fuente.md": original}

    fuente.write_text("modificada\n", encoding="utf-8")
    r = correr(LOG, vault, "INGEST", "segunda", "--raw", "raw/2026-09-18-fuente.md")
    assert r.returncode == 0, r.stderr
    assert "ya registrado" in r.stdout
    assert hashes(vault) == {"raw/2026-09-18-fuente.md": original}


def test_raw_inexistente_no_escribe_nada(vault):
    antes_log, antes_hashes = leer_log(vault), hashes(vault)
    r = correr(LOG, vault, "INGEST", "algo", "--raw", "raw/no-existe.md")
    assert r.returncode == 2
    assert leer_log(vault) == antes_log
    assert hashes(vault) == antes_hashes


def test_raw_fuera_de_raw(vault):
    r = correr(LOG, vault, "INGEST", "algo", "--raw", "wiki/index.md")
    assert r.returncode == 2
    assert hashes(vault) == {}
