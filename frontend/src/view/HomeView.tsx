import { useState } from 'react'
import type { FormEvent, ReactNode } from 'react'
import type { AppView } from '../components/AppHeader'
import { StatChip } from '../components/StatChip'
import type { LibraryResponse } from '../model/library'
import type { SteamProfile } from '../model/steam'

type HomeViewProps = {
  profile: SteamProfile | null
  isLookupMode: boolean
  library: LibraryResponse | null
  errorMessage: string | null
  profileError: string | null
  onLogin: () => void
  onLoginWithId: (steamId: string) => void
  onNavigate: (view: AppView) => void
}

function formatPlaytime(minutes: number) {
  if (minutes < 60) {
    return `${minutes} min`
  }

  return `${Math.round(minutes / 60)} h`
}

function LibrarySymbol() {
  return (
    <svg className="module-symbol" viewBox="0 0 360 260" aria-hidden="true">
      <g className="library-hud">
        <circle cx="180" cy="130" r="92" />
        <circle cx="180" cy="130" r="76" />
        <path d="M180 28v34M180 198v34M78 130h34M248 130h34" />
        <path d="M78 70h58l28 28M282 70h-58l-28 28M78 190h58l28-28M282 190h-58l-28-28" />
        <path d="M94 50h28M238 50h28M94 210h28M238 210h28" />
      </g>
      <g className="library-rack">
        <path d="M116 72h124l14 14v116H106V86Z" />
        <path d="M122 104h116M122 138h116M122 172h116" />
        <path d="M122 88h116" />
      </g>
      <g className="library-books">
        <path d="M130 88h14v16h-14ZM149 88h25v16h-25ZM180 88h14v16h-14ZM200 88h29v16h-29Z" />
        <path d="M130 110h22v28h-22ZM158 110h14v28h-14ZM178 110h27v28h-27ZM211 110h18v28h-18Z" />
        <path d="M130 144h14v28h-14ZM150 144h28v28h-28ZM184 144h16v28h-16ZM206 144h23v28h-23Z" />
        <path d="M130 178h25v16h-25ZM161 178h14v16h-14ZM181 178h28v16h-28ZM215 178h14v16h-14Z" />
      </g>
      <g className="library-node node-a">
        <rect x="38" y="52" width="58" height="42" rx="6" />
        <path d="M53 66h20v19H53ZM58 62v23M78 70h7M78 77h7" />
      </g>
      <g className="library-node node-b">
        <rect x="264" y="52" width="58" height="42" rx="6" />
        <path d="M279 66h20v19H279ZM284 62v23M304 70h7M304 77h7" />
      </g>
      <g className="library-node node-c">
        <rect x="38" y="166" width="58" height="42" rx="6" />
        <path d="M53 180h20v19H53ZM58 176v23M78 184h7M78 191h7" />
      </g>
      <g className="library-node node-d">
        <rect x="264" y="166" width="58" height="42" rx="6" />
        <path d="M279 180h20v19H279ZM284 176v23M304 184h7M304 191h7" />
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
          <span>→</span>
        </span>
      </span>
    </button>
  )
}

export function HomeView({
  profile,
  isLookupMode,
  library,
  errorMessage,
  profileError,
  onLogin,
  onLoginWithId,
  onNavigate,
}: HomeViewProps) {
  const [isSteamIdFormOpen, setIsSteamIdFormOpen] = useState(false)
  const [steamId, setSteamId] = useState('')
  const [steamIdError, setSteamIdError] = useState<string | null>(null)

  function submitSteamId(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const normalizedSteamId = steamId.trim()

    if (!/^\d{17}$/.test(normalizedSteamId)) {
      setSteamIdError('Entre un SteamID64 valide de 17 chiffres.')
      return
    }

    setSteamIdError(null)
    onLoginWithId(normalizedSteamId)
  }

  return (
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
              {isLookupMode ? 'Profil Steam consulte' : 'Compte Steam connecte'}
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
            <button className="connect-button" type="button" onClick={onLogin}>
              Se connecter avec Steam
            </button>
            <button
              className="secondary-button steam-id-button"
              type="button"
              onClick={() => {
                setIsSteamIdFormOpen((current) => !current)
                setSteamIdError(null)
              }}
            >
              Se connecter avec un ID Steam
            </button>
            {isSteamIdFormOpen && (
              <form className="steam-id-form" onSubmit={submitSteamId}>
                <label htmlFor="steam-id">SteamID64</label>
                <div className="steam-id-fields">
                  <input
                    id="steam-id"
                    inputMode="numeric"
                    pattern="[0-9]{17}"
                    value={steamId}
                    placeholder="76561198..."
                    onChange={(event) => setSteamId(event.target.value)}
                  />
                  <button className="secondary-button" type="submit">
                    Continuer
                  </button>
                </div>
                {steamIdError && <p className="status error">{steamIdError}</p>}
              </form>
            )}
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
          onClick={() => (profile ? onNavigate('library') : onLogin())}
        />
        <ModuleCard
          tone="red"
          title="Suggestions"
          subtitle="Recommandations basees sur ton profil"
          action="Voir les suggestions"
          symbol={<SuggestionsSymbol />}
          onClick={() => (profile ? onNavigate('suggestions') : onLogin())}
        />
      </div>
    </section>
  )
}
