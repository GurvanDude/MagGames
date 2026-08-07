type SteamStoreLinkProps = {
  appid: number
  compact?: boolean
}

function steamStoreUrl(appid: number) {
  return `https://store.steampowered.com/app/${appid}/`
}

function SteamIcon() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">
      <circle cx="16.1" cy="7.4" r="3.1" />
      <circle cx="7.2" cy="16.4" r="2.8" />
      <path d="M9.4 15.4 13.8 9.9" />
      <path d="m2.9 14.8 2.1.9" />
    </svg>
  )
}

export function SteamStoreLink({ appid, compact = false }: SteamStoreLinkProps) {
  return (
    <a
      className={`steam-store-link${compact ? ' compact' : ''}`}
      href={steamStoreUrl(appid)}
      target="_blank"
      rel="noreferrer"
      title="Voir ce jeu sur Steam"
      aria-label="Voir ce jeu sur Steam"
      onClick={(event) => event.stopPropagation()}
    >
      <span className="steam-store-icon">
        <SteamIcon />
      </span>
      {!compact && <span>Voir sur Steam</span>}
    </a>
  )
}
