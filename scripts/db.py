"""
Base du projet : data/maggames.db

Trois tables, rien de plus :

    jeux          le catalogue Steam, une ligne par jeu
    joueurs       un SteamID et son statut (inconnu | public | prive)
    bibliotheque  qui possede quoi, avec le temps de jeu

Le lien est l'appid : bibliotheque.appid -> jeux.appid.

Le schema de 'jeux' suit celui du dataset FronkonGames, qui est la source du
catalogue (voir telecharge_catalogue.py et importe_catalogue.py).
"""
import sqlite3
import time
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
CHEMIN_DEFAUT = RACINE / 'data' / 'maggames.db'

# Definition isolee : importe_catalogue.py la reutilise pour reconstruire la
# table a chaque import, il ne doit pas exister deux versions du schema.
SCHEMA_JEUX = """
CREATE TABLE IF NOT EXISTS jeux (
    appid                INTEGER PRIMARY KEY,
    nom                  TEXT,
    description          TEXT,   -- resume affichable
    description_longue   TEXT,
    date_sortie          TEXT,
    prix                 REAL,   -- en dollars, 0 = gratuit
    developpeur          TEXT,
    editeur              TEXT,
    genre                TEXT,   -- "Action, Indie, RPG"
    categories           TEXT,   -- "Single-player|Steam Achievements"
    tags                 TEXT,   -- "Action Roguelike:1330|Rogue-lite:954"
    langues              TEXT,
    plateformes          TEXT,   -- "windows|mac|linux"
    metacritic           INTEGER,
    note_utilisateurs    INTEGER,
    avis_positifs        INTEGER,
    avis_negatifs        INTEGER,
    recommandations      INTEGER,
    proprietaires        TEXT,   -- fourchette, ex "5000000 - 10000000"
    temps_moyen_minutes  INTEGER,
    temps_median_minutes INTEGER,
    joueurs_simultanes   INTEGER,
    succes               INTEGER,
    nb_dlc               INTEGER,
    age_minimum          INTEGER,
    image                TEXT,
    site_web             TEXT
);
"""

SCHEMA = SCHEMA_JEUX + """
CREATE TABLE IF NOT EXISTS joueurs (
    steamid TEXT PRIMARY KEY,
    statut  TEXT,             -- inconnu | public | prive
    maj_le  REAL
);

CREATE TABLE IF NOT EXISTS bibliotheque (
    source            TEXT    DEFAULT 'source1',
    steamid           TEXT    NOT NULL REFERENCES joueurs(steamid),
    appid             INTEGER NOT NULL REFERENCES jeux(appid),
    minutes_jouees    INTEGER DEFAULT 0,
    minutes_2semaines INTEGER DEFAULT 0,
    PRIMARY KEY (steamid, appid)
);

CREATE INDEX IF NOT EXISTS idx_biblio_appid ON bibliotheque(appid);
CREATE INDEX IF NOT EXISTS idx_joueurs_statut ON joueurs(statut);
CREATE INDEX IF NOT EXISTS idx_jeux_nom ON jeux(nom);
"""


def connexion(chemin=None):
    """Ouvre la base et cree les tables si besoin."""
    p = Path(chemin) if chemin else CHEMIN_DEFAUT

    if not p.is_absolute():
        p = RACINE / p

    p.parent.mkdir(parents=True, exist_ok=True)

    cx = sqlite3.connect(p)

    # Nettement plus rapide en insertion massive, sans risque reel pour des
    # donnees qu'on peut recollecter.
    cx.execute('PRAGMA journal_mode = WAL')
    cx.execute('PRAGMA synchronous = NORMAL')

    # Sans ca, deux scripts qui ecrivent en meme temps se font planter avec
    # "database is locked". La, on attend son tour jusqu'a 60 secondes.
    cx.execute('PRAGMA busy_timeout = 60000')

    cx.executescript(SCHEMA)
    cx.commit()

    return cx


def majJoueur(cx, steamid, statut):
    cx.execute(
        'INSERT INTO joueurs (steamid, statut, maj_le) VALUES (?, ?, ?) '
        'ON CONFLICT(steamid) DO UPDATE SET statut = ?, maj_le = ?',
        (steamid, statut, time.time(), statut, time.time()))


def majBibliotheque(cx, source, steamid, jeux):
    """jeux = liste de (appid, minutes_jouees, minutes_2semaines)."""
    # Les appid inconnus du catalogue sont crees vides : la collecte des
    # bibliotheques ne doit pas dependre de l'avancement du catalogue.
    cx.executemany('INSERT OR IGNORE INTO jeux (appid) VALUES (?)',
                   [(a,) for a, _, _ in jeux])

    cx.executemany(
        'INSERT OR REPLACE INTO bibliotheque '
        '(source, steamid, appid, minutes_jouees, minutes_2semaines) '
        'VALUES (?, ?, ?, ?, ?)',
        [(source, steamid, a, m, m2) for a, m, m2 in jeux])
