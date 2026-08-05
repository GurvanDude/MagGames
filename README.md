# MagGames

Plateforme de découverte, comparaison et suivi de jeux vidéo steam (prix, promotions, popularité, avis), permettant à l'utilisateur de se constituer une liste de jeux à suivre adaptée à son profil er à son budget.

## Team Max Mag
- Maxime DANINO
- Awadi BEDJA
- Gurvan GODIN

## Stack technique
- **Backend** : Django + Django REST Framework
- **Données** : Steam Web API
- **Frontend** : React (TypeScript)

## Installation

### Backend

```powershell
python -m venv .venv
.venv/Scripts/python.exe -m pip install -r requirements.txt
```

Créer un fichier `.env` à la racine du projet (il n'est pas versionné) :

```
STEAM_API=votre_cle_ici
```

La clé se récupère sur https://steamcommunity.com/dev/apikey

Puis créer la base de données :

```powershell
.venv/Scripts/python.exe backend/manage.py migrate
```

Le fichier `backend/db.sqlite3` est généré par cette commande. Il n'est pas versionné :
chacun a la sienne, et on peut la supprimer et relancer `migrate` à tout moment.

### Frontend

```powershell
cd frontend
npm install
```

## Lancer le projet

Backend (port 8000) :

```powershell
.venv/Scripts/python.exe backend/manage.py runserver
```

Frontend (port 5173) :

```powershell
cd frontend
npm run dev
```

## API

| Méthode | URL | Description |
|---|---|---|
| GET | `/api/auth/steam/login/` | Redirige vers la page de connexion Steam |
| GET | `/api/auth/steam/callback/` | Retour de Steam, crée le profil et ouvre la session |

La connexion utilise **Steam OpenID** : on ne demande jamais le mot de passe de
l'utilisateur, c'est Steam qui l'authentifie et nous renvoie son SteamID.
Le SteamID est ensuite gardé dans la session Django.

## Structure

```
MagGames/
├── backend/
│   ├── config/          paramètres du projet (settings.py, urls.py)
│   ├── steam/           connexion Steam et profil joueur
│   └── manage.py
├── frontend/            React + Vite + TypeScript
├── requirements.txt
└── .env                 clés d'API (non versionné)
```

## Avancement

- [x] Connexion Steam (OpenID)
- [ ] Endpoint bibliothèque de jeux
- [ ] Affichage de la bibliothèque côté React
- [ ] Moteur de recommandation
