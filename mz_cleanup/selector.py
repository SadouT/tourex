#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Analyse des expressions de selection de dossiers.

Les expressions supportees (combinables par des virgules) :
    * un numero          : ``5`` ;
    * une plage          : ``1-10`` ;
    * une liste          : ``1,5,8,12`` ;
    * mot-cle ``ok``     : tous les dossiers au statut OK ;
    * mot-cle ``all`` / ``tout`` : tous les candidats.

Les numeros sont bases sur 1 et se referent a l'ordre du tableau affiche.
"""

from __future__ import annotations

from .models import ComparisonRow, Statut


class SelectionError(ValueError):
    """Expression de selection invalide."""


def parse_selection(expression: str, rows: list[ComparisonRow]) -> list[int]:
    """Convertit une expression de selection en indices (bases sur 0).

    Args:
        expression: L'expression saisie par l'utilisateur.
        rows: Les lignes candidates affichees (dans l'ordre du tableau).

    Returns:
        La liste triee, sans doublon, des indices selectionnes (bases sur 0).

    Raises:
        SelectionError: Si l'expression est vide ou contient un jeton invalide.
    """
    if expression is None:
        raise SelectionError("Expression de selection vide.")
    text = expression.strip().lower()
    if not text:
        raise SelectionError("Expression de selection vide.")

    count = len(rows)
    selected: set[int] = set()

    for token in _split_tokens(text):
        if token in ("all", "tout", "tous"):
            selected.update(range(count))
        elif token in ("ok", "auto"):
            selected.update(i for i, row in enumerate(rows) if row.statut is Statut.OK)
        elif "-" in token:
            selected.update(_parse_range(token, count))
        else:
            selected.add(_parse_index(token, count))

    return sorted(selected)


def _split_tokens(text: str) -> list[str]:
    """Decoupe l'expression sur les virgules et espaces, en ignorant le vide."""
    tokens: list[str] = []
    for chunk in text.replace(" ", ",").split(","):
        chunk = chunk.strip()
        if chunk:
            tokens.append(chunk)
    if not tokens:
        raise SelectionError("Expression de selection vide.")
    return tokens


def _parse_index(token: str, count: int) -> int:
    """Analyse un numero unique base sur 1 et retourne l'indice base sur 0."""
    try:
        number = int(token)
    except ValueError as exc:
        raise SelectionError(f"Jeton invalide : '{token}'.") from exc
    if not 1 <= number <= count:
        raise SelectionError(f"Numero hors limites : {number} (1-{count}).")
    return number - 1


def _parse_range(token: str, count: int) -> list[int]:
    """Analyse une plage ``debut-fin`` (bornes incluses)."""
    parts = token.split("-")
    if len(parts) != 2 or not parts[0] or not parts[1]:
        raise SelectionError(f"Plage invalide : '{token}'.")
    start = _parse_index(parts[0], count)
    end = _parse_index(parts[1], count)
    if start > end:
        start, end = end, start
    return list(range(start, end + 1))
