import { useState } from 'react'
import logoUrl from '../assets/maggames-logo.png'

export type AppView = 'home' | 'library' | 'suggestions'

export type HeaderProfile = {
  personaName: string
  avatar: string
} | null

type AppHeaderProps = {
  activeView: AppView
  profile: HeaderProfile
  onNavigate: (view: AppView) => void
  onLogin: () => void
  onLogout: () => void
}

export function AppHeader({
  activeView,
  profile,
  onNavigate,
  onLogin,
  onLogout,
}: AppHeaderProps) {
  const [isProfileMenuOpen, setIsProfileMenuOpen] = useState(false)

  function goTo(view: AppView) {
    setIsProfileMenuOpen(false)

    if (view === 'home' || profile) {
      onNavigate(view)
      return
    }

    onLogin()
  }

  function handleAccountClick() {
    if (!profile) {
      onLogin()
      return
    }

    setIsProfileMenuOpen((current) => !current)
  }

  function handleLogout() {
    setIsProfileMenuOpen(false)
    onLogout()
  }

  return (
    <header className="dashboard-header">
      <a
        className="brand-lockup"
        href="/home"
        onClick={(event) => {
          event.preventDefault()
          goTo('home')
        }}
      >
        <img className="mag-logo" src={logoUrl} alt="MagGames" />
        <span className="brand-wordmark">Games</span>
      </a>

      <nav className="main-nav" aria-label="Navigation principale">
        <a
          className={activeView === 'home' ? 'active' : ''}
          href="/home"
          onClick={(event) => {
            event.preventDefault()
            goTo('home')
          }}
        >
          Accueil
        </a>
        <a
          className={activeView === 'library' ? 'active' : ''}
          href="/library"
          onClick={(event) => {
            event.preventDefault()
            goTo('library')
          }}
        >
          Library
        </a>
        <a
          className={activeView === 'suggestions' ? 'active' : ''}
          href="/suggestions"
          onClick={(event) => {
            event.preventDefault()
            goTo('suggestions')
          }}
        >
          Suggestions
        </a>
      </nav>

      <div className="account-menu">
        <button
          className="account-pill"
          type="button"
          onClick={handleAccountClick}
          aria-haspopup={profile ? 'menu' : undefined}
          aria-expanded={profile ? isProfileMenuOpen : undefined}
        >
          {profile ? <img src={profile.avatar} alt="" /> : <span className="avatar-empty" />}
          <span>{profile?.personaName ?? 'Non connecte'}</span>
          {profile && <span className="account-chevron" aria-hidden="true" />}
        </button>

        {profile && isProfileMenuOpen && (
          <div className="profile-dropdown" role="menu">
            <button type="button" role="menuitem" onClick={handleLogout}>
              Se deconnecter
            </button>
          </div>
        )}
      </div>
    </header>
  )
}
