# mz_cleanup — Comparaison et nettoyage des repertoires MZ

Outil en ligne de commande destine a etre execute sur le serveur **Billing_SIFAC**.
Il compare les repertoires de production du serveur **MZ1** avec les repertoires
de sauvegarde du serveur **BACKUP-MZ**, puis permet de supprimer de maniere
securisee les donnees de MZ1 **uniquement lorsque la sauvegarde est verifiee**.

```
        MZ1  (production)                 BACKUP-MZ  (sauvegarde)
   /mzarchives/EC6/.../MACH   <----->   /BACKUP-MZ1/mzarchives/EC6/...
        20260701/ ...                        20260701/ ...
        20260702/ ...                        20260702/ ...
                    \                       /
                     \                     /
                       Billing_SIFAC (mz_cleanup)
```

## Points cles

- **Securise** : mode simulation (`dry-run`) par defaut, confirmation explicite
  obligatoire, et refus de supprimer un dossier dont la sauvegarde differe
  (sauf `--force`).
- **Performant** : `os.scandir()` en local (comptage recursif sans charger les
  noms en memoire), comptage parallelise, comptage distant via une commande
  `find` en un seul aller-retour SSH.
- **Robuste** : poursuite du traitement malgre un dossier inaccessible, arret
  propre sur `Ctrl+C`, journalisation detaillee et horodatee.
- **Autonome** : le coeur ne depend que de la bibliotheque standard. YAML et SSH
  sont des options.

## Installation

Aucune dependance obligatoire (Python 3.10+). Options :

```bash
pip install -r requirements-mz_cleanup.txt   # PyYAML (config YAML) + paramiko (SSH)
```

## Configuration

Copiez un des exemples fournis a la racine du depot et adaptez-le :

- `config.mz_cleanup.example.yaml` (YAML)
- `config.mz_cleanup.example.json` (JSON)

Formats supportes : **YAML**, **JSON**, **INI** (deduit de l'extension).

Principaux parametres :

| Champ          | Role                                                        |
| -------------- | ----------------------------------------------------------- |
| `pairs`        | Couples `mz1` / `backup` de repertoires a comparer.         |
| `mz1_ssh`      | Connexion SSH vers MZ1 (`enabled: false` = acces local).    |
| `backup_ssh`   | Connexion SSH vers BACKUP-MZ.                               |
| `dry_run`      | Mode simulation (aucune suppression).                       |
| `force`        | Autorise la suppression malgre une sauvegarde differente.   |
| `workers`      | Nombre de threads de comptage.                              |
| `date_pattern` | Regex des dossiers dates (defaut `\d{8}`).                   |
| `logging`      | Niveaux et fichier de log.                                  |

## Utilisation

```bash
# Scan + comparaison seulement (aucune phase de suppression)
python -m mz_cleanup --config config.mz_cleanup.yaml --no-delete

# Session interactive (selection puis confirmation ; dry-run selon la config)
python -m mz_cleanup --config config.mz_cleanup.yaml

# Selectionner automatiquement les dossiers OK, sans interaction, en reel
python -m mz_cleanup --config config.mz_cleanup.yaml --no-dry-run --select ok --yes

# Alternative sans "-m" :
python run_mz_cleanup.py --config config.mz_cleanup.yaml
```

### Principales options

| Option              | Description                                                   |
| ------------------- | ------------------------------------------------------------- |
| `-c, --config`      | Chemin du fichier de configuration (obligatoire).            |
| `--dry-run` / `--no-dry-run` | Force / desactive le mode simulation.               |
| `--force`           | Autorise la suppression de dossiers non conformes.           |
| `--select EXPR`     | Selection non interactive : `1-10`, `1,5,8`, `ok`, `all`.    |
| `--yes, -y`         | Confirme automatiquement la suppression.                     |
| `--no-delete`       | Scan et comparaison uniquement.                              |
| `--workers N`       | Nombre de threads de comptage.                               |
| `--log-level`       | Niveau console (`DEBUG`, `INFO`, `WARNING`, `ERROR`).        |
| `--no-color`        | Desactive les couleurs.                                      |

### Modes de selection

- **Par numero** : `5`
- **Par plage** : `1-10`
- **Multiple** : `1,5,8,12`
- **Automatique (statut OK)** : `ok`
- **Tout** : `all`

Les expressions sont combinables (`1-3,7,ok`).

## Statuts de comparaison

| Statut        | Signification                                        |
| ------------- | ---------------------------------------------------- |
| `OK`          | Meme nombre de fichiers des deux cotes.              |
| `Difference`  | Ecart de nombre de fichiers.                         |
| `MZ1 seul`    | Date presente uniquement sur MZ1.                    |
| `BACKUP seul` | Date presente uniquement sur BACKUP.                 |
| `Vide`        | Dossier vide (MZ1 et/ou BACKUP).                     |
| `Erreur`      | Erreur d'acces lors du scan.                         |

Seuls les dossiers `OK` sont supprimables sans `--force`.

## Architecture

```
mz_cleanup/
  config.py         Chargement/validation de la configuration (YAML/JSON/INI).
  models.py         Structures de donnees (DirStat, ComparisonRow, Statut...).
  logging_setup.py  Journalisation fichier + console coloree.
  scanner.py        Scan local (os.scandir) et distant (SSH/find) + suppression.
  comparator.py     Regles de comparaison MZ1 <-> BACKUP.
  selector.py       Analyse des expressions de selection.
  display.py        Tableaux, barre de progression, couleurs, resume final.
  remover.py        Suppression securisee (garde-fous dry-run / force).
  cli.py            Orchestration et interface en ligne de commande.
```

## Tests

```bash
python -m pytest tests/test_mz_cleanup.py     # avec pytest
python tests/test_mz_cleanup.py               # sans pytest
```
