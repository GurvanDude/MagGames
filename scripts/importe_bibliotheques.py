"""
Importe un CSV de bibliotheques dans la base.

Format attendu (l'ordre des colonnes n'a pas d'importance) :

    steamid, appid, name, playtime_forever[, playtime_2weeks]

Sert a recuperer une collecte faite ailleurs (par un coequipier, un ancien
script, un dataset) sans repasser par l'API.

Les doublons sont impossibles : la cle primaire de bibliotheque est
(steamid, appid). Une ligne deja presente est ignoree, PAS ecrasee : les
donnees collectees par l'API sont datees, celles d'un CSV ne le sont pas.

    python scripts/importe_bibliotheques.py --csv data/owned_games.csv
"""
import argparse
import csv
import time

import db as base

LOT = 50000


def main():
    parser = argparse.ArgumentParser(description='Importe un CSV de bibliotheques')
    parser.add_argument('--csv', required=True, help='fichier a importer')
    parser.add_argument('--db', default=None)
    parser.add_argument('--source', default='import', help='nom du lot')
    parser.add_argument('--remplacer', action='store_true',
                        help='ecraser les lignes deja en base (par defaut on les garde)')
    args = parser.parse_args()

    chemin = base.RACINE / args.csv

    if not chemin.exists():
        print(f'Erreur : {chemin} introuvable')
        return

    cx = base.connexion(args.db)

    avantLignes = cx.execute('SELECT count(*) FROM bibliotheque').fetchone()[0]
    avantJoueurs = cx.execute('SELECT count(DISTINCT steamid) FROM bibliotheque').fetchone()[0]

    print(f'base avant : {avantJoueurs} joueurs, {avantLignes} lignes')
    print(f'import de {chemin.name} (source "{args.source}")\n')

    verbe = 'REPLACE' if args.remplacer else 'IGNORE'
    sqlBiblio = (f'INSERT OR {verbe} INTO bibliotheque '
                 '(source, steamid, appid, minutes_jouees, minutes_2semaines) '
                 'VALUES (?, ?, ?, ?, ?)')

    lignes = []
    jeux = []
    joueurs = set()
    n = 0
    debut = time.monotonic()

    def vider():
        cx.executemany('INSERT OR IGNORE INTO jeux (appid, nom) VALUES (?, ?)', jeux)
        # nom seulement s'il manque : on n'ecrase pas celui du catalogue
        cx.executemany('UPDATE jeux SET nom = ? WHERE appid = ? '
                       'AND (nom IS NULL OR nom = "")',
                       [(nom, appid) for appid, nom in jeux])
        cx.executemany(sqlBiblio, lignes)
        cx.commit()

    rejetees = 0
    sansJeu = set()

    with open(chemin, newline='', encoding='utf-8') as f:
        for l in csv.DictReader(f):
            steamid = (l.get('steamid') or '').strip()

            # Une ligne avec un steamid mais un appid vide signale un joueur
            # SANS jeu (bibliotheque vide ou fermee au moment de l'export).
            # Ce n'est pas une erreur : on la note et on passe.
            try:
                appid = int(l['appid'])
            except (TypeError, ValueError, KeyError):
                if steamid.isdigit():
                    sansJeu.add(steamid)
                else:
                    rejetees += 1
                continue

            if not steamid.isdigit():
                rejetees += 1
                continue

            joueurs.add(steamid)
            jeux.append((appid, l.get('name', '')))
            def minutes(champ):
                try:
                    return int(float(l.get(champ) or 0))
                except ValueError:
                    return 0

            lignes.append((
                args.source, steamid, appid,
                minutes('playtime_forever'),
                minutes('playtime_2weeks'),
            ))
            n += 1

            if len(lignes) >= LOT:
                vider()
                lignes, jeux = [], []
                print(f'  {n} lignes ({time.monotonic() - debut:.0f}s)')

    if lignes:
        vider()

    # Un joueur dont on lit la bibliotheque est forcement public
    cx.executemany("INSERT INTO joueurs (steamid, statut, maj_le) VALUES (?, 'public', ?) "
                   "ON CONFLICT(steamid) DO UPDATE SET statut = 'public', maj_le = ?",
                   [(s, time.time(), time.time()) for s in joueurs])
    cx.commit()

    apresLignes = cx.execute('SELECT count(*) FROM bibliotheque').fetchone()[0]
    apresJoueurs = cx.execute('SELECT count(DISTINCT steamid) FROM bibliotheque').fetchone()[0]

    print(f'\n{n} lignes lues en {time.monotonic() - debut:.0f}s')
    print(f'  joueurs avec des jeux : {len(joueurs)}')
    print(f'  joueurs sans jeu      : {len(sansJeu)} (non marques, l API tranchera)')
    print(f'  lignes vraiment KO    : {rejetees}')
    print(f'  lignes ajoutees       : {apresLignes - avantLignes}')
    print(f'  lignes ignorees       : {n - (apresLignes - avantLignes)} (deja en base)')
    print(f'\nbase apres : {apresJoueurs} joueurs (+{apresJoueurs - avantJoueurs}), '
          f'{apresLignes} lignes')

    cx.close()


if __name__ == '__main__':
    main()
