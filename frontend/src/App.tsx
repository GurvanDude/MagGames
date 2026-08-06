import { useEffect, useState } from 'react'
import type { ReactNode, SyntheticEvent } from 'react'
import { AppHeader } from './components/AppHeader'
import type { AppView } from './components/AppHeader'
import logoUrl from './assets/maggames-logo.png'
import './App.css'

const API_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

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
  total_count: number
  total_playtime: number
  page: number
  total_pages: number
  next: string | null
  previous: string | null
}

type GameDetails = {
  appid: number
  name: string
  image: string
  description: string
  release_date: string | null
  genres: string[]
  developers: string[]
  publishers: string[]
  categories: string[]
  platforms: string[]
  website: string | null
  playtime: number
  achievements: {
    obtained: number | null
    total: number | null
  }
}

const errorMessages: Record<string, string> = {
  connexion: 'La connexion Steam a echoue. Relance la connexion pour reessayer.',
  'cle-steam': 'La cle API Steam manque dans le fichier .env du backend.',
  'api-steam': 'Steam a refuse ou mal repondu pendant la recuperation du profil.',
  'profil-steam': 'Steam a valide la connexion, mais aucun profil joueur n a ete renvoye.',
}

function getViewFromPath(pathname: string): AppView {
  if (pathname === '/library') {
    return 'library'
  }

  if (pathname === '/suggestions') {
    return 'suggestions'
  }

  return 'home'
}

function getPathFromView(view: AppView) {
  return view === 'home' ? '/home' : `/${view}`
}

function formatPlaytime(minutes: number) {
  if (minutes < 60) {
    return `${minutes} min`
  }

  return `${Math.round(minutes / 60)} h`
}

function getCatalogColumnCount() {
  if (window.innerWidth <= 700) {
    return 1
  }

  if (window.innerWidth <= 1100) {
    return 3
  }

  if (window.innerWidth <= 1499) {
    return 4
  }

  return 5
}

function splitIntoRows<T>(items: T[], rowSize: number) {
  const rows: T[][] = []

  for (let index = 0; index < items.length; index += rowSize) {
    rows.push(items.slice(index, index + rowSize))
  }

  return rows
}

function LibrarySymbol() {
  return (
    <svg className="module-symbol" viewBox="0 0 360 260" aria-hidden="true">
      <g className="hud-grid-blue">
        <circle cx="180" cy="130" r="82" />
        <circle cx="180" cy="130" r="60" />
        <path d="M180 34v44M180 182v44M86 130h42M232 130h42" />
        <path d="M98 64h52l30 30h82M98 196h52l30-30h82" />
        <path d="M76 77h45M76 183h45M239 77h45M239 183h45" />
      </g>
      <g className="archive-icon">
        <path d="M132 104h96l13 16v53H119v-53Z" />
        <path d="M132 104h96v28h-96Z" />
        <path d="M146 145h68M146 159h46" />
        <path d="M156 94h72l15 18" />
        <path d="M144 84h72l14 16" />
      </g>
      <g className="library-slots">
        <path d="M127 120h106M127 173h106" />
        <path d="M160 132v41M202 132v41" />
      </g>
      <g className="node node-a">
        <rect x="44" y="52" width="58" height="42" rx="6" />
        <path d="M60 73h22M71 62v22M84 69h4M92 75h4" />
      </g>
      <g className="node node-b">
        <rect x="258" y="52" width="58" height="42" rx="6" />
        <path d="M274 73h22M285 62v22M298 69h4M306 75h4" />
      </g>
      <g className="node node-c">
        <rect x="44" y="166" width="58" height="42" rx="6" />
        <path d="M60 187h22M71 176v22M84 183h4M92 189h4" />
      </g>
      <g className="node node-d">
        <rect x="258" y="166" width="58" height="42" rx="6" />
        <path d="M274 187h22M285 176v22M298 183h4M306 189h4" />
      </g>
    </svg>
  )
}

function SuggestionsSymbol() {
  return (
    <svg className="module-symbol" viewBox="0 0 360 260" aria-hidden="true">
      <g className="hud-grid-red">
        <circle cx="180" cy="130" r="82" />
        <circle cx="180" cy="130" r="58" />
        <circle cx="180" cy="130" r="34" />
        <path d="M180 31v74M180 155v74M81 130h74M205 130h74" />
        <path d="M72 62h50l58 68 68-68h43" />
        <path d="M72 198h50l58-68 68 68h43" />
      </g>
      <g className="target-core">
        <path d="M180 115v30M165 130h30" />
      </g>
      <g className="person-node n1">
        <circle cx="66" cy="64" r="21" />
        <path d="M66 55a7 7 0 1 1 0 14 7 7 0 0 1 0-14ZM54 79c3-8 21-8 24 0" />
      </g>
      <g className="person-node n2">
        <circle cx="295" cy="64" r="21" />
        <path d="M295 55a7 7 0 1 1 0 14 7 7 0 0 1 0-14ZM283 79c3-8 21-8 24 0" />
      </g>
      <g className="person-node n3">
        <circle cx="66" cy="198" r="21" />
        <path d="M66 189a7 7 0 1 1 0 14 7 7 0 0 1 0-14ZM54 213c3-8 21-8 24 0" />
      </g>
      <g className="person-node n4">
        <circle cx="295" cy="198" r="21" />
        <path d="M295 189a7 7 0 1 1 0 14 7 7 0 0 1 0-14ZM283 213c3-8 21-8 24 0" />
      </g>
    </svg>
  )
}

type ModuleCardProps = {
  tone: 'blue' | 'red'
  title: string
  subtitle: string
  action: string
  symbol: ReactNode
  onClick: () => void
}

function ModuleCard({ tone, title, subtitle, action, symbol, onClick }: ModuleCardProps) {
  return (
    <button className={`module-card ${tone}`} type="button" onClick={onClick}>
      <span className="card-corner top" />
      <span className="card-corner bottom" />
      <span className="module-title">{title}</span>
      <span className="module-line" />
      <span className="module-subtitle">{subtitle}</span>
      {symbol}
      <span className="module-action">
        {action}
        <span className="module-arrow" aria-hidden="true">
          <span />
        </span>
      </span>
    </button>
  )
}

function StatChip({ label, value }: { label: string; value: string }) {
  return (
    <div className="stat-chip">
      <strong>{value}</strong>
      <span>{label}</span>
    </div>
  )
}

type GameDetailPanelProps = {
  game: OwnedGame
  details?: GameDetails
  isLoading: boolean
  error: string | null
  onClose: () => void
  onImageError: (event: SyntheticEvent<HTMLImageElement>) => void
}

function GameDetailPanel({
  game,
  details,
  isLoading,
  error,
  onClose,
  onImageError,
}: GameDetailPanelProps) {
  const achievements = details?.achievements
  const obtainedAchievements = achievements?.obtained
  const totalAchievements = achievements?.total

  return (
    <section className="game-detail-panel" aria-labelledby={`game-detail-${game.appid}`}>
      <div className="game-detail-main">
        <div className="game-detail-image">
          <img
            src={details?.image ?? game.image}
            alt=""
            onError={onImageError}
          />
        </div>
        <div className="game-detail-content">
          <div className="game-detail-heading">
            <div>
              <p className="detail-eyebrow">Fiche Steam</p>
              <h2 id={`game-detail-${game.appid}`}>{details?.name ?? game.name}</h2>
            </div>
            <button className="detail-close" type="button" aria-label="Fermer" onClick={onClose}>
              x
            </button>
          </div>

          {isLoading && <p className="detail-status">Recuperation des informations Steam...</p>}
          {error && <p className="detail-status error">{error}</p>}

          {details && (
            <>
              <p className="game-detail-description">
                {details.description || 'Aucune description disponible pour ce jeu.'}
              </p>
              <dl className="game-facts">
                <div>
                  <dt>Date de sortie</dt>
                  <dd>{details.release_date ?? 'Non renseignee'}</dd>
                </div>
                <div>
                  <dt>Studio</dt>
                  <dd>{details.developers.join(', ') || 'Non renseigne'}</dd>
                </div>
                <div>
                  <dt>Genre</dt>
                  <dd>{details.genres.join(', ') || 'Non renseigne'}</dd>
                </div>
                <div>
                  <dt>Temps de jeu</dt>
                  <dd>{formatPlaytime(details.playtime)}</dd>
                </div>
                <div>
                  <dt>Succes obtenus</dt>
                  <dd>
                    {obtainedAchievements === null || obtainedAchievements === undefined
                      ? 'Non disponible'
                      : `${obtainedAchievements} / ${totalAchievements ?? '?'} obtenus`}
                  </dd>
                </div>
              </dl>
              {details.publishers.length > 0 && (
                <p className="game-detail-meta">Editeur : {details.publishers.join(', ')}</p>
              )}
            </>
          )}
        </div>
      </div>
      <aside className="game-suggestions-slot" aria-label="Suggestions liees">
        <p className="detail-eyebrow">Suggestions liees</p>
        <h3>Bientot disponible</h3>
        <p>Les jeux proches de ce profil apparaitront ici lorsque le moteur de recommandation sera integre.</p>
      </aside>
    </section>
  )
}

function App() {
  const params = new URLSearchParams(window.location.search)
  const isConnectedFromSteam = params.get('connecte') === '1'
  const errorCode = params.get('erreur')
  const errorMessage = errorCode ? errorMessages[errorCode] : null

  const [view, setView] = useState<AppView>(() => getViewFromPath(window.location.pathname))
  const [profile, setProfile] = useState<SteamProfile | null>(null)
  const [profileError, setProfileError] = useState<string | null>(null)
  const [isProfileLoading, setIsProfileLoading] = useState(true)
  const [library, setLibrary] = useState<LibraryResponse | null>(null)
  const [isLibraryLoading, setIsLibraryLoading] = useState(false)
  const [libraryError, setLibraryError] = useState<string | null>(null)
  const [libraryPage, setLibraryPage] = useState(1)
  const [librarySearch, setLibrarySearch] = useState('')
  const [librarySearchQuery, setLibrarySearchQuery] = useState('')
  const [selectedGameId, setSelectedGameId] = useState<number | null>(null)
  const [gameDetails, setGameDetails] = useState<Record<number, GameDetails>>({})
  const [gameDetailsLoading, setGameDetailsLoading] = useState(false)
  const [gameDetailsError, setGameDetailsError] = useState<string | null>(null)
  const [catalogColumns, setCatalogColumns] = useState(getCatalogColumnCount)

  const catalogRows = library ? splitIntoRows(library.games, catalogColumns) : []

  function navigateTo(nextView: AppView) {
    const nextPath = getPathFromView(nextView)

    if (window.location.pathname !== nextPath) {
      window.history.pushState({}, '', nextPath)
    }

    setView(nextView)
  }

  function loginWithSteam() {
    window.location.href = `${API_URL}/api/auth/steam/login/`
  }

  function goToLibraryPage(nextPage: number) {
    setLibraryPage(nextPage)
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }

  function toggleGameDetails(appid: number) {
    setGameDetailsError(null)
    setSelectedGameId((current) => (current === appid ? null : appid))
  }

  async function logoutFromSteam() {
    try {
      await fetch(`${API_URL}/api/auth/steam/logout/`, {
        method: 'POST',
        credentials: 'include',
      })
    } finally {
      setProfile(null)
      setLibrary(null)
      setProfileError(null)
      setLibraryError(null)
      setLibraryPage(1)
      setSelectedGameId(null)
      navigateTo('home')
    }
  }

  function handleGameImageError(event: SyntheticEvent<HTMLImageElement>) {
    if (event.currentTarget.src !== logoUrl) {
      event.currentTarget.src = logoUrl
      event.currentTarget.classList.add('game-image-fallback')
    }
  }

  useEffect(() => {
    if (window.location.pathname === '/') {
      window.history.replaceState({}, '', '/home')
    }

    function handlePopState() {
      setView(getViewFromPath(window.location.pathname))
    }

    window.addEventListener('popstate', handlePopState)

    return () => {
      window.removeEventListener('popstate', handlePopState)
    }
  }, [])

  useEffect(() => {
    function updateCatalogColumns() {
      setCatalogColumns(getCatalogColumnCount())
    }

    window.addEventListener('resize', updateCatalogColumns)

    return () => {
      window.removeEventListener('resize', updateCatalogColumns)
    }
  }, [])

  useEffect(() => {
    const timeout = window.setTimeout(() => {
      setLibrarySearchQuery(librarySearch.trim())
      setLibraryPage(1)
    }, 300)

    return () => {
      window.clearTimeout(timeout)
    }
  }, [librarySearch])

  useEffect(() => {
    setSelectedGameId(null)
    setGameDetailsError(null)
  }, [libraryPage, librarySearchQuery])

  useEffect(() => {
    if (profile) {
      setIsProfileLoading(false)
      return
    }

    async function loadProfile() {
      try {
        const response = await fetch(`${API_URL}/api/auth/steam/me/`, {
          credentials: 'include',
        })

        if (response.status === 401) {
          return
        }

        const data = await response.json()

        if (!response.ok) {
          throw new Error(data.detail ?? 'Impossible de recuperer le profil Steam.')
        }

        setProfile(data)
      } catch (error) {
        if (isConnectedFromSteam) {
          setProfileError(
            error instanceof Error
              ? error.message
            : 'Impossible de recuperer le profil Steam.',
          )
        }
      } finally {
        setIsProfileLoading(false)
      }
    }

    void loadProfile()
  }, [isConnectedFromSteam, profile])

  useEffect(() => {
    if (!profile || selectedGameId === null || gameDetails[selectedGameId]) {
      return
    }

    const controller = new AbortController()
    let isCurrentRequest = true
    const appid = selectedGameId

    async function loadGameDetails() {
      setGameDetailsLoading(true)
      setGameDetailsError(null)

      try {
        const response = await fetch(`${API_URL}/api/library/${appid}/`, {
          credentials: 'include',
          signal: controller.signal,
        })
        const data = await response.json()

        if (!response.ok) {
          throw new Error(data.detail ?? 'Impossible de charger les details du jeu.')
        }

        if (isCurrentRequest) {
          setGameDetails((current) => ({ ...current, [appid]: data }))
        }
      } catch (error) {
        if (isCurrentRequest && !(error instanceof DOMException && error.name === 'AbortError')) {
          setGameDetailsError(
            error instanceof Error
              ? error.message
              : 'Impossible de charger les details du jeu.',
          )
        }
      } finally {
        if (isCurrentRequest) {
          setGameDetailsLoading(false)
        }
      }
    }

    void loadGameDetails()

    return () => {
      isCurrentRequest = false
      controller.abort()
    }
  }, [gameDetails, profile, selectedGameId])

  useEffect(() => {
    if (!profile) {
      return
    }

    const controller = new AbortController()
    let isCurrentRequest = true

    async function loadLibrary() {
      setIsLibraryLoading(true)
      setLibraryError(null)

      try {
        const query = new URLSearchParams({ page: String(libraryPage) })

        if (librarySearchQuery) {
          query.set('keyword', librarySearchQuery)
        }

        const response = await fetch(`${API_URL}/api/library/?${query.toString()}`, {
          credentials: 'include',
          signal: controller.signal,
        })
        const data = await response.json()

        if (!response.ok) {
          throw new Error(data.detail ?? 'Impossible de charger la bibliotheque.')
        }

        if (isCurrentRequest) {
          setLibrary(data)
        }
      } catch (error) {
        if (isCurrentRequest && !(error instanceof DOMException && error.name === 'AbortError')) {
          setLibraryError(
            error instanceof Error
              ? error.message
              : 'Impossible de charger la bibliotheque.',
          )
        }
      } finally {
        if (isCurrentRequest) {
          setIsLibraryLoading(false)
        }
      }
    }

    void loadLibrary()

    return () => {
      isCurrentRequest = false
      controller.abort()
    }
  }, [libraryPage, librarySearchQuery, profile])

  return (
    <main className={`dashboard-page view-${view}`}>
      <AppHeader
        activeView={view}
        profile={profile}
        onNavigate={navigateTo}
        onLogin={loginWithSteam}
        onLogout={logoutFromSteam}
      />

      {view === 'home' && (
        <section className="dashboard-grid" aria-labelledby="home-title">
          <div className="account-panel">
            <p className="dash-eyebrow">Bienvenue</p>
            <h1 id="home-title">{profile?.personaName ?? 'MagGames'}</h1>

            {profile ? (
              <>
                <div className="profile-card">
                  <img src={profile.avatar} alt="" />
                </div>
                <p className="connected-state">
                  <span />
                  Compte Steam connecte
                </p>
                <div className="stats-row">
                  <StatChip value={library ? String(library.total_count ?? library.count) : '...'} label="Jeux" />
                  <StatChip value={library ? formatPlaytime(library.total_playtime) : '...'} label="Heures" />
                  <StatChip value="Actif" label="Profil" />
                </div>
              </>
            ) : (
              <>
                <p className="dashboard-copy">
                  Connecte ton compte Steam pour acceder a ta library et lancer
                  les futures suggestions basees sur ton profil.
                </p>
                <button className="connect-button" type="button" onClick={loginWithSteam}>
                  Se connecter avec Steam
                </button>
              </>
            )}

            {errorMessage && <p className="status error">{errorMessage}</p>}
            {profileError && <p className="status error">{profileError}</p>}
          </div>

          <div className="modules-panel">
            <ModuleCard
              tone="blue"
              title="Library"
              subtitle="Jeux, temps de jeu, metadata"
              action="Voir la library"
              symbol={<LibrarySymbol />}
              onClick={() => (profile ? navigateTo('library') : loginWithSteam())}
            />
            <ModuleCard
              tone="red"
              title="Suggestions"
              subtitle="Recommandations basees sur ton profil"
              action="Voir les suggestions"
              symbol={<SuggestionsSymbol />}
              onClick={() => (profile ? navigateTo('suggestions') : loginWithSteam())}
            />
          </div>
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
            {library && (
              <div className="library-summary">
                <StatChip value={String(library.total_count ?? library.count)} label="Jeux" />
                <StatChip value={formatPlaytime(library.total_playtime)} label="Heures" />
                <StatChip value={`${library.page}/${library.total_pages}`} label="Page" />
              </div>
            )}
            <button className="secondary-button" type="button" onClick={() => navigateTo('home')}>
              Retour accueil
            </button>
          </header>

          {!profile && !isProfileLoading && (
            <div className="empty-state">
              <p>Connecte ton compte Steam pour acceder a ta library.</p>
              <button className="steam-button" type="button" onClick={loginWithSteam}>
                Se connecter avec Steam
              </button>
            </div>
          )}

          {isProfileLoading && (
            <p className="status info">Verification de la connexion Steam...</p>
          )}

          {isLibraryLoading && (
            <p className="status info">Chargement de ta bibliotheque...</p>
          )}
          {libraryError && <p className="status error">{libraryError}</p>}

          {library && (
            <>
              <div className="library-toolbar">
                <p className="library-count">
                  {librarySearchQuery
                    ? `${library.count} resultats sur ${library.total_count ?? library.count}`
                    : `${library.count} jeux trouves`}
                </p>
                <label className="library-search">
                  <span>Recherche</span>
                  <input
                    type="search"
                    value={librarySearch}
                    placeholder="Nom dans toute ta bibliotheque"
                    onChange={(event) => setLibrarySearch(event.target.value)}
                  />
                </label>
              </div>
              <div className="game-catalog">
                {catalogRows.map((row, rowIndex) => {
                  const selectedGame = row.find((game) => game.appid === selectedGameId)

                  return (
                    <div className="game-row" key={`row-${rowIndex}`}>
                      {row.map((game) => (
                        <button
                          className={`game-card ${selectedGameId === game.appid ? 'is-selected' : ''}`}
                          key={game.appid}
                          type="button"
                          aria-expanded={selectedGameId === game.appid}
                          onClick={() => toggleGameDetails(game.appid)}
                        >
                          <img src={game.image} alt="" onError={handleGameImageError} />
                          <div>
                            <h2>{game.name}</h2>
                            <p>{formatPlaytime(game.playtime)} de jeu</p>
                          </div>
                        </button>
                      ))}
                      {selectedGame && (
                        <GameDetailPanel
                          game={selectedGame}
                          details={gameDetails[selectedGame.appid]}
                          isLoading={gameDetailsLoading}
                          error={gameDetailsError}
                          onClose={() => setSelectedGameId(null)}
                          onImageError={handleGameImageError}
                        />
                      )}
                    </div>
                  )
                })}
              </div>
              {library.games.length === 0 && (
                <p className="empty-state">Aucun jeu ne correspond a cette recherche.</p>
              )}
              <div className="pagination-bar">
                <button
                  className="secondary-button"
                  type="button"
                  disabled={library.page <= 1 || isLibraryLoading}
                  onClick={() => goToLibraryPage(Math.max(1, library.page - 1))}
                >
                  Precedent
                </button>
                <span>
                  {library.page} / {library.total_pages}
                </span>
                <button
                  className="secondary-button"
                  type="button"
                  disabled={library.page >= library.total_pages || isLibraryLoading}
                  onClick={() => goToLibraryPage(library.page + 1)}
                >
                  Suivant
                </button>
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
            <button className="secondary-button" type="button" onClick={() => navigateTo('home')}>
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
