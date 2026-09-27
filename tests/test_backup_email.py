"""Tests for scripts/backup_email.py (dotenv loading + gzip)."""

import gzip
import importlib.util
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parent.parent / "scripts" / "backup_email.py"


def load_module():
    spec = importlib.util.spec_from_file_location("backup_email", SCRIPTS)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture()
def be():
    return load_module()


def test_load_dotenv_reads_root_env(tmp_path, monkeypatch, be):
    """Lê KEY=VALUE, ignora comentários, suporta aspas e export."""
    env = tmp_path / ".env"
    env.write_text(
        "# comentário\n"
        "BACKUP_EMAIL_TO=a@gmail.com\n"
        "BACKUP_OPT='com espacos'\n"
        "NOTA=fiscal #123\n"
        "EQ=a=b\n"
        'export QUOTED="com espaços"\n'
        "VAZIA=\n"
        "SEM_IGUALDADE\n",
        encoding="utf-8",
    )
    for key in ("BACKUP_EMAIL_TO", "BACKUP_OPT", "NOTA", "EQ", "QUOTED", "VAZIA"):
        monkeypatch.delenv(key, raising=False)

    be.load_dotenv(env)

    import os

    assert os.environ["BACKUP_EMAIL_TO"] == "a@gmail.com"
    assert os.environ["BACKUP_OPT"] == "com espacos"
    assert os.environ["NOTA"] == "fiscal #123"
    assert os.environ["EQ"] == "a=b"
    assert os.environ["QUOTED"] == "com espaços"
    assert os.environ["VAZIA"] == ""
    assert "SEM_IGUALDADE" not in os.environ


def test_load_dotenv_respects_existing_env(tmp_path, monkeypatch, be):
    """Variável já presente no ambiente tem prioridade sobre o .env."""
    env = tmp_path / ".env"
    env.write_text("POSTGRES_PASSWORD=a\n", encoding="utf-8")
    monkeypatch.setenv("POSTGRES_PASSWORD", "b")

    be.load_dotenv(env)

    import os

    assert os.environ["POSTGRES_PASSWORD"] == "b"


def test_load_dotenv_missing_file_ok(tmp_path, be):
    """Arquivo inexistente não quebra (ex.: dev sem .env)."""
    be.load_dotenv(tmp_path / ".env-inexistente")


def test_load_dotenv_never_executes(tmp_path, monkeypatch, be, tmpdir):
    """Conteúdo malicioso é tratado como dado, nunca executado."""
    marker = Path(str(tmpdir)) / "pwned"
    env = tmp_path / ".env"
    env.write_text(
        f"EVIL=$(touch {marker})\nOUTRA=`touch {marker}`\n", encoding="utf-8"
    )
    monkeypatch.delenv("EVIL", raising=False)
    monkeypatch.delenv("OUTRA", raising=False)

    be.load_dotenv(env)

    assert not marker.exists()


def test_gzip_roundtrip_py310(tmp_path):
    """GzipFile com mtime funciona no Python 3.10 e o conteúdo volta intacto."""
    target = tmp_path / "dump.sql.gz"
    with gzip.GzipFile(str(target), "wb", mtime=0) as gz:
        gz.write(b"CREATE TABLE t (id int);")
    with gzip.open(str(target), "rb") as fh:
        assert fh.read() == b"CREATE TABLE t (id int);"
