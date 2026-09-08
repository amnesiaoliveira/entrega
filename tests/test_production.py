"""Valida backups recuperáveis e o processo real de produção com dados isolados."""

import json
import os
import socket
import sqlite3
import subprocess
import sys
import time
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import urlopen

import pytest

from scripts.backup import create_backup, restore_archive, snapshot, verify_archive

ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture
def production(tmp_path):
    database = tmp_path / "db.sqlite3"
    with sqlite3.connect(database) as db:
        db.execute("CREATE TABLE delivery (name TEXT)")
        db.execute("INSERT INTO delivery VALUES ('Cliente preservado')")
    config = tmp_path / "production.json"
    config.write_text(
        json.dumps(
            {
                "DJANGO_DEBUG": "0",
                "DJANGO_SECRET_KEY": "isolated-test-key-" * 5,
                "DJANGO_DATABASE_PATH": str(database),
                "DJANGO_ALLOWED_HOSTS": "127.0.0.1",
                "DJANGO_HTTPS": "0",
                "DJANGO_TIME_ZONE": "America/La_Paz",
                "PORT": 0,
            }
        ),
        encoding="utf-8",
    )
    return config, database


def test_backup_restores_committed_data_and_keeps_unrelated_files(production, tmp_path):
    config, database = production
    destination = tmp_path / "backups"
    first = create_backup(config, destination, days=1)
    os.utime(first, (0, 0))
    unrelated = destination / "manual.zip"
    unrelated.write_bytes(b"preserve")
    os.utime(unrelated, (0, 0))
    # Copia com a conexão original aberta, incluindo WAL.
    with sqlite3.connect(database) as db:
        db.execute("PRAGMA journal_mode=WAL")
        db.execute("INSERT INTO delivery VALUES ('Outro cliente')")
        db.commit()
        archive = create_backup(config, destination, days=1)
    assert not first.exists()
    assert unrelated.exists()
    verify_archive(archive)
    restored = tmp_path / "restored.sqlite3"
    restore_archive(archive, restored)
    with sqlite3.connect(restored) as db:
        assert db.execute("SELECT name FROM delivery").fetchall() == [
            ("Cliente preservado",),
            ("Outro cliente",),
        ]
    with pytest.raises(FileExistsError):
        restore_archive(archive, restored)


def test_failed_backup_preserves_previous_copies(production, tmp_path):
    config, database = production
    destination = tmp_path / "backups"
    archive = create_backup(config, destination)
    os.utime(archive, (0, 0))
    database.write_bytes(b"not a database")
    with pytest.raises(sqlite3.DatabaseError):
        create_backup(config, destination, days=1)
    assert archive.exists()
    verify_archive(archive)


def test_snapshot_does_not_create_missing_source_or_overwrite(production, tmp_path):
    _, database = production
    with pytest.raises(FileExistsError):
        snapshot(database, database)
    missing = tmp_path / "missing.sqlite3"
    with pytest.raises(sqlite3.OperationalError):
        snapshot(missing, tmp_path / "copy.sqlite3")
    assert not missing.exists()


@pytest.mark.parametrize("https", ["0", "1"])
def test_waitress_serves_login_static_and_rejects_unknown_hosts(production, https):
    config, _ = production
    data = json.loads(config.read_text(encoding="utf-8"))
    data["DJANGO_HTTPS"] = https
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        data["PORT"] = sock.getsockname()[1]
    config.write_text(json.dumps(data), encoding="utf-8")
    process = subprocess.Popen(
        [sys.executable, str(ROOT / "servico.py"), "--config", str(config)],
        cwd=ROOT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    base = f"http://127.0.0.1:{data['PORT']}"
    try:
        for _ in range(50):
            assert process.poll() is None, "Waitress encerrou na inicialização"
            try:
                with urlopen(base + "/entrar/", timeout=1) as response:
                    assert response.status == 200
                    assert "csrftoken=" in response.headers["Set-Cookie"]
                    assert ("Secure" in response.headers["Set-Cookie"]) == (
                        https == "1"
                    )
                    break
            except OSError:
                time.sleep(0.1)
        else:
            pytest.fail("Waitress não respondeu")
        with urlopen(base + "/static/theme.css", timeout=3) as response:
            assert response.status == 200
            assert b"--brand-primary" in response.read()
        with pytest.raises(HTTPError) as error:
            urlopen(base.replace("127.0.0.1", "localhost") + "/entrar/", timeout=3)
        assert error.value.code == 400
        assert b"Traceback" not in error.value.read()
    finally:
        process.terminate()
        process.wait(timeout=10)
