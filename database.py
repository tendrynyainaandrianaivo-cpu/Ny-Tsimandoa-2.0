# -*- coding: utf-8 -*-
"""
Couche d'accès aux données pour l'application de gestion de livraisons.
100% locale (SQLite), aucune dépendance réseau.

Schéma :
    vendeurs        -> les vendeurs (= "clients" de l'agence) qui confient des colis
    colis           -> chaque colis/livraison individuel, rattaché à un vendeur
    carburant_jour  -> le montant de carburant dépensé, un par jour, jamais écrasé

Statuts de colis (choix unique, définitif une fois posé) :
    'livre'    -> Livré      (vert)
    'annule'   -> Annulé     (rouge)
    'retour'   -> Colis Retour (orange)
    'reporte'  -> Livraison reportée (jaune)
"""

import sqlite3
from datetime import datetime

STATUTS = {
    "livre": "Livré",
    "annule": "Annulé",
    "retour": "Colis Retour",
    "reporte": "Livraison reportée",
}

DB_PATH_DEFAULT = "livraisons.db"


def aujourdhui():
    """Renvoie la date du jour au format YYYY-MM-DD (heure locale du téléphone)."""
    return datetime.now().strftime("%Y-%m-%d")


def get_connection(db_path=DB_PATH_DEFAULT):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(conn):
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS vendeurs (
            id                    TEXT PRIMARY KEY,
            nom                   TEXT NOT NULL,
            contact               TEXT,
            lieu_recuperation     TEXT,
            frais_recuperation    REAL NOT NULL DEFAULT 0,
            nombre_colis_declare  INTEGER NOT NULL DEFAULT 0,
            date_creation         TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS colis (
            id                INTEGER PRIMARY KEY AUTOINCREMENT,
            vendeur_id        TEXT NOT NULL,
            date_creation     TEXT NOT NULL,
            contact_client    TEXT,
            lieu_livraison    TEXT,
            montant_livraison REAL NOT NULL DEFAULT 0,
            frais_livraison   REAL NOT NULL DEFAULT 0,
            statut            TEXT,
            FOREIGN KEY (vendeur_id) REFERENCES vendeurs(id)
        );

        CREATE TABLE IF NOT EXISTS carburant_jour (
            date    TEXT PRIMARY KEY,
            montant REAL NOT NULL DEFAULT 0
        );

        CREATE INDEX IF NOT EXISTS idx_colis_vendeur ON colis(vendeur_id);
        CREATE INDEX IF NOT EXISTS idx_colis_date ON colis(date_creation);
        """
    )
    conn.commit()


# ---------------------------------------------------------------------------
# Vendeurs
# ---------------------------------------------------------------------------

def _generer_id_vendeur(conn):
    """ID séquentiel unique : V0001, V0002, ... (illimité, s'étend au-delà de 4 chiffres)."""
    row = conn.execute("SELECT COUNT(*) AS n FROM vendeurs").fetchone()
    n = row["n"] + 1
    return f"V{n:04d}"


def ajouter_vendeur(conn, nom, contact="", lieu_recuperation="", frais_recuperation=0,
                     nombre_colis_declare=0):
    vendeur_id = _generer_id_vendeur(conn)
    conn.execute(
        """INSERT INTO vendeurs (id, nom, contact, lieu_recuperation, frais_recuperation,
                                  nombre_colis_declare, date_creation)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (vendeur_id, nom.strip(), contact.strip(), lieu_recuperation.strip(),
         float(frais_recuperation or 0), int(nombre_colis_declare or 0), aujourdhui()),
    )
    conn.commit()
    return vendeur_id


def obtenir_vendeur(conn, vendeur_id):
    return conn.execute("SELECT * FROM vendeurs WHERE id = ?", (vendeur_id,)).fetchone()


def lister_vendeurs(conn):
    return conn.execute("SELECT * FROM vendeurs ORDER BY nom COLLATE NOCASE").fetchall()


def rechercher_vendeurs(conn, terme):
    """Recherche par ID, nom ou numéro de contact (insensible à la casse, partielle)."""
    terme = f"%{terme.strip()}%"
    return conn.execute(
        """SELECT * FROM vendeurs
           WHERE id LIKE ? OR nom LIKE ? OR contact LIKE ?
           ORDER BY nom COLLATE NOCASE""",
        (terme, terme, terme),
    ).fetchall()


# ---------------------------------------------------------------------------
# Colis
# ---------------------------------------------------------------------------

def ajouter_colis(conn, vendeur_id, contact_client="", lieu_livraison="",
                   montant_livraison=0, frais_livraison=0, date_creation=None):
    date_creation = date_creation or aujourdhui()
    cur = conn.execute(
        """INSERT INTO colis (vendeur_id, date_creation, contact_client, lieu_livraison,
                               montant_livraison, frais_livraison, statut)
           VALUES (?, ?, ?, ?, ?, ?, NULL)""",
        (vendeur_id, date_creation, contact_client.strip(), lieu_livraison.strip(),
         float(montant_livraison or 0), float(frais_livraison or 0)),
    )
    conn.commit()
    return cur.lastrowid


def definir_statut_colis(conn, colis_id, statut):
    """Fixe le statut d'un colis. Refuse si un statut est déjà posé (choix irréversible)."""
    if statut not in STATUTS:
        raise ValueError(f"Statut inconnu : {statut}")
    row = conn.execute("SELECT statut FROM colis WHERE id = ?", (colis_id,)).fetchone()
    if row is None:
        raise ValueError("Colis introuvable")
    if row["statut"] is not None:
        return False  # déjà fixé, action irréversible : on n'écrase pas
    conn.execute("UPDATE colis SET statut = ? WHERE id = ?", (statut, colis_id))
    conn.commit()
    return True


def lister_colis_vendeur(conn, vendeur_id, mois=None):
    """mois optionnel au format YYYY-MM pour ne prendre que les colis de ce mois-là."""
    if mois:
        return conn.execute(
            """SELECT * FROM colis WHERE vendeur_id = ? AND date_creation LIKE ?
               ORDER BY id""",
            (vendeur_id, f"{mois}%"),
        ).fetchall()
    return conn.execute(
        "SELECT * FROM colis WHERE vendeur_id = ? ORDER BY id", (vendeur_id,)
    ).fetchall()


def colis_du_jour(conn, date=None):
    date = date or aujourdhui()
    return conn.execute(
        """SELECT colis.*, vendeurs.nom AS vendeur_nom
           FROM colis JOIN vendeurs ON vendeurs.id = colis.vendeur_id
           WHERE colis.date_creation = ?
           ORDER BY colis.id""",
        (date,),
    ).fetchall()


def jours_avec_livraisons(conn):
    """Liste des dates distinctes ayant au moins un colis, les plus récentes d'abord."""
    rows = conn.execute(
        "SELECT DISTINCT date_creation FROM colis ORDER BY date_creation DESC"
    ).fetchall()
    return [r["date_creation"] for r in rows]


def totaux(colis_rows):
    """Totaux séparés (jamais additionnés) sur une liste de lignes colis."""
    total_frais = sum(c["frais_livraison"] for c in colis_rows)
    total_montant = sum(c["montant_livraison"] for c in colis_rows)
    return {"total_frais_livraison": total_frais, "total_montant_livraison": total_montant,
            "nombre_colis": len(colis_rows)}


def totaux_vendeur(conn, vendeur_id, mois=None):
    return totaux(lister_colis_vendeur(conn, vendeur_id, mois=mois))


# ---------------------------------------------------------------------------
# Carburant quotidien
# ---------------------------------------------------------------------------

def definir_carburant_jour(conn, montant, date=None):
    date = date or aujourdhui()
    conn.execute(
        """INSERT INTO carburant_jour (date, montant) VALUES (?, ?)
           ON CONFLICT(date) DO UPDATE SET montant = excluded.montant""",
        (date, float(montant or 0)),
    )
    conn.commit()


def obtenir_carburant_jour(conn, date=None):
    date = date or aujourdhui()
    row = conn.execute(
        "SELECT montant FROM carburant_jour WHERE date = ?", (date,)
    ).fetchone()
    return row["montant"] if row else 0.0


# ---------------------------------------------------------------------------
# Archive mensuelle
# ---------------------------------------------------------------------------

def resume_mensuel(conn, annee_mois):
    """annee_mois au format 'YYYY-MM'. Renvoie totaux, lieux les plus fréquents,
    total carburant du mois et vendeurs actifs ce mois-là."""
    colis_mois = conn.execute(
        "SELECT * FROM colis WHERE date_creation LIKE ?", (f"{annee_mois}%",)
    ).fetchall()

    lieux = {}
    for c in colis_mois:
        lieu = c["lieu_livraison"] or "(non renseigné)"
        lieux[lieu] = lieux.get(lieu, 0) + 1
    lieux_tries = sorted(lieux.items(), key=lambda kv: kv[1], reverse=True)

    total_carburant = conn.execute(
        "SELECT COALESCE(SUM(montant), 0) AS s FROM carburant_jour WHERE date LIKE ?",
        (f"{annee_mois}%",),
    ).fetchone()["s"]

    vendeur_ids = sorted({c["vendeur_id"] for c in colis_mois})
    vendeurs_actifs = [obtenir_vendeur(conn, vid) for vid in vendeur_ids]

    resultat = totaux(colis_mois)
    resultat.update({
        "lieux_frequents": lieux_tries,
        "total_carburant": total_carburant,
        "vendeurs_actifs": vendeurs_actifs,
    })
    return resultat


def mois_avec_livraisons(conn):
    """Liste des mois distincts (YYYY-MM) ayant au moins un colis, les plus récents d'abord."""
    rows = conn.execute(
        "SELECT DISTINCT substr(date_creation, 1, 7) AS mois FROM colis ORDER BY mois DESC"
    ).fetchall()
    return [r["mois"] for r in rows]
