#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Affichage terminal : couleurs, barre de progression et tableaux.

L'implementation est autonome (aucune dependance externe) et repose sur des
codes ANSI. Les couleurs sont automatiquement desactivees si la sortie n'est
pas un terminal ou si l'utilisateur passe ``--no-color``.
"""

from __future__ import annotations

import sys
import time
from typing import Optional

from .models import ComparisonRow, PairResult, RunSummary, Statut
from .utils import human_duration, human_number, human_size

# Codes ANSI ---------------------------------------------------------------- #
_RESET = "\033[0m"
_BOLD = "\033[1m"
_DIM = "\033[2m"
_GREEN = "\033[32m"
_YELLOW = "\033[33m"
_RED = "\033[31m"
_CYAN = "\033[36m"
_MAGENTA = "\033[35m"

# Couleur associee a chaque statut.
_STATUS_COLOR = {
    Statut.OK: _GREEN,
    Statut.DIFFERENCE: _YELLOW,
    Statut.MZ1_SEUL: _CYAN,
    Statut.BACKUP_SEUL: _MAGENTA,
    Statut.VIDE: _DIM,
    Statut.ERREUR: _RED,
}


class Console:
    """Petit assistant d'affichage gerant la coloration et le flux de sortie."""

    def __init__(self, use_color: Optional[bool] = None, stream=None) -> None:
        """Initialise la console.

        Args:
            use_color: Force l'activation/desactivation des couleurs. Si None,
                les couleurs sont activees uniquement pour un terminal.
            stream: Flux de sortie (par defaut ``sys.stdout``).
        """
        self.stream = stream or sys.stdout
        if use_color is None:
            use_color = hasattr(self.stream, "isatty") and self.stream.isatty()
        self.use_color = bool(use_color)

    def color(self, text: str, code: str, bold: bool = False) -> str:
        """Enveloppe ``text`` dans des codes couleur si actives."""
        if not self.use_color:
            return text
        prefix = code + (_BOLD if bold else "")
        return f"{prefix}{text}{_RESET}"

    def print(self, text: str = "") -> None:
        """Ecrit une ligne sur le flux de sortie."""
        print(text, file=self.stream)

    def rule(self, title: str = "") -> None:
        """Trace une ligne de separation, avec un titre optionnel."""
        width = 78
        if title:
            title = f" {title} "
            pad = max(0, width - len(title))
            left = pad // 2
            line = "-" * left + title + "-" * (pad - left)
        else:
            line = "-" * width
        self.print(self.color(line, _DIM))

    # -- Statuts ------------------------------------------------------------ #
    def status_label(self, statut: Statut) -> str:
        """Retourne le libelle colore d'un statut."""
        return self.color(str(statut), _STATUS_COLOR.get(statut, _RESET))


class ProgressBar:
    """Barre de progression textuelle mise a jour sur ``stderr``.

    Elle est volontairement independante de la console de sortie principale afin
    de ne pas polluer les tableaux ou les redirections de ``stdout``.
    """

    def __init__(self, total: int, label: str, use_color: bool, width: int = 32) -> None:
        """Initialise la barre.

        Args:
            total: Nombre total d'unites a traiter.
            label: Libelle affiche a gauche de la barre.
            use_color: Active la coloration.
            width: Largeur de la barre en caracteres.
        """
        self.total = max(1, total)
        self.label = label
        self.width = width
        self.use_color = use_color
        self.count = 0
        self._start = time.monotonic()
        self._enabled = sys.stderr.isatty()

    def update(self, current: str = "") -> None:
        """Incremente le compteur et redessine la barre.

        Args:
            current: Nom de l'element en cours (affiche a droite).
        """
        self.count += 1
        if not self._enabled:
            return
        ratio = min(1.0, self.count / self.total)
        filled = int(self.width * ratio)
        bar = "#" * filled + "-" * (self.width - filled)
        if self.use_color:
            bar = f"\033[36m{bar}\033[0m"
        text = (
            f"\r{self.label} [{bar}] {self.count}/{self.total} "
            f"({ratio * 100:5.1f}%) {current[:20]:<20}"
        )
        sys.stderr.write(text)
        sys.stderr.flush()

    def close(self) -> None:
        """Termine la barre en affichant la duree ecoulee."""
        if not self._enabled:
            return
        elapsed = time.monotonic() - self._start
        sys.stderr.write(
            f"\r{self.label} [{'#' * self.width}] {self.count}/{self.total} "
            f"(100.0%) termine en {human_duration(elapsed)}"
            + " " * 10
            + "\n"
        )
        sys.stderr.flush()


# --------------------------------------------------------------------------- #
# Tableaux
# --------------------------------------------------------------------------- #
def render_comparison_table(console: Console, result: PairResult) -> None:
    """Affiche le tableau de comparaison d'un couple de repertoires.

    Args:
        console: Console de sortie.
        result: Resultat de comparaison du couple.
    """
    console.print()
    console.rule(f"Comparaison : {result.name}")
    console.print(console.color(f"  MZ1    : {result.mz1_dir}", _DIM))
    console.print(console.color(f"  BACKUP : {result.backup_dir}", _DIM))
    console.print()

    headers = ["#", "Date", "Nb MZ1", "Nb BACKUP", "Ecart", "Statut"]
    widths = [4, 12, 14, 14, 8, 14]

    def fmt_row(cells: list[str]) -> str:
        return "  ".join(
            cell.ljust(width) if i == 1 else cell.rjust(width)
            for i, (cell, width) in enumerate(zip(cells, widths))
        )

    console.print(console.color(fmt_row(headers), _BOLD))
    console.print(console.color("  ".join("-" * w for w in widths), _DIM))

    for index, row in enumerate(result.rows, start=1):
        mz1 = human_number(row.mz1_count) if row.mz1_count is not None else "-"
        backup = human_number(row.backup_count) if row.backup_count is not None else "-"
        ecart = human_number(row.ecart) if row.ecart is not None else "-"
        cells = [str(index), row.date, mz1, backup, ecart, str(row.statut)]
        line = fmt_row(cells)
        # Colorise l'ensemble de la ligne selon le statut.
        console.print(console.color(line, _STATUS_COLOR.get(row.statut, _RESET)))

    _render_pair_footnotes(console, result.rows)


def _render_pair_footnotes(console: Console, rows: list[ComparisonRow]) -> None:
    """Affiche sous le tableau les anomalies detectees (regroupees)."""
    def dates(statut: Statut) -> list[str]:
        return [r.date for r in rows if r.statut is statut]

    console.print()
    notes = [
        (Statut.MZ1_SEUL, "Presents uniquement sur MZ1"),
        (Statut.BACKUP_SEUL, "Presents uniquement sur BACKUP"),
        (Statut.DIFFERENCE, "Ecarts de nombre de fichiers"),
        (Statut.VIDE, "Dossiers vides"),
        (Statut.ERREUR, "Erreurs d'acces"),
    ]
    any_note = False
    for statut, libelle in notes:
        items = dates(statut)
        if items:
            any_note = True
            console.print(
                "  "
                + console.status_label(statut)
                + f" - {libelle} ({len(items)}) : "
                + ", ".join(items)
            )
    if not any_note:
        console.print(console.color("  Aucune anomalie detectee.", _GREEN))


def render_deletion_recap(
    console: Console,
    rows: list[ComparisonRow],
    forced_unsafe: list[ComparisonRow],
) -> None:
    """Affiche le recapitulatif avant confirmation de suppression.

    Args:
        console: Console de sortie.
        rows: Lignes retenues pour suppression.
        forced_unsafe: Sous-ensemble non sur, supprime uniquement via --force.
    """
    console.print()
    console.rule("Recapitulatif de suppression (MZ1)")
    total_files = 0
    total_size = 0
    for row in rows:
        files = row.mz1_count or 0
        total_files += files
        total_size += row.mz1_size
        warn = ""
        if row in forced_unsafe:
            warn = console.color("  [FORCE - non sauvegarde a l'identique]", _RED, bold=True)
        console.print(
            f"  {row.date}  "
            f"{human_number(files):>14} fichiers  "
            f"{human_size(row.mz1_size):>12}  "
            f"{console.status_label(row.statut)}{warn}"
        )
    console.print()
    console.print(
        console.color(
            f"  Total : {len(rows)} dossier(s), "
            f"{human_number(total_files)} fichiers, "
            f"~{human_size(total_size)} a liberer.",
            _BOLD,
        )
    )
    if forced_unsafe:
        console.print(
            console.color(
                f"  Attention : {len(forced_unsafe)} dossier(s) supprime(s) en mode --force "
                "malgre une sauvegarde incomplete.",
                _RED,
                bold=True,
            )
        )


def render_summary(console: Console, summary: RunSummary, elapsed: float, dry_run: bool) -> None:
    """Affiche le resume final d'execution.

    Args:
        console: Console de sortie.
        summary: Compteurs cumules.
        elapsed: Duree totale d'execution en secondes.
        dry_run: True si aucune suppression reelle n'a ete effectuee.
    """
    console.print()
    console.rule("Resume final")
    lines = [
        ("Dossiers analyses", human_number(summary.dirs_scanned)),
        ("Fichiers analyses", human_number(summary.files_counted)),
        ("Dossiers identiques (OK)", human_number(summary.identical)),
        ("Dossiers differents", human_number(summary.different)),
        ("Erreurs d'acces", human_number(summary.errors)),
        ("Dossiers supprimes", human_number(summary.deleted_dirs)),
        ("Espace disque recupere", human_size(summary.freed_bytes)),
        ("Duree totale", human_duration(elapsed)),
    ]
    for label, value in lines:
        console.print(f"  {label:<28} : {console.color(value, _BOLD)}")
    if dry_run:
        console.print()
        console.print(
            console.color(
                "  Mode simulation (dry-run) : aucune suppression reelle effectuee.",
                _YELLOW,
                bold=True,
            )
        )
