"""
3/5 - Trouver de nouveaux SteamID.

Part d'un SteamID, lit sa liste d'amis, puis celle de ses amis, etc. Chaque
ID trouve est ecrit dans la table joueurs avec le statut 'inconnu' ; c'est
verifie_ids.py qui tranchera public/prive.

Un appel rapporte plusieurs centaines d'ID, donc c'est peu couteux.

Pas de gestion de doublons a faire : la base connait deja tous les ID
rencontres, ils servent de "deja vu" et ne sont jamais reajoutes.

    python scripts/cherche_ids.py 76561198003378041 --max 100000
"""
import argparse
import time
from collections import deque

import db as base
from steam_api import Limiteur, getAmis, getCle


def main():
    parser = argparse.ArgumentParser(description='Trouver de nouveaux SteamID')
    parser.add_argument('steamid', help='SteamID64 de depart')
    parser.add_argument('--db', default=None)
    parser.add_argument('--max', type=int, default=100000, help='nouveaux ID a trouver')
    parser.add_argument('--rate', type=float, default=5.0, help='appels par seconde')
    args = parser.parse_args()

    cle = getCle()

    if not cle:
        print("Erreur : STEAM_API absent du fichier .env")
        return

    cx = base.connexion(args.db)

    # Tout ce qui est deja en base sert de "deja vu"
    vus = {r[0] for r in cx.execute('SELECT steamid FROM joueurs')}
    print(f'{len(vus)} joueurs deja en base')
    print(f'Depart {args.steamid} | cible {args.max} nouveaux | {args.rate} appels/s\n')

    limiteur = Limiteur(args.rate)

    file = deque([args.steamid])
    vus.add(args.steamid)

    nouveaux = 0
    lues = 0
    fermees = 0
    tampon = []

    try:
        while file and nouveaux < args.max:
            amis = getAmis(file.popleft(), cle, limiteur)
            lues += 1

            if amis is None:
                fermees += 1
            else:
                for ami in amis:
                    if ami in vus:
                        continue

                    vus.add(ami)
                    file.append(ami)
                    tampon.append((ami, 'inconnu', time.time()))
                    nouveaux += 1

                    if nouveaux >= args.max:
                        break

            if len(tampon) >= 1000:
                cx.executemany('INSERT OR IGNORE INTO joueurs '
                               '(steamid, statut, maj_le) VALUES (?,?,?)', tampon)
                cx.commit()
                tampon = []

            print(f'  {lues} listes lues | {nouveaux}/{args.max} nouveaux | '
                  f'{fermees} fermees | file {len(file)} | {limiteur.debitReel():.1f}/s')

    except KeyboardInterrupt:
        print('\nArret demande.')

    if tampon:
        cx.executemany('INSERT OR IGNORE INTO joueurs '
                       '(steamid, statut, maj_le) VALUES (?,?,?)', tampon)

    cx.commit()

    print(f'\n{lues} listes lues, {fermees} fermees, {nouveaux} nouveaux joueurs')

    for statut, n in cx.execute('SELECT statut, count(*) FROM joueurs '
                                'GROUP BY statut ORDER BY 2 DESC'):
        print(f'   {statut:8}: {n}')

    cx.close()


if __name__ == '__main__':
    main()
