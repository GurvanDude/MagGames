import { GameCatalog, GameDetailFrame } from '../components/GameCatalog'
import { StatChip } from '../components/StatChip'
import { SteamStoreLink } from '../components/SteamStoreLink'
import logoUrl from '../assets/maggames-logo.png'
import type { GameDetails, LibraryResponse, OwnedGame } from '../model/library'
import type { RecommendationGame } from '../model/recommendation'
import type { SteamProfile } from '../model/steam'
import type { CatalogItem, DetailField } from '../model/catalog'
import { handleCatalogImageError } from '../utils/catalog'
import { formatPlaytime, splitCatalogValues } from '../utils/formatters'

type LibraryViewProps = {
  profile: SteamProfile | null
  isLookupMode: boolean
  isProfileLoading: boolean
  library: LibraryResponse | null
  isLibraryLoading: boolean
  libraryError: string | null
  librarySearch: string
  catalogColumns: number
  selectedGameId: number | null
  gameDetails: Record<number, GameDetails>
  gameDetailsLoading: boolean
  gameDetailsError: string | null
  relatedRecommendations: Record<number, RecommendationGame[]>
  isRelatedLoading: boolean
  relatedError: string | null
  onLogin: () => void
  onPageChange: (page: number) => void
  onSearchChange: (value: string) => void
  onSelectGame: (appid: number) => void
  onCloseGame: () => void
}

function GameDetailPanel({
  game,
  details,
  relatedGames,
  isRelatedLoading,
  relatedError,
  isLoading,
  error,
  onClose,
}: {
  game: OwnedGame
  details?: GameDetails
  relatedGames: RecommendationGame[]
  isRelatedLoading: boolean
  relatedError: string | null
  isLoading: boolean
  error: string | null
  onClose: () => void
}) {
  const achievements = details?.achievements
  const obtainedAchievements = achievements?.obtained
  const totalAchievements = achievements?.total
  const fields: DetailField[] = details
    ? [
        { label: 'Date de sortie', value: details.release_date ?? 'Non renseignee' },
        { label: 'Studio', value: details.developers.join(', ') || 'Non renseigne' },
        { label: 'Genre', value: details.genres.join(', ') || 'Non renseigne' },
        { label: 'Temps de jeu', value: formatPlaytime(details.playtime) },
        {
          label: 'Succes obtenus',
          value:
            obtainedAchievements === null || obtainedAchievements === undefined
              ? 'Non disponible'
              : `${obtainedAchievements} / ${totalAchievements ?? '?'} obtenus`,
        },
      ]
    : []

  return (
    <GameDetailFrame
      appid={game.appid}
      titleId={`game-detail-${game.appid}`}
      eyebrow="Fiche Steam"
      title={details?.name ?? game.name}
      image={details?.image ?? game.image}
      description={details?.description}
      fields={fields}
      tone="blue"
      isLoading={isLoading}
      error={error}
      meta={
        details && details.publishers.length > 0 ? (
          <p className="game-detail-meta">Editeur : {details.publishers.join(', ')}</p>
        ) : null
      }
      aside={
        <aside className="game-suggestions-slot" aria-label="Suggestions pour ce jeu">
          <p className="detail-eyebrow">Jeux similaires</p>
          {isRelatedLoading && (
            <p className="detail-status">Chargement des jeux similaires...</p>
          )}
          {relatedError && <p className="detail-status detail-error">{relatedError}</p>}
          {!isRelatedLoading && !relatedError && relatedGames.length === 0 && (
            <p className="detail-status">Aucun jeu similaire disponible.</p>
          )}
          {relatedGames.length > 0 && (
            <div className="related-game-list">
              {relatedGames.map((relatedGame) => (
                <article className="related-game-card" key={relatedGame.appid}>
                  <img
                    src={relatedGame.image ?? logoUrl}
                    alt=""
                    onError={handleCatalogImageError}
                  />
                  <div>
                    <div className="related-game-heading">
                      <h3>{relatedGame.nom ?? 'Jeu sans titre'}</h3>
                      <SteamStoreLink appid={relatedGame.appid} compact />
                    </div>
                    <p>{splitCatalogValues(relatedGame.genre).slice(0, 2).join(' / ') || 'Genre non renseigne'}</p>
                  </div>
                </article>
              ))}
            </div>
          )}
        </aside>
      }
      onClose={onClose}
      onImageError={handleCatalogImageError}
    />
  )
}

export function LibraryView({
  profile,
  isLookupMode,
  isProfileLoading,
  library,
  isLibraryLoading,
  libraryError,
  librarySearch,
  catalogColumns,
  selectedGameId,
  gameDetails,
  gameDetailsLoading,
  gameDetailsError,
  relatedRecommendations,
  isRelatedLoading,
  relatedError,
  onLogin,
  onPageChange,
  onSearchChange,
  onSelectGame,
  onCloseGame,
}: LibraryViewProps) {
  const libraryItems: CatalogItem[] = library
    ? library.games.map((game) => ({
        appid: game.appid,
        name: game.name,
        image: game.image,
        secondary: `${formatPlaytime(game.playtime)} de jeu`,
        tone: 'blue',
      }))
    : []

  return (
    <section className="library-page" aria-labelledby="library-title">
      <header className="page-header">
        <div>
          <p className="eyebrow">Bibliotheque Steam</p>
          <h1 id="library-title">Tes jeux Steam</h1>
          <p className="intro">
            {isLookupMode
              ? 'Consultation de la bibliotheque publique de ce profil Steam.'
              : 'Premiere recuperation reelle depuis ton compte Steam.'}
          </p>
        </div>
        {library && (
          <div className="library-summary">
            <StatChip value={String(library.total_count ?? library.count)} label="Jeux" />
            <StatChip value={formatPlaytime(library.total_playtime)} label="Heures" />
            <StatChip value={`${library.page}/${library.total_pages}`} label="Page" />
          </div>
        )}
      </header>

      {!profile && !isProfileLoading && (
        <div className="empty-state">
          <p>Connecte ton compte Steam pour acceder a ta library.</p>
          <button className="steam-button" type="button" onClick={onLogin}>
            Se connecter avec Steam
          </button>
        </div>
      )}

      {isProfileLoading && <p className="status info">Verification de la connexion Steam...</p>}
      {isLibraryLoading && <p className="status info">Chargement de ta bibliotheque...</p>}
      {libraryError && <p className="status error">{libraryError}</p>}

      {library && (
        <>
          <div className="library-toolbar">
            <p className="library-count">
              {librarySearch
                ? `${library.count} resultats sur ${library.total_count ?? library.count}`
                : `${library.count} jeux trouves`}
            </p>
            <label className="library-search">
              <span>Recherche</span>
              <input
                type="search"
                value={librarySearch}
                placeholder="Nom dans toute ta bibliotheque"
                onChange={(event) => onSearchChange(event.target.value)}
              />
            </label>
          </div>
          <GameCatalog
            items={libraryItems}
            columns={catalogColumns}
            selectedId={selectedGameId}
            onSelect={onSelectGame}
            onImageError={handleCatalogImageError}
            renderDetail={(appid) => {
              const selectedGame = library.games.find((game) => game.appid === appid)

              if (!selectedGame) {
                return null
              }

              return (
                <GameDetailPanel
                  game={selectedGame}
                  details={gameDetails[selectedGame.appid]}
                  relatedGames={relatedRecommendations[selectedGame.appid] ?? []}
                  isRelatedLoading={isRelatedLoading}
                  relatedError={relatedError}
                  isLoading={gameDetailsLoading}
                  error={gameDetailsError}
                  onClose={onCloseGame}
                />
              )
            }}
          />
          {library.games.length === 0 && (
            <p className="empty-state">Aucun jeu ne correspond a cette recherche.</p>
          )}
          <div className="pagination-bar">
            <button
              className="secondary-button"
              type="button"
              disabled={library.page <= 1 || isLibraryLoading}
              onClick={() => onPageChange(Math.max(1, library.page - 1))}
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
              onClick={() => onPageChange(library.page + 1)}
            >
              Suivant
            </button>
          </div>
        </>
      )}
    </section>
  )
}
