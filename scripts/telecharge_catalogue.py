"""
1/5 - Telecharge le catalogue Steam public.

Source : https://huggingface.co/datasets/FronkonGames/steam-games-dataset
         games.json, ~137 000 jeux, licence MIT, mis a jour tous les 3-5 jours

C'est le seul fichier du projet mis a jour regulierement : les versions CSV
et parquet du meme dataset ne sont plus maintenues.

Ce dataset remplace 26 h d'appels a l'API du store, et il contient les TAGS
communautaires que l'API Steam n'expose nulle part.

    python scripts/telecharge_catalogue.py
"""
import argparse
import time

import requests

from steam_api import RACINE

URL = ('https://huggingface.co/datasets/FronkonGames/steam-games-dataset/'
       'resolve/main/games.json')


def main():
    parser = argparse.ArgumentParser(description='Telecharge le catalogue Steam')
    parser.add_argument('--out', default='data/steam_games.json')
    parser.add_argument('--url', default=URL)
    args = parser.parse_args()

    sortie = RACINE / args.out
    sortie.parent.mkdir(parents=True, exist_ok=True)

    print(f'Telechargement depuis huggingface.co\n  vers {sortie}\n')

    debut = time.monotonic()
    recu = 0
    palier = 0

    with requests.get(args.url, stream=True, timeout=300) as r:
        r.raise_for_status()

        with open(sortie, 'wb') as f:
            for morceau in r.iter_content(1 << 20):
                f.write(morceau)
                recu += len(morceau)

                # un point tous les 100 Mo
                if recu // (100 << 20) > palier:
                    palier = recu // (100 << 20)
                    print(f'  {recu / 1024 / 1024:.0f} Mo '
                          f'({time.monotonic() - debut:.0f}s)')

    print(f'\n{recu / 1024 / 1024:.0f} Mo en {time.monotonic() - debut:.0f}s')
    print('Lance maintenant : python scripts/importe_catalogue.py')


if __name__ == '__main__':
    main()
