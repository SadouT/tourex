#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Structures de donnees partagees par les differents modules."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class Statut(str, Enum):
    """Statut d'une date apres comparaison entre MZ1 et BACKUP-MZ."""

    OK = "OK"                    # meme nombre de fichiers des deux cotes
    DIFFERENCE = "Difference"    # ecart de nombre de fichiers
    MZ1_SEUL = "MZ1 seul"        # present uniquement sur MZ1
    BACKUP_SEUL = "BACKUP seul"  # present uniquement sur BACKUP
    VIDE = "Vide"                # dossier vide (MZ1 et/ou BACKUP)
    ERREUR = "Erreur"            # erreur d'acces lors du scan

    def __str__(self) -> str:  # pragma: no cover - trivial
        return self.value


@dataclass(slots=True)
class DirStat:
    """Statistiques d'un sous-repertoire date pour un serveur donne.

    Attributes:
        name: Nom du dossier (la date, ex. ``"20260701"``).
        path: Chemin complet du dossier sur son serveur.
        file_count: Nombre de fichiers (comptage recursif).
        total_size: Taille cumulee des fichiers en octets.
        error: Message d'erreur si le dossier n'a pas pu etre lu, sinon None.
    """

    name: str
    path: str
    file_count: int = 0
    total_size: int = 0
    error: Optional[str] = None

    @property
    def is_empty(self) -> bool:
        """True si le dossier est lisible mais ne contient aucun fichier."""
        return self.error is None and self.file_count == 0


@dataclass(slots=True)
class ComparisonRow:
    """Ligne du tableau de comparaison pour une date donnee.

    Attributes:
        date: La date comparee (nom du dossier).
        mz1: Statistiques cote MZ1, ou None si absent de MZ1.
        backup: Statistiques cote BACKUP, ou None si absent de BACKUP.
        statut: Statut resultant de la comparaison.
    """

    date: str
    mz1: Optional[DirStat]
    backup: Optional[DirStat]
    statut: Statut

    @property
    def mz1_count(self) -> Optional[int]:
        """Nombre de fichiers cote MZ1 (None si absent)."""
        return self.mz1.file_count if self.mz1 else None

    @property
    def backup_count(self) -> Optional[int]:
        """Nombre de fichiers cote BACKUP (None si absent)."""
        return self.backup.file_count if self.backup else None

    @property
    def ecart(self) -> Optional[int]:
        """Ecart |MZ1 - BACKUP| en nombre de fichiers (None si non comparable)."""
        if self.mz1 is None or self.backup is None:
            return None
        return abs(self.mz1.file_count - self.backup.file_count)

    @property
    def mz1_size(self) -> int:
        """Taille cote MZ1 en octets (0 si absent)."""
        return self.mz1.total_size if self.mz1 else 0

    @property
    def is_deletable_candidate(self) -> bool:
        """True si la date existe cote MZ1 et peut donc etre proposee au nettoyage."""
        return self.mz1 is not None

    @property
    def is_safe_to_delete(self) -> bool:
        """True si la suppression est sure sans l'option --force.

        Une suppression est jugee sure lorsque la sauvegarde existe et contient
        exactement le meme nombre de fichiers que MZ1.
        """
        return self.statut is Statut.OK


@dataclass(slots=True)
class PairResult:
    """Resultat complet de la comparaison d'un couple de repertoires.

    Attributes:
        name: Libelle du couple (issu de la configuration).
        mz1_dir: Chemin du repertoire MZ1.
        backup_dir: Chemin du repertoire BACKUP.
        rows: Lignes de comparaison, triees par date.
    """

    name: str
    mz1_dir: str
    backup_dir: str
    rows: list[ComparisonRow] = field(default_factory=list)


@dataclass(slots=True)
class RunSummary:
    """Compteurs cumules pour le resume final d'execution."""

    dirs_scanned: int = 0
    files_counted: int = 0
    identical: int = 0
    different: int = 0
    errors: int = 0
    deleted_dirs: int = 0
    freed_bytes: int = 0
