#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Scan des repertoires MZ.

Deux implementations sont fournies derriere l'interface abstraite ``Scanner`` :

    * ``LocalScanner``  : parcourt le systeme de fichiers local avec
      ``os.scandir()`` (comptage recursif sans construire de listes en memoire).
    * ``RemoteScanner`` : execute des commandes ``find`` via SSH (paramiko) sur
      un serveur distant.

Les deux exposent :
    * ``list_date_dirs(parent)``  -> liste des sous-repertoires dates ;
    * ``count_dir(path)``         -> (nb_fichiers, taille_octets, erreur).

Le comptage effectif est orchestre par ``scan_parent`` qui parallelise les
appels ``count_dir`` via un pool de threads et notifie l'avancement.
"""

from __future__ import annotations

import os
import re
import shlex
import threading
from abc import ABC, abstractmethod
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from typing import Callable, Optional

from .config import SSHConfig
from .logging_setup import get_logger
from .models import DirStat

ProgressCallback = Callable[[str], None]


class ScannerError(Exception):
    """Erreur non recuperable lors d'un scan (connexion SSH, etc.)."""


# --------------------------------------------------------------------------- #
# Interface abstraite
# --------------------------------------------------------------------------- #
class Scanner(ABC):
    """Interface commune aux scanners locaux et distants."""

    def __init__(self, date_pattern: str, date_format: str) -> None:
        """Initialise le scanner.

        Args:
            date_pattern: Expression reguliere identifiant un dossier date.
            date_format: Format ``strptime`` pour valider la date (ou "").
        """
        self._date_re = re.compile(f"^{date_pattern}$")
        self._date_format = date_format
        self._log = get_logger()

    # -- Detection de date -------------------------------------------------- #
    def is_date_dir(self, name: str) -> bool:
        """Retourne True si ``name`` correspond a un dossier date valide."""
        if not self._date_re.match(name):
            return False
        if self._date_format:
            try:
                datetime.strptime(name, self._date_format)
            except ValueError:
                return False
        return True

    # -- Methodes a implementer -------------------------------------------- #
    @abstractmethod
    def list_date_dirs(self, parent: str) -> list[tuple[str, str]]:
        """Liste les sous-repertoires dates de ``parent``.

        Returns:
            Une liste de tuples ``(nom_date, chemin_complet)`` triee par nom.
        """

    @abstractmethod
    def count_dir(self, path: str) -> tuple[int, int, Optional[str]]:
        """Compte les fichiers d'un dossier.

        Returns:
            Un tuple ``(nombre_fichiers, taille_totale_octets, erreur)`` ou
            ``erreur`` est None en cas de succes.
        """

    def close(self) -> None:
        """Libere les ressources (connexions distantes). Sans effet en local."""

    # -- Orchestration ------------------------------------------------------ #
    def scan_parent(
        self,
        parent: str,
        workers: int,
        stop_event: Optional[threading.Event] = None,
        progress: Optional[ProgressCallback] = None,
    ) -> dict[str, DirStat]:
        """Scanne un repertoire parent et retourne les stats par date.

        Le comptage de chaque dossier est parallelise via un pool de threads.
        Une erreur sur un dossier n'interrompt pas les autres.

        Args:
            parent: Chemin du repertoire parent a analyser.
            workers: Nombre de threads de comptage.
            stop_event: Evenement d'arret cooperatif (Ctrl+C).
            progress: Callback appele avec le nom du dossier apres son comptage.

        Returns:
            Un dictionnaire ``{date: DirStat}``.
        """
        results: dict[str, DirStat] = {}
        try:
            date_dirs = self.list_date_dirs(parent)
        except ScannerError:
            raise
        except Exception as exc:  # parent illisible : on le signale sans crasher
            self._log.error("Impossible de lister %s : %s", parent, exc)
            return results

        self._log.debug("%s : %d dossier(s) date detecte(s).", parent, len(date_dirs))

        with ThreadPoolExecutor(max_workers=max(1, workers)) as executor:
            futures = {
                executor.submit(self._safe_count, name, path): name
                for name, path in date_dirs
            }
            for future in as_completed(futures):
                if stop_event is not None and stop_event.is_set():
                    executor.shutdown(wait=False, cancel_futures=True)
                    raise KeyboardInterrupt
                stat = future.result()
                results[stat.name] = stat
                if progress is not None:
                    progress(stat.name)
        return results

    def _safe_count(self, name: str, path: str) -> DirStat:
        """Compte un dossier en capturant toute exception dans ``DirStat.error``."""
        try:
            count, size, error = self.count_dir(path)
            if error:
                self._log.warning("Acces impossible a %s : %s", path, error)
            return DirStat(name=name, path=path, file_count=count, total_size=size, error=error)
        except Exception as exc:  # filet de securite
            self._log.warning("Erreur lors du comptage de %s : %s", path, exc)
            return DirStat(name=name, path=path, error=str(exc))


# --------------------------------------------------------------------------- #
# Scanner local
# --------------------------------------------------------------------------- #
class LocalScanner(Scanner):
    """Scanner utilisant ``os.scandir()`` sur le systeme de fichiers local."""

    def list_date_dirs(self, parent: str) -> list[tuple[str, str]]:
        """Liste les sous-repertoires dates locaux via ``os.scandir``."""
        found: list[tuple[str, str]] = []
        with os.scandir(parent) as iterator:
            for entry in iterator:
                try:
                    if entry.is_dir(follow_symlinks=False) and self.is_date_dir(entry.name):
                        found.append((entry.name, entry.path))
                except OSError as exc:
                    self._log.warning("Entree illisible dans %s : %s", parent, exc)
        found.sort(key=lambda item: item[0])
        return found

    def count_dir(self, path: str) -> tuple[int, int, Optional[str]]:
        """Compte recursivement les fichiers d'un dossier local.

        Le parcours utilise ``os.scandir`` en profondeur sans jamais construire
        de liste de noms, afin de rester econome en memoire meme pour plusieurs
        millions de fichiers.
        """
        count = 0
        size = 0
        errors: list[str] = []
        stack = [path]
        while stack:
            current = stack.pop()
            try:
                with os.scandir(current) as iterator:
                    for entry in iterator:
                        try:
                            if entry.is_dir(follow_symlinks=False):
                                stack.append(entry.path)
                            elif entry.is_file(follow_symlinks=False):
                                count += 1
                                try:
                                    size += entry.stat(follow_symlinks=False).st_size
                                except OSError:
                                    pass  # taille indisponible : on ignore
                        except OSError as exc:
                            errors.append(str(exc))
            except OSError as exc:
                errors.append(str(exc))
        error = "; ".join(dict.fromkeys(errors)) if errors else None
        return count, size, error

    def delete_dir(self, path: str) -> int:
        """Supprime recursivement un dossier local et retourne l'espace libere.

        Note:
            La taille est mesuree avant suppression ; en cas d'echec partiel une
            exception est propagee a l'appelant.
        """
        import shutil

        _, size, _ = self.count_dir(path)
        shutil.rmtree(path)
        return size


# --------------------------------------------------------------------------- #
# Scanner distant (SSH)
# --------------------------------------------------------------------------- #
class RemoteScanner(Scanner):
    """Scanner executant des commandes ``find`` via SSH (paramiko)."""

    def __init__(self, ssh: SSHConfig, date_pattern: str, date_format: str) -> None:
        """Ouvre la connexion SSH.

        Raises:
            ScannerError: Si paramiko est absent ou la connexion echoue.
        """
        super().__init__(date_pattern, date_format)
        self._ssh_config = ssh
        self._lock = threading.Lock()
        try:
            import paramiko  # type: ignore
        except ImportError as exc:  # pragma: no cover - depend de l'environnement
            raise ScannerError(
                "Le mode SSH necessite le paquet 'paramiko' (pip install paramiko)."
            ) from exc
        self._paramiko = paramiko
        self._client = self._connect()

    def _connect(self):  # type: ignore[no-untyped-def]
        """Etablit la connexion SSH avec les parametres de configuration."""
        client = self._paramiko.SSHClient()
        client.set_missing_host_key_policy(self._paramiko.AutoAddPolicy())
        try:
            client.connect(
                hostname=self._ssh_config.host,
                port=self._ssh_config.port,
                username=self._ssh_config.user,
                password=self._ssh_config.password,
                key_filename=self._ssh_config.key_file,
                timeout=self._ssh_config.timeout,
                allow_agent=True,
                look_for_keys=True,
            )
        except Exception as exc:
            raise ScannerError(
                f"Connexion SSH impossible vers {self._ssh_config.user}@"
                f"{self._ssh_config.host}:{self._ssh_config.port} : {exc}"
            ) from exc
        self._log.info(
            "Connexion SSH etablie : %s@%s", self._ssh_config.user, self._ssh_config.host
        )
        return client

    def _run(self, command: str) -> tuple[int, str, str]:
        """Execute une commande distante et retourne (code, stdout, stderr).

        Les canaux SSH ne sont pas surs vis-a-vis des threads sur un meme
        transport ; un verrou serialise donc les executions.
        """
        with self._lock:
            _, stdout, stderr = self._client.exec_command(command, timeout=None)
            out = stdout.read().decode("utf-8", "replace")
            err = stderr.read().decode("utf-8", "replace")
            code = stdout.channel.recv_exit_status()
        return code, out, err

    def list_date_dirs(self, parent: str) -> list[tuple[str, str]]:
        """Liste les sous-repertoires immediats du parent distant."""
        quoted = shlex.quote(parent)
        # -mindepth/-maxdepth 1 : uniquement les enfants directs.
        command = f"find {quoted} -mindepth 1 -maxdepth 1 -type d -printf '%f\\n'"
        code, out, err = self._run(command)
        if code != 0 and not out:
            raise ScannerError(f"find a echoue sur {parent} : {err.strip() or code}")
        found: list[tuple[str, str]] = []
        base = parent.rstrip("/")
        for name in out.splitlines():
            name = name.strip()
            if name and self.is_date_dir(name):
                found.append((name, f"{base}/{name}"))
        found.sort(key=lambda item: item[0])
        return found

    def count_dir(self, path: str) -> tuple[int, int, Optional[str]]:
        """Compte fichiers et octets d'un dossier distant via ``find``.

        Une seule commande ``find ... -printf '%s\\n' | awk`` fournit le nombre
        de fichiers et la taille cumulee en un seul aller-retour.
        """
        quoted = shlex.quote(path)
        command = (
            f"find {quoted} -type f -printf '%s\\n' 2>/dev/null | "
            "awk '{c++; t+=$1} END {print (c+0)\" \"(t+0)}'"
        )
        code, out, err = self._run(command)
        out = out.strip()
        if not out:
            # find echoue completement (dossier inaccessible)
            return 0, 0, err.strip() or f"code de sortie {code}"
        try:
            count_str, size_str = out.split()
            return int(count_str), int(size_str), None
        except ValueError:
            return 0, 0, f"sortie inattendue: {out!r}"

    def delete_dir(self, path: str) -> int:
        """Supprime un dossier distant (``rm -rf``) et retourne l'espace libere."""
        _, size, _ = self.count_dir(path)
        quoted = shlex.quote(path)
        code, _, err = self._run(f"rm -rf {quoted}")
        if code != 0:
            raise ScannerError(f"rm -rf a echoue sur {path} : {err.strip() or code}")
        return size

    def close(self) -> None:
        """Ferme la connexion SSH."""
        try:
            self._client.close()
        except Exception:  # pragma: no cover - fermeture best-effort
            pass


# --------------------------------------------------------------------------- #
# Fabrique
# --------------------------------------------------------------------------- #
def build_scanner(ssh: SSHConfig, date_pattern: str, date_format: str) -> Scanner:
    """Construit le scanner approprie selon la configuration SSH.

    Args:
        ssh: Configuration SSH du serveur (``enabled`` decide local/distant).
        date_pattern: Motif de detection des dossiers dates.
        date_format: Format de validation de la date.

    Returns:
        Un ``RemoteScanner`` si SSH est active, sinon un ``LocalScanner``.
    """
    if ssh.enabled:
        return RemoteScanner(ssh, date_pattern, date_format)
    return LocalScanner(date_pattern, date_format)
