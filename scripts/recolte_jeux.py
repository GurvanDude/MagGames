"""
5/5 - Recuperer les bibliotheques des joueurs publics.

Prend les joueurs au statut 'public' dont on n'a pas encore la bibliotheque
et enregistre leurs jeux avec le temps de jeu.

Sont sautes automatiquement :
  - ceux dont la bibliotheque est deja en base
  - ceux marques 'prive' (Steam a repondu : ils cachent leurs jeux)

Ne sont PAS sautes : ceux dont l'appel a echoue (reseau, quota). Un echec ne
laisse aucune trace, donc ils repassent au lancement suivant.

Un appel par joueur : c'est la seule etape qui consomme le quota Steam de
100 000 appels/jour. Cadence mesuree : 8/s tient (2% d'echecs), 15/s non.

    python scripts/recolte_jeux.py --source source2 --max 20000
"""
import argparse
from concurrent.futures import ThreadPoolExecutor

import db as base
from steam_api import Limiteur, getCle, getJeux


def main():
    parser = argparse.ArgumentParser(description='Bibliotheques des joueurs')
    parser.add_argument('--db', default=None)
    parser.add_argument('--source', default='source2', help='nom du lot')
    parser.add_argument('--max', type=int, default=0, help='joueurs (0 = tous)')
    parser.add_argument('--rate', type=float, default=8.0, help='appels par seconde')
    parser.add_argument('--workers', type=int, default=6, help='joueurs en parallele')
    args = parser.parse_args()

    cle = getCle()

    if not cle:
        print("Erreur : STEAM_API absent du fichier .env")
        return

    cx = base.connexion(args.db)

    # Publics dont la bibliotheque manque encore. Les echecs precedents
    # n'ont rien ecrit, donc ils ressortent naturellement ici.
    sql = """
        SELECT steamid FROM joueurs
        WHERE statut = 'public'
          AND steamid NOT IN (SELECT DISTINCT steamid FROM bibliotheque)
    """

    if args.max:
        sql += f' LIMIT {int(args.max)}'

    ids = [r[0] for r in cx.execute(sql)]

    print(f'{len(ids)} joueurs a collecter | source "{args.source}"')

    if not ids:
        print('Rien a faire.')
        cx.close()
        return

    print(f'{args.rate} appels/s | {args.workers} workers | '
          f'~{len(ids) / args.rate / 3600:.1f} h\n')

    limiteur = Limiteur(args.rate)

    ouverts = 0
    fermes = 0
    echecs = 0
    lignes = 0

    def traiter(steamid):
        return steamid, getJeux(steamid, cle, limiteur)

    try:
        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            # Seul le thread principal ecrit : SQLite n'aime pas la
            # concurrence, et pool.map rend les resultats dans l'ordre.
            for i, (steamid, jeux) in enumerate(pool.map(traiter, ids), 1):
                if jeux is None:
                    # Echec : on ne marque rien, il repassera
                    echecs += 1
                elif jeux == 'prive':
                    fermes += 1
                    base.majJoueur(cx, steamid, 'prive')
                else:
                    ouverts += 1
                    base.majJoueur(cx, steamid, 'public')
                    base.majBibliotheque(cx, args.source, steamid, [
                        (j['appid'], j.get('playtime_forever', 0),
                         j.get('playtime_2weeks', 0)) for j in jeux])
                    lignes += len(jeux)

                if i % 50 == 0 or i == len(ids):
                    cx.commit()
                    print(f'  {i}/{len(ids)} | {ouverts} bibliotheques | '
                          f'{fermes} prives | {echecs} echecs | {lignes} lignes | '
                          f'{limiteur.debitReel():.1f}/s')

    except KeyboardInterrupt:
        print('\nArret demande, tout ce qui est fait est enregistre.')

    cx.commit()

    print(f'\n{limiteur.appels} appels, {limiteur.freinages} freinage(s) sur 429')
    print(f'{ouverts} bibliotheques, {fermes} prives, {echecs} echecs (a retenter)')
    print(f'total en base : '
          f'{cx.execute("SELECT count(DISTINCT steamid) FROM bibliotheque").fetchone()[0]} '
          f'joueurs, {cx.execute("SELECT count(*) FROM bibliotheque").fetchone()[0]} lignes')

    cx.close()


if __name__ == '__main__':
    main()
