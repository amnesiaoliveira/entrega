"""Snapshot consistente do SQLite, ZIP verificado e restauração sem sobrescrita."""

import argparse
import json
import logging
import re
import sqlite3
import tempfile
import uuid
from contextlib import closing
from datetime import UTC, datetime, timedelta
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

BACKUP_NAME = re.compile(r"baranda-\d{8}T\d{12}Z-[0-9a-f]{8}\.zip$")


def validate_database(path):
    with closing(sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)) as db:
        if db.execute("PRAGMA integrity_check").fetchall() != [("ok",)]:
            raise ValueError("Falha na integridade do banco de dados.")


def snapshot(source, destination):
    source, destination = Path(source), Path(destination)
    if destination.exists():
        raise FileExistsError(destination)
    with (
        closing(
            sqlite3.connect(source.resolve().as_uri() + "?mode=ro", uri=True)
        ) as db,
        closing(sqlite3.connect(destination)) as target,
    ):
        db.backup(target)
    validate_database(destination)


def verify_archive(archive):
    with ZipFile(archive) as bundle, tempfile.TemporaryDirectory() as temporary:
        if set(bundle.namelist()) != {"db.sqlite3", "production.json", "metadata.json"}:
            raise ValueError("Conteúdo inesperado no backup.")
        if bundle.testzip() is not None:
            raise ValueError("Backup corrompido.")
        json.loads(bundle.read("production.json"))
        json.loads(bundle.read("metadata.json"))
        database = Path(temporary) / "db.sqlite3"
        database.write_bytes(bundle.read("db.sqlite3"))
        validate_database(database)


def create_backup(config_file, destination, days=30):
    if days < 1:
        raise ValueError("A retenção deve ser de pelo menos um dia.")
    config_file, destination = Path(config_file), Path(destination)
    config = json.loads(config_file.read_text(encoding="utf-8-sig"))
    destination.mkdir(parents=True, exist_ok=True)
    now = datetime.now(UTC)
    name = f"baranda-{now:%Y%m%dT%H%M%S%f}Z-{uuid.uuid4().hex[:8]}.zip"
    final = destination / name
    # Temporários no destino para publicação atômica no mesmo volume.
    with tempfile.TemporaryDirectory(dir=destination) as temporary:
        database = Path(temporary) / "db.sqlite3"
        snapshot(config["DJANGO_DATABASE_PATH"], database)
        archive = Path(temporary) / "backup.zip"
        with ZipFile(archive, "w", compression=ZIP_DEFLATED) as bundle:
            bundle.write(database, "db.sqlite3")
            bundle.writestr("production.json", json.dumps(config, ensure_ascii=False))
            bundle.writestr(
                "metadata.json", json.dumps({"created_at": now.isoformat()})
            )
        verify_archive(archive)
        archive.replace(final)
    # Só elimina backups deste utilitário após confirmar a nova cópia.
    cutoff = (now - timedelta(days=days)).timestamp()
    for old in destination.iterdir():
        if (
            old.is_file()
            and BACKUP_NAME.fullmatch(old.name)
            and old.stat().st_mtime < cutoff
        ):
            old.unlink()
    logs = Path(config["DJANGO_DATABASE_PATH"]).parent / "logs"
    if logs.is_dir():
        for old in logs.iterdir():
            if (
                old.is_file()
                and re.fullmatch(r"(?:servico|erros)-[0-9T.]+\.log", old.name)
                and old.stat().st_mtime < (now - timedelta(days=30)).timestamp()
            ):
                old.unlink()
    logging.info("Backup verificado: %s", final)
    return final


def restore_archive(archive, destination):
    verify_archive(archive)
    destination = Path(destination)
    # Modo exclusivo: nunca substitui um banco existente ou em uso.
    with ZipFile(archive) as bundle, destination.open("xb") as output:
        output.write(bundle.read("db.sqlite3"))
    validate_database(destination)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    backup = commands.add_parser("create")
    backup.add_argument("--config", required=True)
    backup.add_argument("--destination", required=True)
    backup.add_argument("--days", type=int, default=30)
    verify = commands.add_parser("verify")
    verify.add_argument("archive")
    restore = commands.add_parser("restore")
    restore.add_argument("archive")
    restore.add_argument("destination")
    copy = commands.add_parser("snapshot")
    copy.add_argument("source")
    copy.add_argument("destination")
    args = parser.parse_args()
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s"
    )
    if args.command == "create":
        config = json.loads(Path(args.config).read_text(encoding="utf-8-sig"))
        log = Path(config["DJANGO_DATABASE_PATH"]).parent / "logs" / "backup.log"
        from logging.handlers import RotatingFileHandler

        log.parent.mkdir(exist_ok=True)
        logging.getLogger().addHandler(
            RotatingFileHandler(log, maxBytes=1048576, backupCount=5)
        )
    try:
        if args.command == "create":
            create_backup(args.config, args.destination, args.days)
        elif args.command == "verify":
            verify_archive(args.archive)
        elif args.command == "restore":
            restore_archive(args.archive, args.destination)
        else:
            snapshot(args.source, args.destination)
    except Exception:
        logging.exception("Operação de backup falhou")
        raise SystemExit(1) from None


if __name__ == "__main__":
    main()
