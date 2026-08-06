# Modèle de recommandation

Recommander des jeux à un utilisateur à partir de sa bibliothèque Steam (jeux possédés + temps de jeu), en s'appuyant sur les jeux similaires possédés par d'autres joueurs et sur le contenu des jeux (genres, tags, prix...).

## Données

Tout se trouve dans `data/` (non versionné, voir `.gitignore`).

### Fichiers actuels (utilisés pour l'entraînement)

| Fichier | Lignes | Colonnes | Origine |
|---|---|---|---|
| `joueurs.csv` | ~1,1M | `steamid, statut, maj_le` | Crawl Steam Web API (collègue) |
| `bibliotheque.csv` | ~15,5M | `steamid, appid, minutes_jouees, minutes_2semaines, source` | Crawl Steam Web API (`GetOwnedGames`), plusieurs sources fusionnées |
| `jeux.csv` | ~145 758 | `appid, nom, description, description_longue, date_sortie, prix, developpeur, editeur, genre, categories, tags, langues, plateformes, metacritic, note_utilisateurs, avis_positifs, avis_negatifs, recommandations, proprietaires, temps_moyen_minutes, temps_median_minutes, joueurs_simultanes, succes, nb_dlc, age_minimum, image, site_web` | Dataset [FronkonGames/steam-games-dataset](https://huggingface.co/datasets/FronkonGames/steam-games-dataset) (Hugging Face, licence MIT) |

`statut` dans `joueurs.csv` vaut `public` ou `prive` — les profils privés n'ont pas d'entrée dans `bibliotheque.csv` (l'API Steam ne renvoie rien pour eux) et sont exclus de l'entraînement.

## Scripts de collecte

- `collect_owned_games.py` — collecte les jeux possédés + temps de jeu par utilisateur via `GetOwnedGames` (Steam Web API). Resumable (relit le CSV de sortie pour ne pas retraiter les steamids déjà faits).
- `collect_game_metadata.py` — collecte les métadonnées d'un jeu (genres, catégories, prix, date de sortie, développeur/éditeur) via l'API Store Steam (`appdetails`). Superseded par `jeux.csv`, gardé au cas où on ait besoin de compléter des `appid` absents du dataset Hugging Face.

## Nettoyage prévu

- Exclure les joueurs `statut=prive` (pas de bibliothèque).
- Dédupliquer `bibliotheque.csv` sur `(steamid, appid)` — plusieurs `source` peuvent se chevaucher.
- Parser les champs multi-valeurs de `jeux.csv` (`genre`, `categories`, `tags` au format `tag:nb_votes`, `plateformes`).
- Gérer les valeurs manquantes (`metacritic=0` ambigu : vraie note ou absence de note → prévoir un flag `has_metacritic`).
- Pondérer le signal d'interaction avec `log(1 + minutes_jouees)` plutôt que la valeur brute (évite qu'un très gros joueur sur un seul jeu écrase le signal).

## Modèle retenu : Two-Tower

Un réseau encode l'utilisateur (moyenne pondérée des embeddings des jeux possédés), un autre encode le jeu (genres, tags, prix, metacritic...), le score est le produit scalaire des deux embeddings.

Pourquoi ce choix plutôt qu'un collaboratif filtering pur (ALS/LightGCN) :
- Gère le cold-start (nouveau jeu ou nouvel utilisateur) grâce au contenu, pas seulement à l'historique d'interactions.
- Scalable à l'inférence : les embeddings des ~145K jeux sont précalculés une fois et indexés (FAISS), seul l'embedding utilisateur est calculé à la demande.

Baseline de comparaison : recommandation par popularité, et LightGCN (pur collaboratif) pour vérifier l'apport réel du contenu.

Évaluation : split leave-one-out par utilisateur (pas de split temporel possible, `bibliotheque.csv` n'a pas de date par interaction), métriques Recall@K / NDCG@K.

## Avancement

- [x] Collecte des joueurs et de leurs bibliothèques
- [x] Récupération des métadonnées jeux (dataset Hugging Face)
- [ ] Nettoyage et feature engineering
- [ ] Implémentation du modèle Two-Tower (PyTorch)
- [ ] Entraînement et évaluation
- [ ] Export des embeddings + indexation FAISS
- [ ] Intégration à l'API Django (endpoint de recommandation)
