#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Configuration de la journalisation (fichier + console)."""

from __future__ import annotations

import logging
import sys
from pathlib import Path

from .config import LoggingConfig

LOGGER_NAME = "mz_cleanup"

# Codes couleur ANSI par niveau, appliques uniquement sur la console.
_LEVEL_COLORS = {
    logging.DEBUG: "\033[90m",     # gris
    logging.INFO: "\033[0m",       # normal
    logging.WARNING: "\033[33m",   # jaune
    logging.ERROR: "\033[31m",     # rouge
    logging.CRITICAL: "\033[1;31m",  # rouge gras
}
_RESET = "\033[0m"


class _ColorFormatter(logging.Formatter):
    """Formateur console qui colore le niveau selon sa severite."""

    def __init__(self, fmt: str, datefmt: str, use_color: bool) -> None:
        super().__init__(fmt=fmt, datefmt=datefmt)
        self.use_color = use_color

    def format(self, record: logging.LogRecord) -> str:  # noqa: A003
        message = super().format(record)
        if self.use_color:
            color = _LEVEL_COLORS.get(record.levelno, _RESET)
            return f"{color}{message}{_RESET}"
        return message


def setup_logging(config: LoggingConfig, use_color: bool = True) -> logging.Logger:
    """Configure et retourne le logger applicatif.

    Deux handlers sont installes :
        * un handler fichier (niveau ``config.level``, horodate) ;
        * un handler console sur ``stderr`` (niveau ``config.console_level``).

    Args:
        config: Parametres de journalisation.
        use_color: Active la coloration des niveaux dans la console.

    Returns:
        Le logger nomme ``mz_cleanup``, pret a l'emploi.
    """
    logger = logging.getLogger(LOGGER_NAME)
    logger.setLevel(logging.DEBUG)
    logger.handlers.clear()  # evite les doublons si appele plusieurs fois
    logger.propagate = False

    date_fmt = "%Y-%m-%d %H:%M:%S"

    # Handler fichier ---------------------------------------------------------
    try:
        log_path = Path(config.file).expanduser()
        if log_path.parent and not log_path.parent.exists():
            log_path.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_path, encoding="utf-8")
        file_handler.setLevel(_level(config.level, logging.DEBUG))
        file_handler.setFormatter(
            logging.Formatter(
                "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
                datefmt=date_fmt,
            )
        )
        logger.addHandler(file_handler)
    except OSError as exc:
        # On continue meme si le fichier de log n'est pas accessible.
        print(f"Avertissement : fichier de log indisponible ({exc}).", file=sys.stderr)

    # Handler console ---------------------------------------------------------
    console_handler = logging.StreamHandler(stream=sys.stderr)
    console_handler.setLevel(_level(config.console_level, logging.INFO))
    console_handler.setFormatter(
        _ColorFormatter(
            "%(asctime)s | %(levelname)-8s | %(message)s",
            datefmt=date_fmt,
            use_color=use_color,
        )
    )
    logger.addHandler(console_handler)

    return logger


def _level(name: str, default: int) -> int:
    """Convertit un nom de niveau ('INFO', ...) en constante logging."""
    value = getattr(logging, str(name).upper(), None)
    return value if isinstance(value, int) else default


def get_logger() -> logging.Logger:
    """Retourne le logger applicatif (deja configure par ``setup_logging``)."""
    return logging.getLogger(LOGGER_NAME)
