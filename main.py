# -*- coding: utf-8 -*-
"""Point d'entrée de l'application de gestion de livraisons.
100% hors ligne : toutes les données sont stockées localement dans livraisons.db (SQLite)."""

from kivy.app import App
from kivy.uix.screenmanager import ScreenManager, NoTransition

import database as db
from screens import (
    EcranVendeurs, EcranDetailVendeur, EcranAujourdhui,
    EcranArchiveJours, EcranDetailJour, EcranArchiveMois, EcranDetailMois,
)

DB_PATH = "livraisons.db"


class LivraisonApp(App):
    def build(self):
        self.title = "NY TSIMANDOA"
        conn = db.get_connection(DB_PATH)
        db.init_db(conn)

        sm = ScreenManager(transition=NoTransition())
        sm.conn = conn  # connexion SQLite partagée, accessible via self.manager.conn

        sm.add_widget(EcranVendeurs())
        sm.add_widget(EcranDetailVendeur())
        sm.add_widget(EcranAujourdhui())
        sm.add_widget(EcranArchiveJours())
        sm.add_widget(EcranDetailJour())
        sm.add_widget(EcranArchiveMois())
        sm.add_widget(EcranDetailMois())

        sm.current = "vendeurs"
        return sm

    def on_stop(self):
        # Ferme proprement la connexion SQLite à la fermeture de l'application.
        conn = getattr(self.root, "conn", None)
        if conn is not None:
            conn.close()


if __name__ == "__main__":
    LivraisonApp().run()
