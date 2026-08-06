# MagGames

Plateforme de découverte, comparaison et suivi de jeux vidéo steam (prix, promotions, popularité, avis), permettant à l'utilisateur de se constituer une liste de jeux à suivre adaptée à son profil er à son budget.

## Team Max Mag
- Maxime DANINO
- Awadi BEDJA
- Gurvan GODIN

## Stack technique
- **Backend** : Django + Django REST Framework
- **Données** : Steam Web API, API du store Steam, dataset FronkonGames
- **Frontend** : React (TypeScript)

---

# Installation

### Backend

```powershell
python -m venv .venv
.venv/Scripts/python.exe -m pip install -r requirements.txt
```

Créer un fichier `.env` à la racine (il n'est pas versionné) :

```
STEAM_API=votre_cle_ici
```

La clé se récupère sur https://steamcommunity.com/dev/apikey

Puis créer la base Django :

```powershell
.venv/Scripts/python.exe backend/manage.py migrate
```

### Frontend

```powershell
cd frontend
npm install
```

### Lancer le projet

```powershell
.venv/Scripts/python.exe backend/manage.py runserver
```

```powershell
cd frontend
npm run dev
```

---

# API du site

| Méthode | URL | Description |
|---|---|---|
| GET | `/api/auth/steam/login/` | Redirige vers la page de connexion Steam |
| GET | `/api/auth/steam/callback/` | Retour de Steam, crée le profil et ouvre la session |

La connexion utilise **Steam OpenID** : on ne demande jamais le mot de passe de
l'utilisateur, c'est Steam qui l'authentifie et nous renvoie son SteamID.
Le SteamID est ensuite gardé dans la session Django.

---

# Les données

La collecte vit dans `scripts/` et remplit une base SQLite : `data/maggames.db`.

## Les APIs utilisées

### 1. Steam Web API — `api.steampowered.com`

Nécessite la clé `STEAM_API`. **Limite : 100 000 appels par jour et par clé**
([conditions officielles](https://steamcommunity.com/dev/apiterms)).

| endpoint | usage | coût |
|---|---|---|
| `ISteamUser/GetFriendList` | liste d'amis d'un joueur | 1 appel → ~300 ID |
| `ISteamUser/GetPlayerSummaries` | profil public ou non | 1 appel → **100 joueurs** |
| `IPlayerService/GetOwnedGames` | bibliothèque d'un joueur | 1 appel → 1 joueur |

Cadences **mesurées**, pas théoriques :

- `GetFriendList` : 5/s sans problème
- `GetPlayerSummaries` : 3/s
- `GetOwnedGames` : **8/s tient (2 % d'échecs), 15/s non (27 %), 30/s non (47 %)**

Au-delà du seuil, Steam **coupe les connexions** au lieu de renvoyer un 429.
Le compteur `freinage(s)` reste donc à 0 alors que tout part en vrille : c'est
la colonne `echecs` qu'il faut surveiller.

⚠️ Un appel raté consomme quand même le quota.

### 2. API du store Steam — `store.steampowered.com/api/appdetails`

Pas de clé. Donne la fiche complète d'un jeu (description, genres, catégories,
prix, date, Metacritic). **Un seul jeu par appel**, `appids=1,2,3` renvoie `null`.

Débit soutenable mesuré : **~2/s**. Elle tolère des rafales de ~150 appels puis
étrangle. Non utilisée dans la collecte, le dataset ci-dessous la remplace.

### 3. Dataset FronkonGames — Hugging Face

https://huggingface.co/datasets/FronkonGames/steam-games-dataset

**137 000 jeux, licence MIT, mis à jour tous les 3-5 jours.** Remplace 26 h
d'appels au store par un téléchargement de 30 secondes, et contient les **tags
communautaires** que l'API Steam n'expose nulle part.

Seul `games.json` est maintenu — les versions CSV et parquet du même dataset
ne sont plus mises à jour.

## La base : `data/maggames.db`

Trois tables.

```
jeux (145 000)
  appid  nom  description  description_longue  date_sortie  prix
  developpeur  editeur  genre  categories  tags  langues  plateformes
  metacritic  note_utilisateurs  avis_positifs  avis_negatifs
  recommandations  proprietaires  temps_moyen_minutes  temps_median_minutes
  joueurs_simultanes  succes  nb_dlc  age_minimum  image  site_web

joueurs (1 112 000)
  steamid  statut  maj_le
  statut = inconnu | public | prive

bibliotheque (5 449 000)
  source  steamid  appid  minutes_jouees  minutes_2semaines
```

Le lien est l'`appid` : `bibliotheque.appid` → `jeux.appid`. Les jeux possédés
mais absents du dataset (DLC, jeux retirés) existent en ligne vide, pour qu'une
jointure ne perde jamais de ligne.

## Initialiser la base

**1. Le catalogue** (~1 min, aucun quota consommé)

```powershell
.venv/Scripts/python.exe scripts/telecharge_catalogue.py
```

```powershell
.venv/Scripts/python.exe scripts/importe_catalogue.py
```

Le premier télécharge `games.json` (~870 Mo) dans `data/`. Le second remplace
la table `jeux` et la remplit en 30 secondes. À relancer quand tu veux
rafraîchir prix et nouveautés.

**2. Trouver des joueurs** (facultatif, il y en a déjà 1,1 million en base)

```powershell
.venv/Scripts/python.exe scripts/cherche_ids.py 76561198003378041 --max 100000
```

**3. Trier les profils publics**

```powershell
.venv/Scripts/python.exe scripts/verifie_ids.py --max 50000
```

100 joueurs par appel : vérifier 50 000 joueurs coûte 500 appels.

**4. Récupérer les bibliothèques**

```powershell
.venv/Scripts/python.exe scripts/recolte_jeux.py --source source2 --max 20000
```

Un appel par joueur : 20 000 joueurs = 20 % du quota quotidien, ~40 min à 8/s.

## Reprise automatique

Tous les scripts reprennent où ils se sont arrêtés, sans option à passer :

- `cherche_ids` n'ajoute que les SteamID absents de `joueurs`
- `verifie_ids` ne teste que les `statut = 'inconnu'`
- `recolte_jeux` ne prend que les publics sans bibliothèque
- `importe_catalogue` reconstruit la table à neuf

Un `Ctrl+C` est intercepté : ce qui est collecté est enregistré, le reste
repassera. Un **échec** (réseau, quota) ne marque rien en base, donc le joueur
est automatiquement réessayé au lancement suivant. Un profil **privé**, lui,
est marqué définitivement et n'est plus jamais redemandé.

## Structure

```
MagGames/
├── backend/            Django : config/ et steam/ (connexion OpenID)
├── frontend/           React + Vite + TypeScript
├── scripts/
│   ├── steam_api.py            appels HTTP, limiteur de cadence, gestion des 429
│   ├── db.py                   schéma et connexion SQLite
│   ├── telecharge_catalogue.py 1. télécharge games.json
│   ├── importe_catalogue.py    2. remplit la table jeux
│   ├── cherche_ids.py          3. trouve des SteamID
│   ├── verifie_ids.py          4. trie les profils publics
│   └── recolte_jeux.py         5. récupère les bibliothèques
├── data/               maggames.db (non versionné)
├── requirements.txt
└── .env                clé d'API (non versionné)
```

## Avancement

- [x] Connexion Steam (OpenID)
- [x] Catalogue des jeux avec tags et descriptions
- [x] Collecte des bibliothèques de joueurs
- [ ] Endpoint bibliothèque côté Django
- [ ] Affichage côté React
- [ ] Moteur de recommandation
