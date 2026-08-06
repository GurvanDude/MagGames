"""
Remplace la table jeux par le dataset public FronkonGames.

Source : https://huggingface.co/datasets/FronkonGames/steam-games-dataset
        (games.json, ~137 000 jeux, licence MIT, mis a jour tous les 3-5 jours)

Pourquoi ce dataset plutot que l'API Steam : il apporte en un telechargement
ce qui demanderait 26 h d'appels, et il contient les TAGS communautaires que
l'API Steam n'expose nulle part.

Le fichier fait ~870 Mo, on le lit en streaming (ijson) pour ne pas charger
900 Mo de JSON en memoire.

    python scripts/importe_catalogue.py --json data/steam_games.json
"""
import argparse
import time

import ijson

import db as base

LOT = 5000


COLONNES = ('appid', 'nom', 'description', 'description_longue', 'date_sortie',
            'prix', 'developpeur', 'editeur', 'genre', 'categories', 'tags',
            'langues', 'plateformes', 'metacritic', 'note_utilisateurs',
            'avis_positifs', 'avis_negatifs', 'recommandations',
            'proprietaires', 'temps_moyen_minutes', 'temps_median_minutes',
            'joueurs_simultanes', 'succes', 'nb_dlc', 'age_minimum',
            'image', 'site_web')


def joindre(valeur, sep=', '):
    """Une liste du JSON -> une chaine. Les tags sont parfois un dict."""
    if not valeur:
        return ''

    if isinstance(valeur, dict):
        # {nom: votes} trie par votes decroissants
        ordonnes = sorted(valeur.items(), key=lambda t: t[1], reverse=True)
        return '|'.join(f'{n}:{v}' for n, v in ordonnes)

    if isinstance(valeur, list):
        return sep.join(str(v) for v in valeur)

    return str(valeur)


def entier(valeur):
    try:
        return int(valeur)
    except (TypeError, ValueError):
        return 0


def ligne(appid, j):
    plateformes = [n for n in ('windows', 'mac', 'linux') if j.get(n)]

    return (
        int(appid),
        j.get('name', ''),
        (j.get('short_description') or '').replace('\n', ' ').strip(),
        (j.get('about_the_game') or '').replace('\n', ' ').strip(),
        j.get('release_date', ''),
        float(j.get('price') or 0),
        joindre(j.get('developers')),
        joindre(j.get('publishers')),
        joindre(j.get('genres')),
        joindre(j.get('categories'), '|'),
        joindre(j.get('tags')),
        joindre(j.get('supported_languages')),
        '|'.join(plateformes),
        entier(j.get('metacritic_score')),
        entier(j.get('user_score')),
        entier(j.get('positive')),
        entier(j.get('negative')),
        entier(j.get('recommendations')),
        j.get('estimated_owners', ''),
        entier(j.get('average_playtime_forever')),
        entier(j.get('median_playtime_forever')),
        entier(j.get('peak_ccu')),
        entier(j.get('achievements')),
        entier(j.get('dlc_count')),
        entier(j.get('required_age')),
        j.get('header_image', ''),
        j.get('website', ''),
    )


def main():
    parser = argparse.ArgumentParser(description='Importe le catalogue public')
    parser.add_argument('--json', default='data/steam_games.json')
    parser.add_argument('--db', default=None)
    args = parser.parse_args()

    chemin = base.RACINE / args.json

    if not chemin.exists():
        print(f'Erreur : {chemin} introuvable')
        return

    cx = base.connexion(args.db)

    # On garde la trace des appid connus des bibliotheques : le dataset
    # exclut les DLC, or des joueurs en possedent. Sans ca, la jointure
    # bibliotheque -> jeux perdrait ces lignes.
    possedes = {r[0] for r in cx.execute('SELECT DISTINCT appid FROM bibliotheque')}
    print(f'{len(possedes)} appid presents dans les bibliotheques')

    print('Remplacement de la table jeux...')
    cx.executescript('DROP TABLE IF EXISTS jeux;' + base.SCHEMA_JEUX +
                     'CREATE INDEX IF NOT EXISTS idx_jeux_nom ON jeux(nom);')
    cx.commit()

    sql = (f'INSERT OR REPLACE INTO jeux ({", ".join(COLONNES)}) '
           f'VALUES ({", ".join("?" * len(COLONNES))})')

    n = 0
    tampon = []
    vus = set()
    d = time.monotonic()

    # Streaming : le fichier fait ~870 Mo, le charger d'un coup prendrait
    # plusieurs Go de memoire.
    with open(chemin, 'rb') as f:
        cx.execute('BEGIN')

        for appid, jeu in ijson.kvitems(f, ''):
            tampon.append(ligne(appid, jeu))
            vus.add(int(appid))
            n += 1

            if len(tampon) >= LOT:
                cx.executemany(sql, tampon)
                tampon = []
                cx.commit()
                cx.execute('BEGIN')
                print(f'  {n} jeux ({time.monotonic() - d:.0f}s)')

        if tampon:
            cx.executemany(sql, tampon)

        cx.commit()

    print(f'\n{n} jeux importes en {time.monotonic() - d:.0f}s')

    # Les appid possedes mais absents du dataset (DLC, jeux retires) sont
    # crees vides, pour que les jointures continuent de fonctionner.
    manquants = possedes - vus

    if manquants:
        cx.executemany('INSERT OR IGNORE INTO jeux (appid) VALUES (?)',
                       [(a,) for a in manquants])
        cx.commit()
        print(f'{len(manquants)} appid possedes mais absents du dataset, '
              f'crees vides (DLC, jeux retires)')

    total = cx.execute('SELECT count(*) FROM jeux').fetchone()[0]
    avecTags = cx.execute('SELECT count(*) FROM jeux WHERE tags != ""').fetchone()[0]
    avecDesc = cx.execute('SELECT count(*) FROM jeux WHERE description != ""').fetchone()[0]

    print(f'\n  jeux         : {total}')
    print(f'  avec tags    : {avecTags}')
    print(f'  avec descr.  : {avecDesc}')

    cx.close()


if __name__ == '__main__':
    main()
