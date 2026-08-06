"""
4/5 - Trier les profils publics.

Prend les joueurs au statut 'inconnu' et les passe en 'public' ou 'prive'.
Un appel teste 100 SteamID d'un coup : verifier 100 000 joueurs ne coute
que 1000 appels.

Relancer ne refait jamais le meme travail, seuls les 'inconnu' sont testes.

    python scripts/verifie_ids.py
    python scripts/verifie_ids.py --max 50000
"""
import argparse
import time
from concurrent.futures import ThreadPoolExecutor

import db as base
from steam_api import PAQUET, Limiteur, getCle, verifierPaquet


def main():
    parser = argparse.ArgumentParser(description='Trier les profils publics')
    parser.add_argument('--db', default=None)
    parser.add_argument('--max', type=int, default=0, help='ID a tester (0 = tous)')
    parser.add_argument('--rate', type=float, default=3.0, help='appels par seconde')
    parser.add_argument('--workers', type=int, default=2, help='paquets en parallele')
    args = parser.parse_args()

    cle = getCle()

    if not cle:
        print("Erreur : STEAM_API absent du fichier .env")
        return

    cx = base.connexion(args.db)

    sql = "SELECT steamid FROM joueurs WHERE statut = 'inconnu'"

    if args.max:
        sql += f' LIMIT {int(args.max)}'

    ids = [r[0] for r in cx.execute(sql)]

    if not ids:
        print('Aucun joueur a verifier.')
        cx.close()
        return

    paquets = [ids[i:i + PAQUET] for i in range(0, len(ids), PAQUET)]

    print(f'{len(ids)} joueurs a verifier ({len(paquets)} paquets de {PAQUET})')
    print(f'{args.rate} appels/s | ~{len(paquets) / args.rate / 60:.0f} min\n')

    limiteur = Limiteur(args.rate)

    publics = 0
    prives = 0

    def traiter(paquet):
        return paquet, verifierPaquet(paquet, cle, limiteur)

    try:
        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            # Seul le thread principal ecrit : SQLite n'aime pas la concurrence
            for i, (paquet, trouves) in enumerate(pool.map(traiter, paquets), 1):
                ouverts = set(trouves)
                maintenant = time.time()

                cx.executemany(
                    'UPDATE joueurs SET statut = ?, maj_le = ? WHERE steamid = ?',
                    [('public' if s in ouverts else 'prive', maintenant, s)
                     for s in paquet])

                publics += len(ouverts)
                prives += len(paquet) - len(ouverts)

                if i % 20 == 0 or i == len(paquets):
                    cx.commit()
                    print(f'  {i}/{len(paquets)} paquets | {publics} publics | '
                          f'{prives} prives | {limiteur.debitReel():.1f}/s')

    except KeyboardInterrupt:
        print('\nArret demande, tout ce qui est fait est enregistre.')

    cx.commit()

    print(f'\n{limiteur.appels} appels, {limiteur.freinages} freinage(s) sur 429')

    for statut, n in cx.execute('SELECT statut, count(*) FROM joueurs '
                                'GROUP BY statut ORDER BY 2 DESC'):
        print(f'   {statut:8}: {n}')

    cx.close()


if __name__ == '__main__':
    main()
