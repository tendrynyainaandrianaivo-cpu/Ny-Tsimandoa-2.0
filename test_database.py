# -*- coding: utf-8 -*-
"""Tests rapides de la couche database.py (sans Kivy, juste sqlite3)."""
import os
import database as db

TEST_DB = "test_livraisons.db"
if os.path.exists(TEST_DB):
    os.remove(TEST_DB)

conn = db.get_connection(TEST_DB)
db.init_db(conn)

# --- Création de vendeurs, vérification des ID séquentiels ---
v1 = db.ajouter_vendeur(conn, "Rakoto", "034 11 222 33", "Analakely", 2000, nombre_colis_declare=2)
v2 = db.ajouter_vendeur(conn, "Bao Shop", "032 44 555 66", "Behoririka", 1500, nombre_colis_declare=3)
assert v1 == "V0001", v1
assert v2 == "V0002", v2
print("OK: ID vendeurs séquentiels ->", v1, v2)

# --- Recherche par nom / téléphone / ID ---
assert len(db.rechercher_vendeurs(conn, "Rakoto")) == 1
assert len(db.rechercher_vendeurs(conn, "034 11")) == 1
assert len(db.rechercher_vendeurs(conn, "V0002")) == 1
assert len(db.rechercher_vendeurs(conn, "inexistant")) == 0
print("OK: recherche vendeur par nom / téléphone / ID")

# --- Colis pour v1 (2 colis, comme déclaré) ---
c1 = db.ajouter_colis(conn, v1, "Client A", "Ivandry", montant_livraison=50000, frais_livraison=5000)
c2 = db.ajouter_colis(conn, v1, "Client B", "Ankorondrano", montant_livraison=30000, frais_livraison=5000)
# --- Colis pour v2 ---
c3 = db.ajouter_colis(conn, v2, "Client C", "Ivandry", montant_livraison=20000, frais_livraison=4000)

colis_v1 = db.lister_colis_vendeur(conn, v1)
assert len(colis_v1) == 2
print("OK: colis liés au bon vendeur ->", len(colis_v1), "colis pour", v1)

# --- Statut irréversible ---
ok = db.definir_statut_colis(conn, c1, "livre")
assert ok is True
rejoue = db.definir_statut_colis(conn, c1, "annule")  # tentative de changer -> doit être refusée
assert rejoue is False
colis_c1 = conn.execute("SELECT statut FROM colis WHERE id=?", (c1,)).fetchone()
assert colis_c1["statut"] == "livre", "le statut ne doit PAS avoir changé"
print("OK: statut de colis irréversible une fois posé")

# --- Totaux vendeur (séparés, jamais additionnés) ---
t = db.totaux_vendeur(conn, v1)
assert t["total_montant_livraison"] == 80000
assert t["total_frais_livraison"] == 10000
assert t["nombre_colis"] == 2
print("OK: totaux vendeur séparés ->", t)

# --- Carburant quotidien, ne s'écrase pas d'un jour à l'autre ---
db.definir_carburant_jour(conn, 15000, date="2026-09-20")
db.definir_carburant_jour(conn, 22000, date="2026-09-21")
assert db.obtenir_carburant_jour(conn, "2026-09-20") == 15000
assert db.obtenir_carburant_jour(conn, "2026-09-21") == 22000
# on peut corriger le jour courant sans toucher aux autres jours
db.definir_carburant_jour(conn, 25000, date="2026-09-21")
assert db.obtenir_carburant_jour(conn, "2026-09-21") == 25000
assert db.obtenir_carburant_jour(conn, "2026-09-20") == 15000
print("OK: carburant quotidien conservé par jour, sans écrasement croisé")

# --- Colis du jour / regroupement quotidien ---
db.ajouter_colis(conn, v1, "Client D", "Tanjombato", 10000, 2000, date_creation="2026-09-20")
jour = db.colis_du_jour(conn, "2026-09-20")
assert len(jour) == 1
assert jour[0]["vendeur_nom"] == "Rakoto"
print("OK: regroupement des colis par jour ->", len(jour), "colis le 2026-09-20")

jours = db.jours_avec_livraisons(conn)
print("OK: jours avec livraisons ->", jours)

# --- Résumé mensuel ---
resume = db.resume_mensuel(conn, "2026-09")
assert resume["nombre_colis"] == 4  # c1,c2,c3 + celui du 20/09
assert len(resume["vendeurs_actifs"]) == 2
assert resume["lieux_frequents"][0][0] == "Ivandry"  # apparaît 2 fois
assert resume["lieux_frequents"][0][1] == 2
print("OK: résumé mensuel ->", {k: v for k, v in resume.items() if k != "vendeurs_actifs"})

print("\nTOUS LES TESTS SONT PASSÉS ✔")
os.remove(TEST_DB)
