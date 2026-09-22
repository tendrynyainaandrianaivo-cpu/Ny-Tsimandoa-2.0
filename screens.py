# -*- coding: utf-8 -*-
"""Écrans de l'application (logique Python). La mise en page statique est dans livraison.kv ;
les listes (vendeurs, colis, jours, mois) sont construites dynamiquement ici."""

from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.popup import Popup
from kivy.uix.scrollview import ScrollView
from kivy.graphics import Color, RoundedRectangle
from kivy.metrics import dp

import database as db
from utils import fmt_ar, fmt_date_longue, fmt_mois_long, STATUT_COULEURS

DB_PATH = "livraisons.db"


# ---------------------------------------------------------------------------
# Petits composants réutilisables
# ---------------------------------------------------------------------------

class Carte(BoxLayout):
    """Un conteneur avec un fond légèrement grisé, pour délimiter visuellement une carte."""

    def __init__(self, **kwargs):
        super().__init__(orientation="vertical", padding=dp(10), spacing=dp(4),
                          size_hint_y=None, **kwargs)
        self.bind(minimum_height=self.setter("height"))
        with self.canvas.before:
            Color(0.93, 0.93, 0.95, 1)
            self._rect = RoundedRectangle(radius=[dp(8)], pos=self.pos, size=self.size)
        self.bind(pos=self._maj_rect, size=self._maj_rect)

    def _maj_rect(self, *_args):
        self._rect.pos = self.pos
        self._rect.size = self.size


def ligne_titre_valeur(titre, valeur):
    ligne = BoxLayout(size_hint_y=None, height=dp(24))
    ligne.add_widget(Label(text=titre, size_hint_x=0.45, halign="left", valign="middle",
                            color=(0.3, 0.3, 0.3, 1), font_size="13sp"))
    lbl = Label(text=str(valeur), halign="left", valign="middle", font_size="14sp")
    lbl.bind(size=lbl.setter("text_size"))
    ligne.add_widget(lbl)
    return ligne


def construire_ligne_colis(colis_row, conn, on_statut_pose=None, afficher_vendeur=False):
    """Construit la carte d'un colis : infos + (boutons de statut OU statut déjà posé)."""
    carte = Carte()

    if afficher_vendeur:
        carte.add_widget(ligne_titre_valeur("Vendeur", colis_row["vendeur_nom"]))
    carte.add_widget(ligne_titre_valeur("Contact Client", colis_row["contact_client"] or "-"))
    carte.add_widget(ligne_titre_valeur("Lieu de livraison", colis_row["lieu_livraison"] or "-"))
    carte.add_widget(ligne_titre_valeur("Montant du livraison", fmt_ar(colis_row["montant_livraison"])))
    carte.add_widget(ligne_titre_valeur("Frais de livraison", fmt_ar(colis_row["frais_livraison"])))

    zone_statut = BoxLayout(size_hint_y=None, height=dp(40), spacing=dp(4))
    carte.add_widget(zone_statut)

    def afficher_statut_pose(statut_key):
        zone_statut.clear_widgets()
        libelle = db.STATUTS[statut_key]
        lbl = Label(text=libelle, bold=True, color=(1, 1, 1, 1))
        with lbl.canvas.before:
            Color(*STATUT_COULEURS[statut_key])
            rect = RoundedRectangle(radius=[dp(6)], pos=lbl.pos, size=lbl.size)
        lbl.bind(pos=lambda *_a: setattr(rect, "pos", lbl.pos),
                 size=lambda *_a: setattr(rect, "size", lbl.size))
        zone_statut.add_widget(lbl)

    def choisir_statut(statut_key, *_args):
        ok = db.definir_statut_colis(conn, colis_row["id"], statut_key)
        if ok:
            afficher_statut_pose(statut_key)
            if on_statut_pose:
                on_statut_pose()

    statut_actuel = colis_row["statut"]
    if statut_actuel:
        afficher_statut_pose(statut_actuel)
    else:
        for cle in ("livre", "annule", "retour", "reporte"):
            btn = Button(text=db.STATUTS[cle].split()[0], font_size="11sp",
                         background_normal="", background_color=STATUT_COULEURS[cle])
            btn.bind(on_release=lambda inst, c=cle: choisir_statut(c))
            zone_statut.add_widget(btn)

    return carte


# ---------------------------------------------------------------------------
# Écran : liste des vendeurs
# ---------------------------------------------------------------------------

class EcranVendeurs(Screen):
    def on_pre_enter(self, *_args):
        self.rafraichir()

    def rafraichir(self, terme=""):
        conn = self.manager.conn
        liste = self.ids.liste_vendeurs
        liste.clear_widgets()
        vendeurs = db.rechercher_vendeurs(conn, terme) if terme else db.lister_vendeurs(conn)
        if not vendeurs:
            liste.add_widget(Label(text="Aucun vendeur pour l'instant.", size_hint_y=None,
                                    height=dp(40)))
            return
        for v in vendeurs:
            t = db.totaux_vendeur(conn, v["id"])
            btn = Button(
                text=f"[b]{v['nom']}[/b]  ({v['id']})\n{t['nombre_colis']} colis - "
                     f"{fmt_ar(t['total_montant_livraison'])}",
                markup=True, size_hint_y=None, height=dp(56), halign="left",
                valign="middle",
            )
            btn.bind(size=lambda i, *_a: setattr(i, "text_size", (i.width - dp(20), None)))
            btn.bind(on_release=lambda inst, vid=v["id"]: self.ouvrir_vendeur(vid))
            liste.add_widget(btn)

    def on_recherche(self, texte):
        self.rafraichir(terme=texte)

    def ouvrir_vendeur(self, vendeur_id):
        ecran = self.manager.get_screen("detail_vendeur")
        ecran.vendeur_id = vendeur_id
        ecran.mois_filtre = None
        ecran.ecran_origine = "vendeurs"
        self.manager.current = "detail_vendeur"

    def ouvrir_formulaire_nouveau_vendeur(self):
        FormulaireVendeur(conn=self.manager.conn, on_cree=self.rafraichir).open()


class FormulaireVendeur(Popup):
    def __init__(self, conn, on_cree, **kwargs):
        super().__init__(title="Nouveau vendeur", size_hint=(0.9, 0.85), **kwargs)
        self.conn = conn
        self.on_cree = on_cree
        corps = BoxLayout(orientation="vertical", padding=dp(10), spacing=dp(8))
        self.champ_nom = TextInput(hint_text="Nom", multiline=False, size_hint_y=None, height=dp(40))
        self.champ_contact = TextInput(hint_text="Contact (téléphone)", multiline=False,
                                        size_hint_y=None, height=dp(40))
        self.champ_lieu = TextInput(hint_text="Lieu de récupération", multiline=False,
                                     size_hint_y=None, height=dp(40))
        self.champ_frais = TextInput(hint_text="Frais de récupération (Ar)", multiline=False,
                                      input_filter="float", size_hint_y=None, height=dp(40))
        self.champ_nb_colis = TextInput(hint_text="Nombre de colis à livrer", multiline=False,
                                         input_filter="int", size_hint_y=None, height=dp(40))
        for w in (self.champ_nom, self.champ_contact, self.champ_lieu, self.champ_frais,
                  self.champ_nb_colis):
            corps.add_widget(w)
        self.erreur = Label(text="", color=(0.8, 0.1, 0.1, 1), size_hint_y=None, height=dp(20))
        corps.add_widget(self.erreur)
        boutons = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(8))
        btn_annuler = Button(text="Annuler")
        btn_annuler.bind(on_release=self.dismiss)
        btn_enregistrer = Button(text="Enregistrer")
        btn_enregistrer.bind(on_release=self.enregistrer)
        boutons.add_widget(btn_annuler)
        boutons.add_widget(btn_enregistrer)
        corps.add_widget(boutons)
        self.content = corps

    def enregistrer(self, *_args):
        if not self.champ_nom.text.strip():
            self.erreur.text = "Le nom est obligatoire."
            return
        db.ajouter_vendeur(
            self.conn,
            nom=self.champ_nom.text,
            contact=self.champ_contact.text,
            lieu_recuperation=self.champ_lieu.text,
            frais_recuperation=self.champ_frais.text or 0,
            nombre_colis_declare=self.champ_nb_colis.text or 0,
        )
        self.dismiss()
        if self.on_cree:
            self.on_cree()


# ---------------------------------------------------------------------------
# Écran : détail d'un vendeur (vue complète, ou filtrée sur un mois)
# ---------------------------------------------------------------------------

class EcranDetailVendeur(Screen):
    vendeur_id = None
    mois_filtre = None
    ecran_origine = "vendeurs"

    def on_pre_enter(self, *_args):
        self.rafraichir()

    def rafraichir(self):
        conn = self.manager.conn
        v = db.obtenir_vendeur(conn, self.vendeur_id)
        if v is None:
            return
        entete = self.ids.entete_vendeur
        entete.clear_widgets()
        entete.add_widget(ligne_titre_valeur("ID", v["id"]))
        entete.add_widget(ligne_titre_valeur("Nom", v["nom"]))
        entete.add_widget(ligne_titre_valeur("Contact", v["contact"] or "-"))
        entete.add_widget(ligne_titre_valeur("Lieu de récupération", v["lieu_recuperation"] or "-"))
        entete.add_widget(ligne_titre_valeur("Frais de récupération", fmt_ar(v["frais_recuperation"])))
        entete.add_widget(ligne_titre_valeur("Colis déclarés", v["nombre_colis_declare"]))

        self.ids.titre_ecran.text = (
            f"{v['nom']} — {fmt_mois_long(self.mois_filtre)}" if self.mois_filtre else v["nom"]
        )
        self.ids.bouton_ajout_colis.opacity = 0 if self.mois_filtre else 1
        self.ids.bouton_ajout_colis.disabled = bool(self.mois_filtre)

        liste = self.ids.liste_colis
        liste.clear_widgets()
        colis = db.lister_colis_vendeur(conn, self.vendeur_id, mois=self.mois_filtre)
        if not colis:
            liste.add_widget(Label(text="Aucun colis pour l'instant.", size_hint_y=None, height=dp(40)))
        for c in colis:
            liste.add_widget(construire_ligne_colis(c, conn, on_statut_pose=self.rafraichir))

        t = db.totaux_vendeur(conn, self.vendeur_id, mois=self.mois_filtre)
        self.ids.totaux_vendeur.text = (
            f"{t['nombre_colis']} colis  •  "
            f"Total montant : {fmt_ar(t['total_montant_livraison'])}  •  "
            f"Total frais : {fmt_ar(t['total_frais_livraison'])}"
        )

    def ouvrir_formulaire_nouveau_colis(self):
        FormulaireColis(conn=self.manager.conn, vendeur_id=self.vendeur_id,
                         on_cree=self.rafraichir).open()

    def retour(self):
        self.manager.current = self.ecran_origine


class FormulaireColis(Popup):
    def __init__(self, conn, vendeur_id, on_cree, **kwargs):
        super().__init__(title="Nouveau colis", size_hint=(0.9, 0.8), **kwargs)
        self.conn = conn
        self.vendeur_id = vendeur_id
        self.on_cree = on_cree
        corps = BoxLayout(orientation="vertical", padding=dp(10), spacing=dp(8))
        self.champ_client = TextInput(hint_text="Contact Client", multiline=False,
                                       size_hint_y=None, height=dp(40))
        self.champ_lieu = TextInput(hint_text="Lieu de livraison", multiline=False,
                                     size_hint_y=None, height=dp(40))
        self.champ_montant = TextInput(hint_text="Montant du livraison (Ar)", multiline=False,
                                        input_filter="float", size_hint_y=None, height=dp(40))
        self.champ_frais = TextInput(hint_text="Frais de livraison (Ar)", multiline=False,
                                      input_filter="float", size_hint_y=None, height=dp(40))
        for w in (self.champ_client, self.champ_lieu, self.champ_montant, self.champ_frais):
            corps.add_widget(w)
        boutons = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(8))
        btn_annuler = Button(text="Annuler")
        btn_annuler.bind(on_release=self.dismiss)
        btn_enregistrer = Button(text="Enregistrer")
        btn_enregistrer.bind(on_release=self.enregistrer)
        boutons.add_widget(btn_annuler)
        boutons.add_widget(btn_enregistrer)
        corps.add_widget(boutons)
        self.content = corps

    def enregistrer(self, *_args):
        db.ajouter_colis(
            self.conn, self.vendeur_id,
            contact_client=self.champ_client.text,
            lieu_livraison=self.champ_lieu.text,
            montant_livraison=self.champ_montant.text or 0,
            frais_livraison=self.champ_frais.text or 0,
        )
        self.dismiss()
        if self.on_cree:
            self.on_cree()


# ---------------------------------------------------------------------------
# Écran : Aujourd'hui (tous vendeurs confondus) + carburant du jour
# ---------------------------------------------------------------------------

class EcranAujourdhui(Screen):
    def on_pre_enter(self, *_args):
        self.rafraichir()

    def rafraichir(self):
        conn = self.manager.conn
        aujourdhui = db.aujourdhui()
        self.ids.titre_jour.text = f"LIVRAISON DU {fmt_date_longue(aujourdhui)}"

        self.ids.champ_carburant.text = str(db.obtenir_carburant_jour(conn, aujourdhui) or "")

        liste = self.ids.liste_colis_jour
        liste.clear_widgets()
        colis = db.colis_du_jour(conn, aujourdhui)
        if not colis:
            liste.add_widget(Label(text="Aucune livraison enregistrée aujourd'hui.",
                                    size_hint_y=None, height=dp(40)))
        for c in colis:
            liste.add_widget(construire_ligne_colis(c, conn, on_statut_pose=self.rafraichir,
                                                      afficher_vendeur=True))

        t = db.totaux(colis)
        self.ids.totaux_jour.text = (
            f"{t['nombre_colis']} colis  •  Total montant : {fmt_ar(t['total_montant_livraison'])}  •  "
            f"Total frais : {fmt_ar(t['total_frais_livraison'])}"
        )

    def enregistrer_carburant(self):
        conn = self.manager.conn
        valeur = self.ids.champ_carburant.text or 0
        db.definir_carburant_jour(conn, valeur, date=db.aujourdhui())


# ---------------------------------------------------------------------------
# Écran : archive des jours passés
# ---------------------------------------------------------------------------

class EcranArchiveJours(Screen):
    def on_pre_enter(self, *_args):
        self.rafraichir()

    def rafraichir(self):
        conn = self.manager.conn
        liste = self.ids.liste_jours
        liste.clear_widgets()
        jours = db.jours_avec_livraisons(conn)
        if not jours:
            liste.add_widget(Label(text="Aucune journée archivée pour l'instant.",
                                    size_hint_y=None, height=dp(40)))
        for jour in jours:
            colis_jour = db.colis_du_jour(conn, jour)
            t = db.totaux(colis_jour)
            btn = Button(
                text=f"LIVRAISON DU {fmt_date_longue(jour)}\n"
                     f"{t['nombre_colis']} colis - {fmt_ar(t['total_montant_livraison'])}",
                size_hint_y=None, height=dp(52),
            )
            btn.bind(on_release=lambda inst, j=jour: self.ouvrir_jour(j))
            liste.add_widget(btn)

    def ouvrir_jour(self, jour):
        ecran = self.manager.get_screen("detail_jour")
        ecran.jour = jour
        self.manager.current = "detail_jour"


class EcranDetailJour(Screen):
    jour = None

    def on_pre_enter(self, *_args):
        self.rafraichir()

    def rafraichir(self):
        conn = self.manager.conn
        self.ids.titre_jour_detail.text = f"LIVRAISON DU {fmt_date_longue(self.jour)}"
        carburant = db.obtenir_carburant_jour(conn, self.jour)
        self.ids.carburant_jour_detail.text = f"Carburant du jour : {fmt_ar(carburant)}"

        liste = self.ids.liste_colis_jour_detail
        liste.clear_widgets()
        colis = db.colis_du_jour(conn, self.jour)
        for c in colis:
            liste.add_widget(construire_ligne_colis(c, conn, on_statut_pose=self.rafraichir,
                                                      afficher_vendeur=True))

        t = db.totaux(colis)
        self.ids.totaux_jour_detail.text = (
            f"{t['nombre_colis']} colis  •  Total montant : {fmt_ar(t['total_montant_livraison'])}  •  "
            f"Total frais : {fmt_ar(t['total_frais_livraison'])}"
        )

    def retour(self):
        self.manager.current = "archive_jours"


# ---------------------------------------------------------------------------
# Écran : archive mensuelle
# ---------------------------------------------------------------------------

class EcranArchiveMois(Screen):
    def on_pre_enter(self, *_args):
        self.rafraichir()

    def rafraichir(self):
        conn = self.manager.conn
        liste = self.ids.liste_mois
        liste.clear_widgets()
        mois_disponibles = db.mois_avec_livraisons(conn)
        if not mois_disponibles:
            liste.add_widget(Label(text="Aucune archive mensuelle pour l'instant.",
                                    size_hint_y=None, height=dp(40)))
        for m in mois_disponibles:
            r = db.resume_mensuel(conn, m)
            btn = Button(
                text=f"{fmt_mois_long(m)}\n{r['nombre_colis']} colis - "
                     f"{fmt_ar(r['total_montant_livraison'])}",
                size_hint_y=None, height=dp(52),
            )
            btn.bind(on_release=lambda inst, mm=m: self.ouvrir_mois(mm))
            liste.add_widget(btn)

    def ouvrir_mois(self, mois):
        ecran = self.manager.get_screen("detail_mois")
        ecran.mois = mois
        self.manager.current = "detail_mois"


class EcranDetailMois(Screen):
    mois = None

    def on_pre_enter(self, *_args):
        self.rafraichir()

    def rafraichir(self):
        conn = self.manager.conn
        r = db.resume_mensuel(conn, self.mois)
        self.ids.titre_mois.text = fmt_mois_long(self.mois)
        self.ids.totaux_mois.text = (
            f"{r['nombre_colis']} colis  •  Total montant : {fmt_ar(r['total_montant_livraison'])}\n"
            f"Total frais de livraison : {fmt_ar(r['total_frais_livraison'])}  •  "
            f"Total carburant : {fmt_ar(r['total_carburant'])}"
        )

        lieux = self.ids.liste_lieux
        lieux.clear_widgets()
        for lieu, n in r["lieux_frequents"][:10]:
            lieux.add_widget(ligne_titre_valeur(lieu, f"{n} livraison(s)"))

        vendeurs = self.ids.liste_vendeurs_mois
        vendeurs.clear_widgets()
        for v in r["vendeurs_actifs"]:
            btn = Button(text=f"{v['nom']} ({v['id']})", size_hint_y=None, height=dp(44))
            btn.bind(on_release=lambda inst, vid=v["id"]: self.ouvrir_vendeur_du_mois(vid))
            vendeurs.add_widget(btn)

    def ouvrir_vendeur_du_mois(self, vendeur_id):
        ecran = self.manager.get_screen("detail_vendeur")
        ecran.vendeur_id = vendeur_id
        ecran.mois_filtre = self.mois
        ecran.ecran_origine = "detail_mois"
        self.manager.current = "detail_vendeur"

    def retour(self):
        self.manager.current = "archive_mois"
