#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Permet l'execution du paquet via ``python -m mz_cleanup``."""

from __future__ import annotations

import sys

from .cli import main

if __name__ == "__main__":
    sys.exit(main())
