#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Interface en ligne de commande et orchestration du traitement."""

from __future__ import annotations

import argparse
import signal
import sys
import threading
import time
from pathlib import Path
from typing import Optional

from . import __version__
from .comparator import compare
from .config import AppConfig, ConfigError, DirectoryPair, SSHConfig, load_config
from .display import (
    Console,
    ProgressBar,
    render_comparison_table,
    render_deletion_recap,
    render_summary,
)
from .logging_setup import get_logger, setup_logging
from .models import ComparisonRow, PairResult, RunSummary, Statut
from .remover import Remover
from .scanner import Scanner, ScannerError, build_scanner
from .selector import SelectionError, parse_selection

# Evenement d'arret cooperatif, arme par Ctrl+C.
_STOP = threading.Event()


# --------------------------------------------------------------------------- #
# Arguments
# --------------------------------------------------------------------------- #
def build_parser() -> argparse.ArgumentParser:
    """Construit l'analyseur d'arguments de la ligne de commande."""
    parser = argparse.ArgumentParser(
        prog="mz_cleanup",
        description=(
            "Compare les repertoires de production MZ1 aux sauvegardes BACKUP-MZ "
            "et permet la suppression securisee des donnees MZ1 verifiees."
        ),
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "-c", "--config", required=True,
        help="Chemin du fichier de configuration (format INI : .ini / .cfg).",
    )
    parser.add_argument(
        "--dry-run", dest="dry_run", action="store_true", default=None,
        help="Force le mode simulation (aucune suppression).",
    )
    parser.add_argument(
        "--no-dry-run", dest="dry_run", action="store_false",
        help="Desactive le mode simulation (autorise les suppressions).",
    )
    parser.add_argument(
        "--force", action="store_true", default=None,
        help="Autorise la suppression de dossiers dont la sauvegarde differe.",
    )
    parser.add_argument(
        "--select", metavar="EXPR",
        help=(
            "Selection non interactive (ex. '1-10', '1,5,8', 'ok', 'all'). "
            "Appliquee a chaque couple de repertoires."
        ),
    )
    parser.add_argument(
        "--yes", "-y", action="store_true",
        help="Repond automatiquement 'oui' a la confirmation de suppression.",
    )
    parser.add_argument(
        "--no-delete", action="store_true",
        help="Effectue uniquement le scan et la comparaison, sans phase de suppression.",
    )
    parser.add_argument(
        "--workers", type=int, default=None,
        help="Nombre de threads de comptage (surcharge la configuration).",
    )
    parser.add_argument(
        "--log-level", default=None,
        help="Niveau de log console (DEBUG, INFO, WARNING, ERROR).",
    )
    parser.add_argument(
        "--no-color", action="store_true",
        help="Desactive les couleurs dans la console.",
    )
    parser.add_argument(
        "--version", action="version", version=f"%(prog)s {__version__}",
    )
    return parser


def _apply_overrides(config: AppConfig, args: argparse.Namespace) -> None:
    """Applique les surcharges de la ligne de commande a la configuration."""
    if args.dry_run is not None:
        config.dry_run = args.dry_run
    if args.force:
        config.force = True
    if args.workers is not None:
        config.workers = max(1, args.workers)
    if args.log_level:
        config.logging.console_level = args.log_level.upper()


# --------------------------------------------------------------------------- #
# Orchestration principale
# --------------------------------------------------------------------------- #
class Application:
    """Orchestre le scan, la comparaison et le nettoyage pour tous les couples."""

    def __init__(self, config: AppConfig, args: argparse.Namespace) -> None:
        """Prepare l'application (logger, console, scanners)."""
        self.config = config
        self.args = args
        # Couleurs actives seulement si demandees ET si stderr est un terminal.
        use_color = (not args.no_color) and sys.stderr.isatty()
        self.log = setup_logging(config.logging, use_color=use_color)
        self.console = Console(use_color=None if not args.no_color else False)
        self.summary = RunSummary()
        self._mz1_scanner: Optional[Scanner] = None
        self._backup_scanner: Optional[Scanner] = None

    # -- Cycle de vie ------------------------------------------------------- #
    def _build_scanners(self) -> None:
        """Instancie les scanners MZ1 et BACKUP selon la configuration SSH."""
        self._mz1_scanner = build_scanner(
            self.config.mz1_ssh, self.config.date_pattern, self.config.date_format
        )
        self._backup_scanner = build_scanner(
            self.config.backup_ssh, self.config.date_pattern, self.config.date_format
        )

    def close(self) -> None:
        """Ferme les scanners (connexions SSH)."""
        for scanner in (self._mz1_scanner, self._backup_scanner):
            if scanner is not None:
                scanner.close()

    def run(self) -> int:
        """Execute le traitement complet et retourne un code de sortie.

        Returns:
            0 en cas de succes, 1 en cas d'erreur, 130 si interrompu (Ctrl+C).
        """
        start = time.monotonic()
        self._log_startup()
        try:
            self._build_scanners()
        except ScannerError as exc:
            self.log.error("Initialisation impossible : %s", exc)
            return 1

        try:
            for pair in self.config.pairs:
                if _STOP.is_set():
                    raise KeyboardInterrupt
                self._process_pair(pair)
        except KeyboardInterrupt:
            self.log.warning("Interruption demandee par l'utilisateur (Ctrl+C).")
            self.close()
            elapsed = time.monotonic() - start
            render_summary(self.console, self.summary, elapsed, self.config.dry_run)
            return 130
        finally:
            self.close()

        elapsed = time.monotonic() - start
        render_summary(self.console, self.summary, elapsed, self.config.dry_run)
        self.log.info("Execution terminee en %.2f s.", elapsed)
        return 0

    def _log_startup(self) -> None:
        """Journalise le demarrage et les parametres effectifs."""
        self.log.info("=== Demarrage mz_cleanup v%s ===", __version__)
        self.log.info(
            "Parametres : dry_run=%s force=%s workers=%d couples=%d",
            self.config.dry_run,
            self.config.force,
            self.config.workers,
            len(self.config.pairs),
        )
        self.log.info(
            "MZ1 %s | BACKUP %s",
            "SSH " + self.config.mz1_ssh.host if self.config.mz1_ssh.enabled else "local",
            "SSH " + self.config.backup_ssh.host if self.config.backup_ssh.enabled else "local",
        )

    # -- Traitement d'un couple -------------------------------------------- #
    def _process_pair(self, pair: DirectoryPair) -> None:
        """Scanne, compare, puis (le cas echeant) nettoie un couple de repertoires."""
        assert self._mz1_scanner is not None and self._backup_scanner is not None
        self.log.info("--- Couple '%s' ---", pair.name)

        scan_start = time.monotonic()
        mz1_stats = self._scan_side("MZ1", self._mz1_scanner, pair.mz1)
        backup_stats = self._scan_side("BACKUP", self._backup_scanner, pair.backup)
        scan_elapsed = time.monotonic() - scan_start

        rows = compare(mz1_stats, backup_stats)
        result = PairResult(
            name=pair.name, mz1_dir=pair.mz1, backup_dir=pair.backup, rows=rows
        )
        self._update_summary(rows)
        self.log.info(
            "Scan '%s' termine en %.2f s : %d date(s) comparee(s).",
            pair.name,
            scan_elapsed,
            len(rows),
        )
        render_comparison_table(self.console, result)

        if self.args.no_delete:
            return
        self._cleanup_pair(result)

    def _scan_side(self, label: str, scanner: Scanner, directory: str) -> dict:
        """Scanne un cote (MZ1 ou BACKUP) avec barre de progression."""
        self.log.info("Debut du scan %s : %s", label, directory)
        try:
            date_dirs = scanner.list_date_dirs(directory)
        except ScannerError as exc:
            self.log.error("Scan %s impossible (%s) : %s", label, directory, exc)
            return {}
        except OSError as exc:
            self.log.error("Repertoire %s inaccessible (%s) : %s", label, directory, exc)
            return {}

        if not date_dirs:
            self.log.warning("Aucun dossier date trouve dans %s (%s).", label, directory)
            return {}

        bar = ProgressBar(len(date_dirs), f"Scan {label:<7}", self.console.use_color)
        stats = scanner.scan_parent(
            directory,
            workers=self.config.workers,
            stop_event=_STOP,
            progress=lambda name: bar.update(name),
        )
        bar.close()
        return stats

    def _update_summary(self, rows: list[ComparisonRow]) -> None:
        """Met a jour les compteurs cumules a partir des lignes comparees."""
        for row in rows:
            for stat in (row.mz1, row.backup):
                if stat is not None:
                    self.summary.dirs_scanned += 1
                    self.summary.files_counted += stat.file_count
            if row.statut is Statut.OK:
                self.summary.identical += 1
            elif row.statut is Statut.ERREUR:
                self.summary.errors += 1
            elif row.statut in (Statut.DIFFERENCE, Statut.MZ1_SEUL, Statut.BACKUP_SEUL):
                self.summary.different += 1

    # -- Nettoyage --------------------------------------------------------- #
    def _cleanup_pair(self, result: PairResult) -> None:
        """Selection, confirmation et suppression pour un couple."""
        candidates = [row for row in result.rows if row.is_deletable_candidate]
        if not candidates:
            self.log.info("Aucun dossier MZ1 candidat au nettoyage pour '%s'.", result.name)
            return

        selection = self._get_selection(candidates)
        if not selection:
            self.log.info("Aucun dossier selectionne pour '%s'.", result.name)
            return

        selected_rows = [candidates[i] for i in selection]
        self.log.info(
            "Dossiers selectionnes pour '%s' : %s",
            result.name,
            ", ".join(r.date for r in selected_rows),
        )

        forced_unsafe = [r for r in selected_rows if not r.is_safe_to_delete]
        if forced_unsafe and not self.config.force:
            # Sans --force, on ne retient que les dossiers surs.
            blocked = ", ".join(r.date for r in forced_unsafe)
            self.log.warning(
                "Ignores (sauvegarde non conforme, --force absent) : %s", blocked
            )
            selected_rows = [r for r in selected_rows if r.is_safe_to_delete]
            forced_unsafe = []
            if not selected_rows:
                self.log.info("Plus aucun dossier sur a supprimer pour '%s'.", result.name)
                return

        render_deletion_recap(self.console, selected_rows, forced_unsafe)
        if not self._confirm():
            self.log.info("Suppression annulee par l'utilisateur pour '%s'.", result.name)
            return

        self.log.info("Confirmation utilisateur : OUI pour '%s'.", result.name)
        self._perform_deletion(selected_rows)

    def _get_selection(self, candidates: list[ComparisonRow]) -> list[int]:
        """Obtient la selection, en mode interactif ou via ``--select``."""
        if self.args.select:
            try:
                indices = parse_selection(self.args.select, candidates)
                self.log.info(
                    "Selection non interactive '%s' -> %d dossier(s).",
                    self.args.select,
                    len(indices),
                )
                return indices
            except SelectionError as exc:
                self.log.error("Expression de selection invalide : %s", exc)
                return []
        return self._prompt_selection(candidates)

    def _prompt_selection(self, candidates: list[ComparisonRow]) -> list[int]:
        """Demande interactivement la selection des dossiers a supprimer."""
        if not sys.stdin.isatty():
            self.log.warning(
                "Entree non interactive : aucune selection (utilisez --select)."
            )
            return []
        self.console.print()
        self.console.print(
            "Selection des dossiers a supprimer sur MZ1 "
            "(ex. '1-10', '1,5,8', 'ok', 'all', ou vide pour ignorer) :"
        )
        try:
            raw = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            self.console.print()
            return []
        if not raw:
            return []
        try:
            return parse_selection(raw, candidates)
        except SelectionError as exc:
            self.console.print(f"Selection invalide : {exc}")
            return self._prompt_selection(candidates)

    def _confirm(self) -> bool:
        """Demande une confirmation explicite avant suppression."""
        if self.args.yes:
            self.log.info("Confirmation automatique activee (--yes).")
            return True
        if not sys.stdin.isatty():
            self.log.warning("Entree non interactive sans --yes : suppression annulee.")
            return False
        try:
            answer = input("Voulez-vous vraiment supprimer ces dossiers ? (oui/non) ")
        except (EOFError, KeyboardInterrupt):
            self.console.print()
            return False
        return answer.strip().lower() in ("oui", "o", "yes", "y")

    def _perform_deletion(self, rows: list[ComparisonRow]) -> None:
        """Execute la suppression et met a jour le resume."""
        assert self._mz1_scanner is not None
        remover = Remover(self._mz1_scanner, self.config.dry_run, self.config.force)
        outcomes = remover.delete(rows)
        for outcome in outcomes:
            if outcome.deleted:
                self.summary.deleted_dirs += 1
                self.summary.freed_bytes += outcome.freed_bytes
            elif self.config.dry_run and outcome.skipped_reason == "dry-run":
                # En simulation, on comptabilise l'espace theorique libere.
                self.summary.freed_bytes += outcome.freed_bytes


# --------------------------------------------------------------------------- #
# Point d'entree
# --------------------------------------------------------------------------- #
def _install_signal_handler() -> None:
    """Installe le gestionnaire de Ctrl+C (SIGINT) pour un arret propre."""

    def handler(signum, frame):  # type: ignore[no-untyped-def]
        _STOP.set()
        get_logger().warning("Signal d'interruption recu, arret en cours...")

    signal.signal(signal.SIGINT, handler)


def main(argv: Optional[list[str]] = None) -> int:
    """Point d'entree principal de l'outil.

    Args:
        argv: Arguments de ligne de commande (par defaut ``sys.argv``).

    Returns:
        Le code de sortie du processus.
    """
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        config = load_config(args.config)
    except ConfigError as exc:
        print(f"Erreur de configuration : {exc}", file=sys.stderr)
        return 2

    _apply_overrides(config, args)
    _install_signal_handler()

    app = Application(config, args)
    try:
        return app.run()
    except KeyboardInterrupt:
        return 130
    except Exception as exc:  # filet de securite global
        get_logger().exception("Erreur inattendue : %s", exc)
        return 1


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
