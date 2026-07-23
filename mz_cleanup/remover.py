#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Suppression securisee des repertoires selectionnes sur MZ1."""

from __future__ import annotations

from dataclasses import dataclass

from .logging_setup import get_logger
from .models import ComparisonRow
from .scanner import Scanner


@dataclass(slots=True)
class DeletionOutcome:
    """Resultat de suppression d'un dossier.

    Attributes:
        row: La ligne de comparaison concernee.
        deleted: True si le dossier a reellement ete supprime.
        skipped_reason: Raison de non-suppression (sinon None).
        freed_bytes: Espace libere en octets (0 si non supprime / dry-run).
        error: Message d'erreur eventuel.
    """

    row: ComparisonRow
    deleted: bool
    skipped_reason: str | None = None
    freed_bytes: int = 0
    error: str | None = None


class Remover:
    """Applique la suppression des dossiers MZ1 en respectant les garde-fous."""

    def __init__(self, scanner: Scanner, dry_run: bool, force: bool) -> None:
        """Initialise le remover.

        Args:
            scanner: Scanner MZ1 (local ou distant) capable de supprimer.
            dry_run: Si True, aucune suppression reelle n'est effectuee.
            force: Autorise la suppression de dossiers non sauvegardes a l'identique.
        """
        self._scanner = scanner
        self._dry_run = dry_run
        self._force = force
        self._log = get_logger()

    def delete(self, rows: list[ComparisonRow]) -> list[DeletionOutcome]:
        """Supprime (ou simule) la suppression des dossiers fournis.

        Un dossier dont le statut n'est pas sur est ignore, sauf si ``force``
        est actif. En mode ``dry_run``, la suppression est journalisee mais non
        executee, tout en estimant l'espace qui serait libere.

        Args:
            rows: Lignes retenues pour suppression (candidats MZ1).

        Returns:
            La liste des ``DeletionOutcome`` correspondants.
        """
        outcomes: list[DeletionOutcome] = []
        for row in rows:
            outcomes.append(self._delete_one(row))
        return outcomes

    def _delete_one(self, row: ComparisonRow) -> DeletionOutcome:
        """Traite un dossier unique."""
        if row.mz1 is None:  # ne devrait pas arriver (candidats filtres en amont)
            return DeletionOutcome(row, deleted=False, skipped_reason="absent de MZ1")

        if not row.is_safe_to_delete and not self._force:
            reason = f"sauvegarde non conforme (statut {row.statut}) ; --force requis"
            self._log.warning("Suppression ignoree pour %s : %s", row.date, reason)
            return DeletionOutcome(row, deleted=False, skipped_reason=reason)

        path = row.mz1.path
        if self._dry_run:
            freed = row.mz1_size
            self._log.info(
                "[DRY-RUN] Suppression simulee de %s (%d fichiers, %d octets).",
                path,
                row.mz1_count or 0,
                freed,
            )
            return DeletionOutcome(row, deleted=False, skipped_reason="dry-run", freed_bytes=freed)

        try:
            freed = self._scanner.delete_dir(path)  # type: ignore[attr-defined]
            self._log.info("Dossier supprime : %s (%d octets liberes).", path, freed)
            return DeletionOutcome(row, deleted=True, freed_bytes=freed)
        except Exception as exc:
            self._log.error("Echec de suppression de %s : %s", path, exc)
            return DeletionOutcome(row, deleted=False, error=str(exc))
