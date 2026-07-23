#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Comparaison des repertoires MZ1 et BACKUP-MZ."""

from __future__ import annotations

from .logging_setup import get_logger
from .models import ComparisonRow, DirStat, Statut


def compare(
    mz1_stats: dict[str, DirStat],
    backup_stats: dict[str, DirStat],
) -> list[ComparisonRow]:
    """Compare les statistiques des deux serveurs date par date.

    La logique de statut applique les regles suivantes, dans l'ordre :
        1. une erreur d'acces d'un cote      -> ``ERREUR`` ;
        2. date presente uniquement sur MZ1  -> ``MZ1_SEUL`` ;
        3. date presente uniquement sur BACKUP -> ``BACKUP_SEUL`` ;
        4. dossier(s) vide(s)                -> ``VIDE`` ;
        5. nombres de fichiers egaux         -> ``OK`` ;
        6. sinon                             -> ``DIFFERENCE``.

    Args:
        mz1_stats: Statistiques cote MZ1 ``{date: DirStat}``.
        backup_stats: Statistiques cote BACKUP ``{date: DirStat}``.

    Returns:
        La liste des ``ComparisonRow`` triee par date croissante.
    """
    log = get_logger()
    rows: list[ComparisonRow] = []
    all_dates = sorted(set(mz1_stats) | set(backup_stats))

    for date in all_dates:
        mz1 = mz1_stats.get(date)
        backup = backup_stats.get(date)
        statut = _determine_status(mz1, backup)
        rows.append(ComparisonRow(date=date, mz1=mz1, backup=backup, statut=statut))
        log.debug(
            "Comparaison %s : mz1=%s backup=%s -> %s",
            date,
            mz1.file_count if mz1 else "-",
            backup.file_count if backup else "-",
            statut,
        )
    return rows


def _determine_status(mz1: DirStat | None, backup: DirStat | None) -> Statut:
    """Determine le statut d'une date a partir des stats des deux cotes."""
    if (mz1 and mz1.error) or (backup and backup.error):
        return Statut.ERREUR
    if mz1 and backup is None:
        return Statut.MZ1_SEUL
    if backup and mz1 is None:
        return Statut.BACKUP_SEUL
    assert mz1 is not None and backup is not None  # les deux existent ici
    if mz1.is_empty or backup.is_empty:
        return Statut.VIDE
    if mz1.file_count == backup.file_count:
        return Statut.OK
    return Statut.DIFFERENCE
