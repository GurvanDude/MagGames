"""
Exporte les tables de la base en CSV.

Sert a partager les donnees avec l'equipe, ou a les ouvrir dans un tableur.
La base fait plusieurs Go et n'est pas versionnee : les CSV sont le format
d'echange.

    python scripts/exporte_csv.py                 les trois tables
    python scripts/exporte_csv.py --table jeux    une seule

Les fichiers vont dans data/export/.
"""
import argparse
import csv
import time

import db as base

TABLES = ('jeux', 'joueurs', 'bibliotheque')
LOT = 100000


def exporter(cx, table, dossier):
    colonnes = [r[1] for r in cx.execute(f'PRAGMA table_info({table})')]

    if not colonnes:
        print(f'  ! table {table} introuvable')
        return

    total = cx.execute(f'SELECT count(*) FROM {table}').fetchone()[0]
    sortie = dossier / f'{table}.csv'
    debut = time.monotonic()
    n = 0

    with open(sortie, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(colonnes)

        # fetchmany plutot que fetchall : bibliotheque fait 15 millions de
        # lignes, on ne les charge pas toutes en memoire.
        curseur = cx.execute(f'SELECT {", ".join(colonnes)} FROM {table}')

        while True:
            paquet = curseur.fetchmany(LOT)

            if not paquet:
                break

            writer.writerows(paquet)
            n += len(paquet)

            if n % (LOT * 10) == 0:
                print(f'    {n}/{total}')

    taille = sortie.stat().st_size / 1024 / 1024
    print(f'  {table:14} : {n} lignes | {taille:.0f} Mo | '
          f'{time.monotonic() - debut:.0f}s -> {sortie.name}')


def main():
    parser = argparse.ArgumentParser(description='Exporte les tables en CSV')
    parser.add_argument('--db', default=None)
    parser.add_argument('--table', choices=TABLES, help='une seule table')
    parser.add_argument('--out', default='data/export', help='dossier de sortie')
    args = parser.parse_args()

    cx = base.connexion(args.db)

    dossier = base.RACINE / args.out
    dossier.mkdir(parents=True, exist_ok=True)

    print(f'Export vers {dossier}\n')

    for table in ([args.table] if args.table else TABLES):
        exporter(cx, table, dossier)

    cx.close()


if __name__ == '__main__':
    main()
