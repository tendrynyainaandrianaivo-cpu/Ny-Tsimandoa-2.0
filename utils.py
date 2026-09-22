# -*- coding: utf-8 -*-
"""Utilitaires de formatage pour l'affichage (devise Ariary, dates)."""
from datetime import datetime

MOIS_FR = ["", "Janvier", "Février", "Mars", "Avril", "Mai", "Juin",
           "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"]


def fmt_ar(montant):
    """Formate un montant en Ariary avec séparateur de milliers : 50000 -> '50 000 Ar'."""
    try:
        montant = float(montant)
    except (TypeError, ValueError):
        montant = 0
    entier = int(round(montant))
    signe = "-" if entier < 0 else ""
    entier = abs(entier)
    s = f"{entier:,}".replace(",", " ")
    return f"{signe}{s} Ar"


def fmt_date_longue(date_iso):
    """'2026-09-21' -> '21 Septembre 2026'."""
    try:
        d = datetime.strptime(date_iso, "%Y-%m-%d")
    except (ValueError, TypeError):
        return date_iso or ""
    return f"{d.day} {MOIS_FR[d.month]} {d.year}"


def fmt_mois_long(annee_mois):
    """'2026-09' -> 'Septembre 2026'."""
    try:
        annee, mois = annee_mois.split("-")
        return f"{MOIS_FR[int(mois)]} {annee}"
    except (ValueError, IndexError, TypeError):
        return annee_mois or ""


STATUT_COULEURS = {
    "livre":   (0.20, 0.70, 0.20, 1),   # vert
    "annule":  (0.80, 0.20, 0.20, 1),   # rouge
    "retour":  (0.95, 0.55, 0.10, 1),   # orange
    "reporte": (0.90, 0.80, 0.10, 1),   # jaune
}
