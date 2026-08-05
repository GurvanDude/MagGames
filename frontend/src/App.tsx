import { useEffect, useState } from 'react'
import './App.css'

const API_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

type View = 'home' | 'library' | 'suggestions'

type SteamProfile = {
  steamid: string
  personaName: string
  avatar: string
}

type OwnedGame = {
  appid: number
  name: string
  image: string
  playtime: number
}

type LibraryResponse = {
  games: OwnedGame[]
  count: number
  page: number
  total_pages: number
  next: string | null
  previous: string | null
}

const errorMessages: Record<string, string> = {
  connexion: 'La connexion Steam a echoue. Relance la connexion pour reessayer.',
  'cle-steam': 'La cle API Steam manque dans le fichier .env du backend.',
  'api-steam': 'Steam a refuse ou mal repondu pendant la recuperation du profil.',
  'profil-steam': 'Steam a valide la connexion, mais aucun profil joueur n a ete renvoye.',
}

function formatPlaytime(minutes: number) {
  if (minutes < 60) {
    return `${minutes} min`
  }

  return `${Math.round(minutes / 60)} h`
}

function App() {
  const params = new URLSearchParams(window.location.search)
  const isConnectedFromSteam = params.get('connecte') === '1'
  const errorCode = params.get('erreur')
  const errorMessage = errorCode ? errorMessages[errorCode] : null

  const [view, setView] = useState<View>('home')
  const [profile, setProfile] = useState<SteamProfile | null>(null)
  const [profileError, setProfileError] = useState<string | null>(null)
  const [library, setLibrary] = useState<LibraryResponse | null>(null)
  const [isLibraryLoading, setIsLibraryLoading] = useState(false)
  const [libraryError, setLibraryError] = useState<string | null>(null)

  const isConnected = Boolean(profile)

  function loginWithSteam() {
    window.location.href = `${API_URL}/api/auth/steam/login/`
  }

  useEffect(() => {
    if (!isConnectedFromSteam || profile) {
      return
    }

    async function loadProfile() {
      try {
        const response = await fetch(`${API_URL}/api/auth/steam/me/`, {
          credentials: 'include',
        })
        const data = await response.json()

        if (!response.ok) {
          throw new Error(data.detail ?? 'Impossible de recuperer le profil Steam.')
        }

        setProfile(data)
      } catch (error) {
        setProfileError(
          error instanceof Error
            ? error.message
            : 'Impossible de recuperer le profil Steam.',
        )
      }
    }

    void loadProfile()
  }, [isConnectedFromSteam, profile])

  useEffect(() => {
    if (view !== 'library' || library || isLibraryLoading) {
      return
    }

    async function loadLibrary() {
      setIsLibraryLoading(true)
      setLibraryError(null)

      try {
        const response = await fetch(`${API_URL}/api/library/`, {
          credentials: 'include',
        })
        const data = await response.json()

        if (!response.ok) {
          throw new Error(data.detail ?? 'Impossible de charger la bibliotheque.')
        }

        setLibrary(data)
      } catch (error) {
        setLibraryError(
          error instanceof Error
            ? error.message
            : 'Impossible de charger la bibliotheque.',
        )
      } finally {
        setIsLibraryLoading(false)
      }
    }

    void loadLibrary()
  }, [isLibraryLoading, library, view])

  return (
    <main className={view === 'home' ? 'home-page' : 'app-shell'}>
      {view === 'home' && (
        <section className="home-panel" aria-labelledby="home-title">
          <p className="eyebrow">MagGames</p>
          <h1 id="home-title">Trouve ton prochain jeu Steam</h1>
          <p className="intro">
            Connecte ton compte Steam pour recuperer ta bibliotheque et preparer
            des recommandations basees sur tes vrais jeux.
          </p>

          {!isConnected && (
            <button className="steam-button" type="button" onClick={loginWithSteam}>
              Se connecter avec Steam
            </button>
          )}

          {profile && (
            <div className="welcome-block">
              <div className="profile-row">
                <img src={profile.avatar} alt="" />
                <p>Bienvenue {profile.personaName}</p>
              </div>
              <div className="action-row">
                <button
                  className="steam-button"
                  type="button"
                  onClick={() => setView('library')}
                >
                  Acceder a la library
                </button>
                <button
                  className="secondary-button"
                  type="button"
                  onClick={() => setView('suggestions')}
                >
                  Acceder aux suggestions
                </button>
              </div>
            </div>
          )}

          {errorMessage && <p className="status error">{errorMessage}</p>}
          {profileError && <p className="status error">{profileError}</p>}
        </section>
      )}

      {view === 'library' && (
        <section className="library-page" aria-labelledby="library-title">
          <header className="page-header">
            <div>
              <p className="eyebrow">Bibliotheque Steam</p>
              <h1 id="library-title">Tes jeux Steam</h1>
              <p className="intro">
                Premiere recuperation reelle depuis ton compte Steam.
              </p>
            </div>
            <button className="secondary-button" type="button" onClick={() => setView('home')}>
              Retour accueil
            </button>
          </header>

          {isLibraryLoading && (
            <p className="status info">Chargement de ta bibliotheque...</p>
          )}
          {libraryError && <p className="status error">{libraryError}</p>}

          {library && (
            <>
              <p className="library-count">
                {library.count} jeux trouves, page {library.page} sur{' '}
                {library.total_pages}
              </p>
              <div className="game-grid">
                {library.games.map((game) => (
                  <article className="game-card" key={game.appid}>
                    <img src={game.image} alt="" />
                    <div>
                      <h2>{game.name}</h2>
                      <p>{formatPlaytime(game.playtime)} de jeu</p>
                    </div>
                  </article>
                ))}
              </div>
            </>
          )}
        </section>
      )}

      {view === 'suggestions' && (
        <section className="suggestions-page" aria-labelledby="suggestions-title">
          <header className="page-header">
            <div>
              <p className="eyebrow">Suggestions</p>
              <h1 id="suggestions-title">Recommandations</h1>
              <p className="intro">
                Cette page accueillera le moteur de recommendation base sur ta
                bibliotheque Steam.
              </p>
            </div>
            <button className="secondary-button" type="button" onClick={() => setView('home')}>
              Retour accueil
            </button>
          </header>
          <p className="empty-state">
            Les suggestions seront ajoutees apres la recuperation et
            l'exploitation de la library.
          </p>
        </section>
      )}
    </main>
  )
}

export default App
