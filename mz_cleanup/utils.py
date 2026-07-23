#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Fonctions utilitaires transverses (formatage, temps, chaines)."""

from __future__ import annotations

from datetime import timedelta


def human_size(num_bytes: int) -> str:
    """Convertit un nombre d'octets en chaine lisible (Kio, Mio, Gio...).

    Args:
        num_bytes: Taille en octets.

    Returns:
        Une representation binaire (base 1024) telle que ``"1.5 Gio"``.
    """
    if num_bytes < 0:
        return f"-{human_size(-num_bytes)}"
    unites = ["o", "Kio", "Mio", "Gio", "Tio", "Pio", "Eio"]
    taille = float(num_bytes)
    for unite in unites:
        if taille < 1024.0 or unite == unites[-1]:
            if unite == "o":
                return f"{int(taille)} {unite}"
            return f"{taille:.2f} {unite}"
        taille /= 1024.0
    return f"{num_bytes} o"  # pragma: no cover (inatteignable)


def human_number(value: int) -> str:
    """Formate un entier avec des espaces comme separateurs de milliers.

    Args:
        value: L'entier a formater.

    Returns:
        Par exemple ``"1 234 567"``.
    """
    return f"{value:,}".replace(",", " ")


def human_duration(seconds: float) -> str:
    """Formate une duree en secondes sous forme lisible ``HH:MM:SS``.

    Args:
        seconds: Duree en secondes.

    Returns:
        Une chaine telle que ``"0:01:23"`` ou ``"1.23 s"`` pour les durees
        inferieures a la minute.
    """
    if seconds < 60:
        return f"{seconds:.2f} s"
    return str(timedelta(seconds=int(seconds)))
