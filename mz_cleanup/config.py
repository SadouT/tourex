#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Chargement et validation de la configuration.

Trois formats sont supportes :
    * YAML  (necessite le paquet ``PyYAML``) ;
    * JSON  (bibliotheque standard) ;
    * INI   (bibliotheque standard ``configparser``).

Le format est deduit de l'extension du fichier (``.yaml`` / ``.yml``,
``.json``, ``.ini`` / ``.cfg``).
"""

from __future__ import annotations

import configparser
import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional


class ConfigError(Exception):
    """Erreur de configuration (fichier introuvable, champ manquant, etc.)."""


@dataclass(slots=True)
class SSHConfig:
    """Parametres de connexion SSH vers un serveur distant.

    Si ``enabled`` est False, le serveur est considere comme local et les
    chemins sont lus directement sur la machine executant le script.
    """

    enabled: bool = False
    host: str = ""
    port: int = 22
    user: str = ""
    password: Optional[str] = None
    key_file: Optional[str] = None
    timeout: float = 30.0

    @classmethod
    def from_dict(cls, data: Optional[dict[str, Any]]) -> "SSHConfig":
        """Construit une SSHConfig depuis un dictionnaire (potentiellement vide)."""
        if not data:
            return cls()
        key_file = data.get("key_file")
        if key_file:
            key_file = os.path.expanduser(str(key_file))
        return cls(
            enabled=bool(data.get("enabled", False)),
            host=str(data.get("host", "")),
            port=int(data.get("port", 22)),
            user=str(data.get("user", "")),
            password=data.get("password"),
            key_file=key_file,
            timeout=float(data.get("timeout", 30.0)),
        )

    def validate(self, label: str) -> None:
        """Verifie la coherence des parametres SSH lorsqu'ils sont actives."""
        if not self.enabled:
            return
        if not self.host:
            raise ConfigError(f"[{label}] ssh.host est requis lorsque ssh.enabled est vrai.")
        if not self.user:
            raise ConfigError(f"[{label}] ssh.user est requis lorsque ssh.enabled est vrai.")
        if self.key_file and not Path(self.key_file).is_file():
            raise ConfigError(f"[{label}] cle SSH introuvable : {self.key_file}")


@dataclass(slots=True)
class LoggingConfig:
    """Parametres de journalisation."""

    level: str = "DEBUG"          # niveau du fichier de log
    console_level: str = "INFO"   # niveau affiche dans la console
    file: str = "mz_cleanup.log"

    @classmethod
    def from_dict(cls, data: Optional[dict[str, Any]]) -> "LoggingConfig":
        """Construit une LoggingConfig depuis un dictionnaire."""
        if not data:
            return cls()
        return cls(
            level=str(data.get("level", "DEBUG")).upper(),
            console_level=str(data.get("console_level", "INFO")).upper(),
            file=str(data.get("file", "mz_cleanup.log")),
        )


@dataclass(slots=True)
class DirectoryPair:
    """Couple de repertoires a comparer (production MZ1 <-> sauvegarde BACKUP)."""

    name: str
    mz1: str
    backup: str

    @classmethod
    def from_dict(cls, data: dict[str, Any], index: int) -> "DirectoryPair":
        """Construit un DirectoryPair depuis un dictionnaire de configuration."""
        try:
            mz1 = str(data["mz1"])
            backup = str(data["backup"])
        except KeyError as exc:  # champ manquant
            raise ConfigError(
                f"pairs[{index}] : champ obligatoire manquant {exc}."
            ) from exc
        name = str(data.get("name") or f"pair-{index + 1}")
        return cls(name=name, mz1=mz1, backup=backup)


@dataclass(slots=True)
class AppConfig:
    """Configuration complete de l'application."""

    pairs: list[DirectoryPair]
    mz1_ssh: SSHConfig = field(default_factory=SSHConfig)
    backup_ssh: SSHConfig = field(default_factory=SSHConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    dry_run: bool = True
    force: bool = False
    workers: int = 8
    date_pattern: str = r"\d{8}"
    date_format: str = "%Y%m%d"

    def validate(self) -> None:
        """Valide l'ensemble de la configuration ou leve ``ConfigError``."""
        if not self.pairs:
            raise ConfigError("Aucun couple de repertoires defini (section 'pairs').")
        if self.workers < 1:
            raise ConfigError("Le nombre de 'workers' doit etre >= 1.")
        self.mz1_ssh.validate("mz1")
        self.backup_ssh.validate("backup")


# --------------------------------------------------------------------------- #
# Lecture des differents formats de fichier
# --------------------------------------------------------------------------- #
def _load_yaml(path: Path) -> dict[str, Any]:
    """Charge un fichier YAML (necessite PyYAML)."""
    try:
        import yaml  # type: ignore
    except ImportError as exc:  # pragma: no cover - depend de l'environnement
        raise ConfigError(
            "Le format YAML necessite le paquet 'PyYAML' (pip install pyyaml). "
            "Vous pouvez aussi fournir une configuration JSON ou INI."
        ) from exc
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle)
    if not isinstance(data, dict):
        raise ConfigError("Le fichier YAML doit contenir un objet a la racine.")
    return data


def _load_json(path: Path) -> dict[str, Any]:
    """Charge un fichier JSON."""
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ConfigError("Le fichier JSON doit contenir un objet a la racine.")
    return data


def _load_ini(path: Path) -> dict[str, Any]:
    """Charge un fichier INI et le convertit vers la structure attendue.

    Convention INI :
        [general]  dry_run, force, workers, date_pattern, date_format
        [logging]  level, console_level, file
        [ssh:mz1]  enabled, host, port, user, password, key_file
        [ssh:backup] idem
        [pair:NOM] mz1 = ..., backup = ...
    """
    # interpolation=None : les valeurs comme date_format='%Y%m%d' contiennent
    # des '%' qui ne doivent pas etre interpretes par configparser.
    parser = configparser.ConfigParser(interpolation=None)
    parser.optionxform = str  # conserve la casse des cles
    if not parser.read(path, encoding="utf-8"):
        raise ConfigError(f"Impossible de lire le fichier INI : {path}")

    def as_bool(section: str, option: str, default: bool) -> bool:
        if parser.has_option(section, option):
            return parser.getboolean(section, option)
        return default

    data: dict[str, Any] = {}
    if parser.has_section("general"):
        gen = parser["general"]
        data.update(
            {
                "dry_run": as_bool("general", "dry_run", True),
                "force": as_bool("general", "force", False),
                "workers": int(gen.get("workers", "8")),
                "date_pattern": gen.get("date_pattern", r"\d{8}"),
                "date_format": gen.get("date_format", "%Y%m%d"),
            }
        )
    if parser.has_section("logging"):
        log = parser["logging"]
        data["logging"] = {
            "level": log.get("level", "DEBUG"),
            "console_level": log.get("console_level", "INFO"),
            "file": log.get("file", "mz_cleanup.log"),
        }

    for role in ("mz1", "backup"):
        section = f"ssh:{role}"
        if parser.has_section(section):
            sec = parser[section]
            data[f"{role}_ssh"] = {
                "enabled": as_bool(section, "enabled", False),
                "host": sec.get("host", ""),
                "port": int(sec.get("port", "22")),
                "user": sec.get("user", ""),
                "password": sec.get("password") or None,
                "key_file": sec.get("key_file") or None,
                "timeout": float(sec.get("timeout", "30")),
            }

    pairs: list[dict[str, Any]] = []
    for section in parser.sections():
        if section.startswith("pair:"):
            sec = parser[section]
            pairs.append(
                {
                    "name": section.split(":", 1)[1],
                    "mz1": sec.get("mz1", ""),
                    "backup": sec.get("backup", ""),
                }
            )
    data["pairs"] = pairs
    return data


def _from_dict(data: dict[str, Any]) -> AppConfig:
    """Convertit un dictionnaire brut en ``AppConfig``."""
    raw_pairs = data.get("pairs") or []
    if not isinstance(raw_pairs, list):
        raise ConfigError("La section 'pairs' doit etre une liste.")
    pairs = [DirectoryPair.from_dict(p, i) for i, p in enumerate(raw_pairs)]

    return AppConfig(
        pairs=pairs,
        mz1_ssh=SSHConfig.from_dict(data.get("mz1_ssh") or (data.get("mz1") or {}).get("ssh")),
        backup_ssh=SSHConfig.from_dict(
            data.get("backup_ssh") or (data.get("backup") or {}).get("ssh")
        ),
        logging=LoggingConfig.from_dict(data.get("logging")),
        dry_run=bool(data.get("dry_run", True)),
        force=bool(data.get("force", False)),
        workers=int(data.get("workers", 8)),
        date_pattern=str(data.get("date_pattern", r"\d{8}")),
        date_format=str(data.get("date_format", "%Y%m%d")),
    )


def load_config(path: str | os.PathLike[str]) -> AppConfig:
    """Charge et valide la configuration depuis un fichier.

    Args:
        path: Chemin du fichier de configuration (YAML, JSON ou INI).

    Returns:
        L'objet ``AppConfig`` valide.

    Raises:
        ConfigError: Si le fichier est introuvable, illisible ou invalide.
    """
    config_path = Path(path).expanduser()
    if not config_path.is_file():
        raise ConfigError(f"Fichier de configuration introuvable : {config_path}")

    suffix = config_path.suffix.lower()
    try:
        if suffix in (".yaml", ".yml"):
            data = _load_yaml(config_path)
        elif suffix == ".json":
            data = _load_json(config_path)
        elif suffix in (".ini", ".cfg"):
            data = _load_ini(config_path)
        else:
            raise ConfigError(
                f"Extension de configuration non supportee : '{suffix}'. "
                "Utilisez .yaml, .json ou .ini."
            )
    except ConfigError:
        raise
    except Exception as exc:  # erreurs de parsing (yaml/json/ini)
        raise ConfigError(f"Erreur de lecture de {config_path} : {exc}") from exc

    config = _from_dict(data)
    config.validate()
    return config
