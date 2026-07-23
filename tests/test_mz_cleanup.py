#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests unitaires de l'outil mz_cleanup.

Executer avec :
    python -m pytest tests/test_mz_cleanup.py
    # ou, sans pytest :
    python tests/test_mz_cleanup.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

# Permet l'import du paquet lorsque les tests sont lances directement.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from mz_cleanup.comparator import compare  # noqa: E402
from mz_cleanup.config import ConfigError, load_config  # noqa: E402
from mz_cleanup.models import DirStat, Statut  # noqa: E402
from mz_cleanup.scanner import LocalScanner  # noqa: E402
from mz_cleanup.selector import SelectionError, parse_selection  # noqa: E402
from mz_cleanup.utils import human_duration, human_number, human_size  # noqa: E402


# --------------------------------------------------------------------------- #
# utils
# --------------------------------------------------------------------------- #
def test_human_size() -> None:
    assert human_size(0) == "0 o"
    assert human_size(512) == "512 o"
    assert human_size(1024) == "1.00 Kio"
    assert human_size(1024 * 1024) == "1.00 Mio"
    assert human_size(5 * 1024 ** 3) == "5.00 Gio"


def test_human_number() -> None:
    assert human_number(0) == "0"
    assert human_number(1234567) == "1 234 567"


def test_human_duration() -> None:
    assert human_duration(1.5) == "1.50 s"
    assert human_duration(90) == "0:01:30"


# --------------------------------------------------------------------------- #
# comparator
# --------------------------------------------------------------------------- #
def _stat(name: str, count: int, size: int = 0, error: str | None = None) -> DirStat:
    return DirStat(name=name, path=f"/x/{name}", file_count=count, total_size=size, error=error)


def test_compare_statuses() -> None:
    mz1 = {
        "20260701": _stat("20260701", 100),
        "20260702": _stat("20260702", 100),
        "20260703": _stat("20260703", 0),        # vide
        "20260704": _stat("20260704", 50),        # mz1 seul
        "20260705": _stat("20260705", 10, error="boom"),  # erreur
    }
    backup = {
        "20260701": _stat("20260701", 100),       # OK
        "20260702": _stat("20260702", 95),         # difference
        "20260703": _stat("20260703", 5),
        "20260706": _stat("20260706", 30),         # backup seul
        "20260705": _stat("20260705", 10),
    }
    rows = {r.date: r for r in compare(mz1, backup)}
    assert rows["20260701"].statut is Statut.OK
    assert rows["20260702"].statut is Statut.DIFFERENCE
    assert rows["20260702"].ecart == 5
    assert rows["20260703"].statut is Statut.VIDE
    assert rows["20260704"].statut is Statut.MZ1_SEUL
    assert rows["20260706"].statut is Statut.BACKUP_SEUL
    assert rows["20260705"].statut is Statut.ERREUR


def test_deletable_and_safe_flags() -> None:
    rows = {r.date: r for r in compare(
        {"20260701": _stat("20260701", 100), "20260704": _stat("20260704", 50)},
        {"20260701": _stat("20260701", 100), "20260706": _stat("20260706", 30)},
    )}
    assert rows["20260701"].is_deletable_candidate is True
    assert rows["20260701"].is_safe_to_delete is True
    assert rows["20260704"].is_deletable_candidate is True   # mz1 seul
    assert rows["20260704"].is_safe_to_delete is False
    assert rows["20260706"].is_deletable_candidate is False  # backup seul


# --------------------------------------------------------------------------- #
# selector
# --------------------------------------------------------------------------- #
def _rows_for_selection() -> list:
    return compare(
        {
            "20260701": _stat("20260701", 100),
            "20260702": _stat("20260702", 95),
            "20260703": _stat("20260703", 100),
        },
        {
            "20260701": _stat("20260701", 100),   # OK
            "20260702": _stat("20260702", 90),     # difference
            "20260703": _stat("20260703", 100),    # OK
        },
    )


def test_parse_selection_forms() -> None:
    rows = _rows_for_selection()
    assert parse_selection("1", rows) == [0]
    assert parse_selection("1-3", rows) == [0, 1, 2]
    assert parse_selection("1,3", rows) == [0, 2]
    assert parse_selection("3,1", rows) == [0, 2]          # trie + dedoublonne
    assert parse_selection("all", rows) == [0, 1, 2]
    assert parse_selection("ok", rows) == [0, 2]           # statut OK uniquement
    assert parse_selection("2-1", rows) == [0, 1]          # bornes inversees


def test_parse_selection_errors() -> None:
    rows = _rows_for_selection()
    for bad in ("", "0", "4", "1-", "abc", "1-x"):
        try:
            parse_selection(bad, rows)
        except SelectionError:
            continue
        raise AssertionError(f"'{bad}' aurait du lever SelectionError")


# --------------------------------------------------------------------------- #
# LocalScanner (utilise un arbre de fichiers temporaire)
# --------------------------------------------------------------------------- #
def test_local_scanner(tmp_path: Path) -> None:
    parent = tmp_path / "MACH"
    parent.mkdir()
    # dossiers dates valides
    (parent / "20260701").mkdir()
    (parent / "20260701" / "a.txt").write_text("hello")   # 5 octets
    (parent / "20260701" / "b.txt").write_text("world!")  # 6 octets
    (parent / "20260702").mkdir()                          # vide
    # sous-dossier imbrique (comptage recursif)
    nested = parent / "20260703" / "sub"
    nested.mkdir(parents=True)
    (nested / "c.txt").write_text("x")
    # dossier non date (ignore)
    (parent / "extract").mkdir()
    (parent / "extract" / "junk").write_text("nope")

    scanner = LocalScanner(date_pattern=r"\d{8}", date_format="%Y%m%d")
    date_dirs = scanner.list_date_dirs(str(parent))
    names = [n for n, _ in date_dirs]
    assert names == ["20260701", "20260702", "20260703"]

    stats = scanner.scan_parent(str(parent), workers=2)
    assert stats["20260701"].file_count == 2
    assert stats["20260701"].total_size == 11
    assert stats["20260702"].is_empty is True
    assert stats["20260703"].file_count == 1     # recursif


def test_local_scanner_delete(tmp_path: Path) -> None:
    parent = tmp_path / "MACH"
    (parent / "20260701").mkdir(parents=True)
    (parent / "20260701" / "a.txt").write_text("hello")
    scanner = LocalScanner(date_pattern=r"\d{8}", date_format="%Y%m%d")
    freed = scanner.delete_dir(str(parent / "20260701"))
    assert freed == 5
    assert not (parent / "20260701").exists()


# --------------------------------------------------------------------------- #
# config
# --------------------------------------------------------------------------- #
def test_load_config_ini(tmp_path: Path) -> None:
    ini = (
        "[general]\n"
        "dry_run = false\n"
        "workers = 3\n"
        "date_format = %Y%m%d\n\n"
        "[ssh:mz1]\n"
        "enabled = false\n"
        "host = mz1\n"
        "user = mzadmin\n"
        "password = secret\n\n"
        "[pair:EC6]\n"
        "mz1 = /prod/ec6\n"
        "backup = /save/ec6\n"
    )
    path = tmp_path / "c.ini"
    path.write_text(ini, encoding="utf-8")
    config = load_config(str(path))
    assert config.dry_run is False
    assert config.workers == 3
    assert config.date_format == "%Y%m%d"          # pas d'interpolation du '%'
    assert config.mz1_ssh.password == "secret"
    assert config.pairs[0].name == "EC6"
    assert config.pairs[0].mz1 == "/prod/ec6"


def test_load_config_missing_pairs(tmp_path: Path) -> None:
    path = tmp_path / "c.ini"
    path.write_text("[general]\ndry_run = true\n", encoding="utf-8")
    try:
        load_config(str(path))
    except ConfigError:
        return
    raise AssertionError("Une config sans couples aurait du lever ConfigError")


def test_load_config_rejects_non_ini(tmp_path: Path) -> None:
    path = tmp_path / "c.json"
    path.write_text("{}", encoding="utf-8")
    try:
        load_config(str(path))
    except ConfigError:
        return
    raise AssertionError("Une extension non INI aurait du lever ConfigError")


# --------------------------------------------------------------------------- #
# Execution directe (sans pytest)
# --------------------------------------------------------------------------- #
def _run_all() -> None:
    import tempfile

    test_human_size()
    test_human_number()
    test_human_duration()
    test_compare_statuses()
    test_deletable_and_safe_flags()
    test_parse_selection_forms()
    test_parse_selection_errors()
    with tempfile.TemporaryDirectory() as d:
        base = Path(d)
        for sub, func in (
            ("t1", test_local_scanner),
            ("t2", test_local_scanner_delete),
            ("t3", test_load_config_ini),
            ("t4", test_load_config_missing_pairs),
            ("t5", test_load_config_rejects_non_ini),
        ):
            target = base / sub
            target.mkdir(parents=True, exist_ok=True)
            func(target)
    print("Tous les tests sont passes.")


if __name__ == "__main__":
    _run_all()
