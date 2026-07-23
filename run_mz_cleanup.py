#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Script de lancement de l'outil de comparaison/nettoyage des repertoires MZ.

Point d'entree pratique equivalent a ``python -m mz_cleanup`` :

    python run_mz_cleanup.py --config config.mz_cleanup.yaml
"""

from __future__ import annotations

import sys

from mz_cleanup.cli import main

if __name__ == "__main__":
    sys.exit(main())
