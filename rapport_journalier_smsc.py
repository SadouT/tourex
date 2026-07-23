#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Rapport journalier des sequences SMSC (dailycheck).

Analyse les tables PostgreSQL :
    - tb_dailycheck_sequence_smsc           (bilan par noeud et par jour)
    - tb_dailycheck_sequence_smsc_manquant  (detail des fichiers manquants)

Le rapport couvre :
    1. Resume du jour (volumes, taux de completude, repartition par statut)
    2. Anomalies du jour (manquants, statut KO, incoherences de sequence,
       doublons, noeuds disparus)
    3. Tendances sur N jours (degradation, anomalies statistiques de volume,
       noeuds nouvellement apparus)
    4. Detail des fichiers manquants

Prerequis :
    pip install psycopg2-binary

Connexion (variables d'environnement) :
    DATABASE_URL="postgresql://user:pass@host:5432/base"
    -- ou bien --
    PGHOST, PGPORT, PGDATABASE, PGUSER, PGPASSWORD

Utilisation :
    python rapport_journalier_smsc.py                 # dernier jour disponible
    python rapport_journalier_smsc.py --date 2026-07-22
    python rapport_journalier_smsc.py --jours 30 --sortie ./rapports
"""

import argparse
import html
import os
import sys
from datetime import datetime, timedelta

try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
except ImportError:
    sys.exit("Le paquet 'psycopg2' est requis. Lancez : pip install psycopg2-binary")


# --------------------------------------------------------------------------- #
# Parametres / seuils d'alerte
# --------------------------------------------------------------------------- #
TABLE_BILAN = "tb_dailycheck_sequence_smsc"
TABLE_MANQUANT = "tb_dailycheck_sequence_smsc_manquant"

TAUX_ALERTE = 95.0          # taux de completude (%) en dessous duquel on alerte
Z_SEUIL = 2.0               # z-score au-dela duquel un volume est anormal
JOURS_TENDANCE = 14         # fenetre par defaut pour l'analyse de tendance
STATUTS_OK = {"OK", "COMPLET", "COMPLETE"}   # statuts consideres comme sains


# --------------------------------------------------------------------------- #
# Connexion
# --------------------------------------------------------------------------- #
def get_connection():
    url = os.environ.get("DATABASE_URL")
    try:
        if url:
            return psycopg2.connect(url)
        return psycopg2.connect(
            host=os.environ.get("PGHOST", "localhost"),
            port=os.environ.get("PGPORT", "5432"),
            dbname=os.environ.get("PGDATABASE", "postgres"),
            user=os.environ.get("PGUSER", "postgres"),
            password=os.environ.get("PGPASSWORD", ""),
        )
    except psycopg2.Error as exc:
        sys.exit(f"Connexion PostgreSQL impossible : {exc}")


def q(conn, sql, params=None):
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(sql, params or ())
        return cur.fetchall()


# --------------------------------------------------------------------------- #
# Recuperation des donnees
# --------------------------------------------------------------------------- #
def date_cible(conn, date_arg):
    if date_arg:
        return datetime.strptime(date_arg, "%Y-%m-%d").date()
    rows = q(conn, f"SELECT MAX(date_seq) AS d FROM {TABLE_BILAN}")
    d = rows[0]["d"] if rows else None
    if d is None:
        sys.exit(f"Aucune donnee dans {TABLE_BILAN}.")
    return d


def bilan_du_jour(conn, jour):
    return q(conn, f"""
        SELECT noeud, date_seq, seq_initiale, seq_finale,
               nb_fichiers_recus, nb_a_recevoir, manquants, statut, date_insertion
        FROM {TABLE_BILAN}
        WHERE date_seq = %s
        ORDER BY manquants DESC NULLS LAST, noeud
    """, (jour,))


def doublons(conn, jour):
    return q(conn, f"""
        SELECT noeud, COUNT(*) AS n
        FROM {TABLE_BILAN}
        WHERE date_seq = %s
        GROUP BY noeud
        HAVING COUNT(*) > 1
        ORDER BY n DESC, noeud
    """, (jour,))


def noeuds_disparus(conn, jour, debut):
    return q(conn, f"""
        SELECT h.noeud, MAX(h.date_seq) AS dernier_jour
        FROM {TABLE_BILAN} h
        WHERE h.date_seq BETWEEN %s AND %s
          AND h.noeud NOT IN (SELECT noeud FROM {TABLE_BILAN} WHERE date_seq = %s)
        GROUP BY h.noeud
        ORDER BY dernier_jour DESC, h.noeud
    """, (debut, jour, jour))


def serie_tendance(conn, debut, jour):
    return q(conn, f"""
        SELECT noeud, date_seq, nb_fichiers_recus, nb_a_recevoir, manquants,
               CASE WHEN nb_a_recevoir > 0
                    THEN ROUND(100.0 * nb_fichiers_recus / nb_a_recevoir, 2)
                    ELSE NULL END AS taux
        FROM {TABLE_BILAN}
        WHERE date_seq BETWEEN %s AND %s
        ORDER BY noeud, date_seq
    """, (debut, jour))


def manquants_du_jour(conn, jour):
    return q(conn, f"""
        SELECT noeud, nom_fichier
        FROM {TABLE_MANQUANT}
        WHERE date_seq = %s
        ORDER BY noeud, nom_fichier
    """, (jour,))


def manquants_par_jour(conn, debut, jour):
    return q(conn, f"""
        SELECT date_seq, COUNT(*) AS n
        FROM {TABLE_MANQUANT}
        WHERE date_seq BETWEEN %s AND %s
        GROUP BY date_seq
        ORDER BY date_seq
    """, (debut, jour))


# --------------------------------------------------------------------------- #
# Analyses
# --------------------------------------------------------------------------- #
def i(v):
    """int sur/robuste aux NULL."""
    return int(v) if v is not None else 0


def analyse_resume(rows):
    tot_recus = sum(i(r["nb_fichiers_recus"]) for r in rows)
    tot_attendu = sum(i(r["nb_a_recevoir"]) for r in rows)
    tot_manq = sum(i(r["manquants"]) for r in rows)
    taux = round(100.0 * tot_recus / tot_attendu, 2) if tot_attendu else None
    par_statut = {}
    for r in rows:
        s = (r["statut"] or "?").strip()
        par_statut[s] = par_statut.get(s, 0) + 1
    return {
        "nb_noeuds": len(rows),
        "tot_recus": tot_recus,
        "tot_attendu": tot_attendu,
        "tot_manquants": tot_manq,
        "taux": taux,
        "par_statut": par_statut,
    }


def analyse_anomalies_jour(rows):
    manquants, statut_ko, incoherences, sous_seuil = [], [], [], []
    for r in rows:
        nb_manq = i(r["manquants"])
        recu = i(r["nb_fichiers_recus"])
        attendu = i(r["nb_a_recevoir"])
        statut = (r["statut"] or "").strip()
        taux = round(100.0 * recu / attendu, 2) if attendu else None

        if nb_manq > 0:
            manquants.append((r["noeud"], nb_manq, taux))
        if statut.upper() not in STATUTS_OK:
            statut_ko.append((r["noeud"], statut or "(vide)", nb_manq))
        if taux is not None and taux < TAUX_ALERTE:
            sous_seuil.append((r["noeud"], taux, nb_manq))

        # coherence: etendue de sequence vs nb attendu, et manquants declares
        si, sf = r["seq_initiale"], r["seq_finale"]
        details = []
        if si is not None and sf is not None:
            etendue = sf - si + 1
            if attendu and etendue != attendu:
                details.append(f"etendue seq={etendue} != nb_a_recevoir={attendu}")
        if attendu and (attendu - recu) != nb_manq:
            details.append(f"manquants={nb_manq} != attendu-recus={attendu - recu}")
        if details:
            incoherences.append((r["noeud"], "; ".join(details)))

    manquants.sort(key=lambda x: x[1], reverse=True)
    sous_seuil.sort(key=lambda x: (x[1] if x[1] is not None else 999))
    return {
        "manquants": manquants,
        "statut_ko": statut_ko,
        "incoherences": incoherences,
        "sous_seuil": sous_seuil,
    }


def _pente(valeurs):
    """Pente d'une regression lineaire simple (signe = tendance)."""
    n = len(valeurs)
    if n < 2:
        return 0.0
    xs = list(range(n))
    mx = sum(xs) / n
    my = sum(valeurs) / n
    denom = sum((x - mx) ** 2 for x in xs)
    if denom == 0:
        return 0.0
    return sum((xs[k] - mx) * (valeurs[k] - my) for k in range(n)) / denom


def analyse_tendances(serie, jour):
    """Regroupe la serie par noeud et detecte degradations et anomalies."""
    par_noeud = {}
    for r in serie:
        par_noeud.setdefault(r["noeud"], []).append(r)

    degradations, anomalies_volume, nouveaux = [], [], []
    for noeud, pts in par_noeud.items():
        pts.sort(key=lambda x: x["date_seq"])
        manq = [i(p["manquants"]) for p in pts]
        recus = [i(p["nb_fichiers_recus"]) for p in pts]

        # Degradation : pente des manquants positive et manquants recents > 0
        pente = _pente(manq)
        if pente > 0.5 and manq[-1] > 0:
            degradations.append((noeud, round(pente, 2), manq[-1], manq[0]))

        # Anomalie de volume sur le dernier jour (z-score vs historique)
        if len(recus) >= 3:
            hist = recus[:-1]
            moy = sum(hist) / len(hist)
            var = sum((x - moy) ** 2 for x in hist) / len(hist)
            ecart = var ** 0.5
            if ecart > 0:
                z = (recus[-1] - moy) / ecart
                if abs(z) >= Z_SEUIL:
                    anomalies_volume.append(
                        (noeud, recus[-1], round(moy, 1), round(z, 2))
                    )

        # Noeud nouveau : premiere apparition = jour cible
        if pts[0]["date_seq"] == jour and len(pts) == 1:
            nouveaux.append(noeud)

    degradations.sort(key=lambda x: x[1], reverse=True)
    anomalies_volume.sort(key=lambda x: abs(x[3]), reverse=True)
    return {
        "degradations": degradations,
        "anomalies_volume": anomalies_volume,
        "nouveaux": sorted(nouveaux),
    }


def grouper_manquants(rows, echantillon=10):
    par_noeud = {}
    for r in rows:
        par_noeud.setdefault(r["noeud"], []).append(r["nom_fichier"])
    resultat = []
    for noeud, fichiers in sorted(par_noeud.items(), key=lambda kv: -len(kv[1])):
        resultat.append((noeud, len(fichiers), fichiers[:echantillon]))
    return resultat


# --------------------------------------------------------------------------- #
# Rendu texte
# --------------------------------------------------------------------------- #
def rendu_texte(jour, debut, resume, anomalies, tendances, manq_groupes,
                disparus, dbl, manq_serie):
    L = []
    sep = "=" * 72
    L.append(sep)
    L.append(f"  RAPPORT JOURNALIER SMSC — {jour}")
    L.append(f"  Fenetre de tendance : {debut} -> {jour}")
    L.append(sep)

    L.append("\n[1] RESUME DU JOUR")
    L.append(f"  Noeuds analyses     : {resume['nb_noeuds']}")
    L.append(f"  Fichiers recus      : {resume['tot_recus']:,}".replace(",", " "))
    L.append(f"  Fichiers attendus   : {resume['tot_attendu']:,}".replace(",", " "))
    L.append(f"  Fichiers manquants  : {resume['tot_manquants']:,}".replace(",", " "))
    taux = resume["taux"]
    L.append(f"  Taux de completude  : {taux if taux is not None else 'n/a'} %")
    L.append("  Repartition statut  : " + ", ".join(
        f"{k}={v}" for k, v in sorted(resume["par_statut"].items())))

    L.append("\n[2] ANOMALIES DU JOUR")
    if dbl:
        L.append("  ! Doublons (plusieurs lignes pour un meme noeud) :")
        for r in dbl:
            L.append(f"      - {r['noeud']} : {r['n']} lignes")
    a = anomalies
    if a["statut_ko"]:
        L.append(f"  ! Statut non conforme ({len(a['statut_ko'])}) :")
        for noeud, st, nb in a["statut_ko"][:20]:
            L.append(f"      - {noeud} : statut={st}, manquants={nb}")
    if a["sous_seuil"]:
        L.append(f"  ! Taux < {TAUX_ALERTE}% ({len(a['sous_seuil'])}) :")
        for noeud, tx, nb in a["sous_seuil"][:20]:
            L.append(f"      - {noeud} : taux={tx}%, manquants={nb}")
    if a["incoherences"]:
        L.append(f"  ! Incoherences de sequence ({len(a['incoherences'])}) :")
        for noeud, det in a["incoherences"][:20]:
            L.append(f"      - {noeud} : {det}")
    if disparus:
        L.append(f"  ! Noeuds sans remontee aujourd'hui ({len(disparus)}) :")
        for r in disparus[:20]:
            L.append(f"      - {r['noeud']} (vu pour la derniere fois le {r['dernier_jour']})")
    if not (dbl or a["statut_ko"] or a["sous_seuil"] or a["incoherences"] or disparus):
        L.append("  Aucune anomalie detectee le jour cible.")

    L.append("\n[3] TENDANCES")
    t = tendances
    if t["degradations"]:
        L.append(f"  ! Degradation (manquants en hausse) ({len(t['degradations'])}) :")
        for noeud, pente, dernier, premier in t["degradations"][:20]:
            L.append(f"      - {noeud} : pente=+{pente}/j (manquants {premier} -> {dernier})")
    if t["anomalies_volume"]:
        L.append(f"  ! Volume anormal vs historique ({len(t['anomalies_volume'])}) :")
        for noeud, val, moy, z in t["anomalies_volume"][:20]:
            sens = "chute" if z < 0 else "pic"
            L.append(f"      - {noeud} : {val} recus ({sens}, moy={moy}, z={z})")
    if t["nouveaux"]:
        L.append(f"  i Nouveaux noeuds apparus : {', '.join(t['nouveaux'][:30])}")
    if manq_serie:
        L.append("  Fichiers manquants par jour :")
        for r in manq_serie:
            L.append(f"      {r['date_seq']} : {r['n']}")
    if not (t["degradations"] or t["anomalies_volume"] or t["nouveaux"]):
        L.append("  Aucune tendance notable.")

    L.append("\n[4] DETAIL DES FICHIERS MANQUANTS")
    if manq_groupes:
        for noeud, n, echant in manq_groupes[:30]:
            L.append(f"  - {noeud} : {n} fichier(s) manquant(s)")
            for f in echant:
                L.append(f"        {f}")
            if n > len(echant):
                L.append(f"        ... (+{n - len(echant)} autres)")
    else:
        L.append("  Aucun fichier manquant recense.")

    L.append("\n" + sep)
    return "\n".join(L)


# --------------------------------------------------------------------------- #
# Rendu HTML
# --------------------------------------------------------------------------- #
def _table(entetes, lignes):
    if not lignes:
        return "<p class='ok'>Aucune donnee.</p>"
    th = "".join(f"<th>{html.escape(str(h))}</th>" for h in entetes)
    corps = ""
    for ligne in lignes:
        tds = "".join(f"<td>{html.escape(str(c))}</td>" for c in ligne)
        corps += f"<tr>{tds}</tr>"
    return f"<table><thead><tr>{th}</tr></thead><tbody>{corps}</tbody></table>"


def rendu_html(jour, debut, resume, anomalies, tendances, manq_groupes,
               disparus, dbl, manq_serie):
    taux = resume["taux"]
    classe_taux = "ok" if (taux is not None and taux >= TAUX_ALERTE) else "ko"
    genere = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    parts = [f"""<!DOCTYPE html><html lang="fr"><head><meta charset="utf-8">
<title>Rapport SMSC {jour}</title><style>
body{{font-family:system-ui,Segoe UI,Arial,sans-serif;margin:2rem;color:#1a2233;background:#f6f8fb}}
h1{{margin:0 0 .3rem}} h2{{margin-top:2rem;border-bottom:2px solid #dde3ec;padding-bottom:.3rem}}
.sub{{color:#667}} .cards{{display:flex;gap:1rem;flex-wrap:wrap;margin:1rem 0}}
.card{{background:#fff;border:1px solid #e2e8f0;border-radius:10px;padding:1rem 1.4rem;min-width:150px}}
.card .v{{font-size:1.7rem;font-weight:700}} .card .l{{color:#667;font-size:.85rem}}
table{{border-collapse:collapse;width:100%;background:#fff;margin:.6rem 0;font-size:.92rem}}
th,td{{border:1px solid #e2e8f0;padding:.4rem .6rem;text-align:left}}
th{{background:#eef2f8}} .ok{{color:#0a7d32}} .ko{{color:#c0261a;font-weight:700}}
.badge{{display:inline-block;padding:.1rem .5rem;border-radius:6px;background:#eef2f8;margin:.1rem}}
</style></head><body>
<h1>Rapport journalier SMSC — {jour}</h1>
<p class="sub">Fenetre de tendance : {debut} &rarr; {jour} &middot; genere le {genere}</p>
<div class="cards">
  <div class="card"><div class="v">{resume['nb_noeuds']}</div><div class="l">Noeuds</div></div>
  <div class="card"><div class="v">{resume['tot_recus']}</div><div class="l">Recus</div></div>
  <div class="card"><div class="v">{resume['tot_attendu']}</div><div class="l">Attendus</div></div>
  <div class="card"><div class="v ko">{resume['tot_manquants']}</div><div class="l">Manquants</div></div>
  <div class="card"><div class="v {classe_taux}">{taux if taux is not None else 'n/a'} %</div><div class="l">Completude</div></div>
</div>
<p>Statuts : """ + " ".join(
        f"<span class='badge'>{html.escape(k)} : {v}</span>"
        for k, v in sorted(resume["par_statut"].items())) + "</p>"]

    parts.append("<h2>Anomalies du jour</h2>")
    parts.append("<h3>Doublons</h3>" + _table(
        ["Noeud", "Nb lignes"], [(r["noeud"], r["n"]) for r in dbl]))
    parts.append("<h3>Statut non conforme</h3>" + _table(
        ["Noeud", "Statut", "Manquants"], anomalies["statut_ko"]))
    parts.append(f"<h3>Taux &lt; {TAUX_ALERTE}%</h3>" + _table(
        ["Noeud", "Taux %", "Manquants"], anomalies["sous_seuil"]))
    parts.append("<h3>Incoherences de sequence</h3>" + _table(
        ["Noeud", "Detail"], anomalies["incoherences"]))
    parts.append("<h3>Noeuds sans remontee aujourd'hui</h3>" + _table(
        ["Noeud", "Derniere remontee"],
        [(r["noeud"], r["dernier_jour"]) for r in disparus]))

    parts.append("<h2>Tendances</h2>")
    parts.append("<h3>Degradation (manquants en hausse)</h3>" + _table(
        ["Noeud", "Pente/j", "Manquants (dernier)", "Manquants (debut)"],
        tendances["degradations"]))
    parts.append("<h3>Volume anormal (z-score)</h3>" + _table(
        ["Noeud", "Recus", "Moyenne hist.", "z-score"],
        tendances["anomalies_volume"]))
    if tendances["nouveaux"]:
        parts.append("<h3>Nouveaux noeuds</h3><p>" + ", ".join(
            html.escape(n) for n in tendances["nouveaux"]) + "</p>")
    parts.append("<h3>Fichiers manquants par jour</h3>" + _table(
        ["Date", "Nb"], [(r["date_seq"], r["n"]) for r in manq_serie]))

    parts.append("<h2>Detail des fichiers manquants</h2>")
    lignes = []
    for noeud, n, echant in manq_groupes:
        apercu = "<br>".join(html.escape(f) for f in echant)
        if n > len(echant):
            apercu += f"<br>… (+{n - len(echant)} autres)"
        lignes.append((noeud, n, apercu))
    if lignes:
        th = "<th>Noeud</th><th>Nb</th><th>Apercu</th>"
        corps = "".join(
            f"<tr><td>{html.escape(str(a))}</td><td>{b}</td><td>{c}</td></tr>"
            for a, b, c in lignes)
        parts.append(f"<table><thead><tr>{th}</tr></thead><tbody>{corps}</tbody></table>")
    else:
        parts.append("<p class='ok'>Aucun fichier manquant.</p>")

    parts.append("</body></html>")
    return "".join(parts)


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #
def main():
    ap = argparse.ArgumentParser(description="Rapport journalier des sequences SMSC")
    ap.add_argument("--date", help="Jour cible AAAA-MM-JJ (defaut : dernier disponible)")
    ap.add_argument("--jours", type=int, default=JOURS_TENDANCE,
                    help=f"Fenetre de tendance en jours (defaut {JOURS_TENDANCE})")
    ap.add_argument("--sortie", default=".", help="Repertoire du rapport HTML")
    ap.add_argument("--no-html", action="store_true", help="Ne pas generer le HTML")
    args = ap.parse_args()

    conn = get_connection()
    try:
        jour = date_cible(conn, args.date)
        debut = jour - timedelta(days=args.jours - 1)

        rows = bilan_du_jour(conn, jour)
        if not rows:
            sys.exit(f"Aucune donnee pour le {jour} dans {TABLE_BILAN}.")

        resume = analyse_resume(rows)
        anomalies = analyse_anomalies_jour(rows)
        serie = serie_tendance(conn, debut, jour)
        tendances = analyse_tendances(serie, jour)
        manq_rows = manquants_du_jour(conn, jour)
        manq_groupes = grouper_manquants(manq_rows)
        disparus = noeuds_disparus(conn, jour, debut)
        dbl = doublons(conn, jour)
        manq_serie = manquants_par_jour(conn, debut, jour)
    finally:
        conn.close()

    texte = rendu_texte(jour, debut, resume, anomalies, tendances,
                        manq_groupes, disparus, dbl, manq_serie)
    print(texte)

    if not args.no_html:
        os.makedirs(args.sortie, exist_ok=True)
        chemin = os.path.join(args.sortie, f"rapport_smsc_{jour}.html")
        with open(chemin, "w", encoding="utf-8") as fh:
            fh.write(rendu_html(jour, debut, resume, anomalies, tendances,
                                manq_groupes, disparus, dbl, manq_serie))
        print(f"\nRapport HTML genere : {chemin}")


if __name__ == "__main__":
    main()
