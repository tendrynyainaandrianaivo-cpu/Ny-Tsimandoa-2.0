# NY TSIMANDOA — application de gestion de livraisons

Application Android (Kivy, Python), 100% hors ligne — toutes les données sont stockées
localement dans le fichier `livraisons.db` (SQLite), aucune connexion internet requise.

## Fichiers du projet

| Fichier            | Rôle                                                              |
|---------------------|--------------------------------------------------------------------|
| `database.py`       | Toute la logique de données (vendeurs, colis, carburant, archives) |
| `utils.py`          | Formatage (Ariary, dates en français)                             |
| `screens.py`        | Les écrans de l'application (logique Python)                      |
| `livraison.kv`      | La mise en page visuelle des écrans (langage KV de Kivy)          |
| `main.py`           | Point d'entrée de l'application                                   |
| `test_database.py`  | Tests automatiques de la couche de données                        |
| `buildozer.spec`    | Configuration pour compiler l'APK Android plus tard                |

## Ce qui a été vérifié ici, et ce qui ne l'a pas été

Cet environnement n'a pas accès à internet, donc Kivy n'a pas pu être installé ni
testé visuellement ici. En revanche :
- **`database.py` a été testé et validé** (voir `test_database.py`) : génération des ID
  vendeurs, recherche, calcul des totaux séparés, irréversibilité du statut, non-écrasement
  du carburant d'un jour à l'autre, regroupement quotidien et mensuel — tout fonctionne
  comme prévu.
- **L'interface Kivy (`screens.py`, `livraison.kv`) n'a pas pu être lancée ni vue ici.**
  Le code suit les conventions standards de Kivy, mais il faudra le tester chez toi
  (étape 1 ci-dessous) avant de passer à la compilation Android, au cas où un ajustement
  visuel serait nécessaire.

## Étape 1 — Tester sur ordinateur (avant l'APK)

```bash
pip install -r requirements.txt
python3 main.py
```

Une fenêtre s'ouvre avec l'application (utilisable à la souris comme un téléphone).
C'est plus rapide pour corriger d'éventuels ajustements avant de compiler pour Android.

## Étape 2 — Compiler en APK via GitHub (recommandé, pas besoin de Linux)

Le dossier `.github/workflows/build.yml` est déjà inclus : dès que le projet est
envoyé sur GitHub, la compilation se lance automatiquement dans le cloud. Voir le
guide détaillé fourni dans la conversation pour la marche à suivre pas à pas.

`buildozer.spec` est déjà réglé sur une API minimale de 21 (Android 5.0, 2014) :
c'est aujourd'hui le plancher réaliste pour couvrir un maximum d'appareils avec les
outils de compilation actuels.

## Alternative — Compiler en local (Linux ou WSL)

```bash
pip install buildozer cython
buildozer android debug
```

L'APK généré se trouve ensuite dans `bin/`.

## Deux ajustements faits pendant la conception

- **Produit/Article, Quantité, Prix unitaire, Heure à rattraper** (mentionnés au tout
  début) n'apparaissent plus : les descriptions les plus détaillées et les plus récentes
  (texte + schéma) n'en parlaient plus. Le rapport mensuel "articles les plus livrés"
  a donc été remplacé par "lieux les plus fréquents" + nombre total de colis, qui ne
  dépendent pas de ces champs. Si tu veux les remettre, c'est facile à ajouter.
- **La clôture "vers 20h"** est gérée par regroupement automatique par date du jour,
  plutôt que par un déclencheur à une heure précise : sur une appli hors-ligne, le
  téléphone n'est pas toujours ouvert pile à 20h, donc chaque colis rejoint simplement
  la section du jour où il a été saisi, consultable à tout moment dans l'onglet
  "Aujourd'hui" (jour en cours) ou "Jours" (archive).
