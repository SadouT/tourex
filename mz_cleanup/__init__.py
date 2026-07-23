#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Outil de comparaison et de nettoyage des repertoires MZ.

Ce paquet fournit un outil en ligne de commande destine a etre execute sur le
serveur *Billing_SIFAC*. Il compare les repertoires de production du serveur
*MZ1* avec les repertoires de sauvegarde du serveur *BACKUP-MZ*, puis permet de
supprimer de maniere securisee les donnees de MZ1 une fois la sauvegarde
verifiee.

Modules principaux :
    config          Chargement et validation de la configuration (YAML/JSON/INI).
    models          Structures de donnees (statistiques, lignes de comparaison).
    logging_setup   Configuration de la journalisation (fichier + console).
    scanner         Scan des repertoires (local via os.scandir, distant via SSH).
    comparator      Comparaison des deux serveurs.
    selector        Analyse des expressions de selection (plages, listes, OK).
    display         Affichage terminal (tableaux, barre de progression, couleurs).
    remover         Suppression securisee des repertoires selectionnes.
    cli             Orchestration et interface en ligne de commande.
"""

__version__ = "1.0.0"
__all__ = ["__version__"]
