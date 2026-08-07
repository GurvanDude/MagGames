import { GameCatalog, GameDetailFrame } from '../components/GameCatalog'
import type { CatalogItem, DetailField } from '../model/catalog'
import type { RecommendationGame, RecommendationResponse } from '../model/recommendation'
import type { SteamProfile } from '../model/steam'
import { handleCatalogImageError } from '../utils/catalog'
import { formatCatalogPrice, splitCatalogValues } from '../utils/formatters'

type SuggestionsViewProps = {
  profile: SteamProfile | null
  isLookupMode: boolean
  isProfileLoading: boolean
  profileError: string | null
  recommendations: RecommendationResponse | null
  isRecommendationsLoading: boolean
  recommendationError: string | null
  catalogColumns: number
  selectedRecommendationId: number | null
  onLogin: () => void
  onNavigateHome: () => void
  onSelectRecommendation: (appid: number) => void
  onCloseRecommendation: () => void
}

function RecommendationDetailPanel({
  game,
  onClose,
}: {
  game: RecommendationGame
  onClose: () => void
}) {
  const genres = splitCatalogValues(game.genre)
  const platforms = splitCatalogValues(game.plateformes)
  const tags = splitCatalogValues(game.tags)

  const fields: DetailField[] = [
    { label: 'Date de sortie', value: game.date_sortie ?? 'Non renseignee' },
    { label: 'Genre', value: genres.join(', ') || 'Non renseigne' },
    { label: 'Developpeur', value: game.developpeur ?? 'Non renseigne' },
    { label: 'Editeur', value: game.editeur ?? 'Non renseigne' },
    { label: 'Prix', value: formatCatalogPrice(game.prix) },
    {
      label: 'Metacritic',
      value: game.metacritic === null ? 'Non renseigne' : `${game.metacritic} / 100`,
    },
    { label: 'Plateformes', value: platforms.join(', ') || 'Non renseigne' },
  ]

  return (
    <GameDetailFrame
      titleId={`recommendation-detail-${game.appid}`}
      eyebrow="Fiche catalogue"
      title={game.nom ?? 'Jeu sans titre'}
      image={game.image}
      description={game.description}
      fields={fields}
      tone="red"
      meta={
        tags.length > 0 ? (
          <p className="game-detail-meta">Tags : {tags.slice(0, 8).join(', ')}</p>
        ) : null
      }
      onClose={onClose}
      onImageError={handleCatalogImageError}
    >
      {game.site_web && (
        <a
          className="recommendation-link"
          href={game.site_web}
          target="_blank"
          rel="noreferrer"
        >
          Voir le site du jeu
        </a>
      )}
    </GameDetailFrame>
  )
}

export function SuggestionsView({
  profile,
  isLookupMode,
  isProfileLoading,
  profileError,
  recommendations,
  isRecommendationsLoading,
  recommendationError,
  catalogColumns,
  selectedRecommendationId,
  onLogin,
  onNavigateHome,
  onSelectRecommendation,
  onCloseRecommendation,
}: SuggestionsViewProps) {
  const recommendationItems: CatalogItem[] = recommendations
    ? recommendations.recommendations.map((game) => ({
        appid: game.appid,
        name: game.nom ?? 'Jeu sans titre',
        image: game.image,
        secondary: formatCatalogPrice(game.prix),
        tone: 'red',
      }))
    : []

  return (
    <section className="suggestions-page" aria-labelledby="suggestions-title">
      <header className="page-header">
        <div>
          <p className="eyebrow">Suggestions</p>
          <h1 id="suggestions-title">Recommandations</h1>
          <p className="intro">
            Des jeux choisis a partir de ta bibliotheque Steam et du catalogue MagGames.
          </p>
        </div>
        <button className="secondary-button" type="button" onClick={onNavigateHome}>
          Retour accueil
        </button>
      </header>

      {!profile && !isProfileLoading && !isLookupMode && (
        <div className="empty-state">
          <p>Connecte ton compte Steam pour obtenir des recommandations.</p>
          <button className="steam-button" type="button" onClick={onLogin}>
            Se connecter avec Steam
          </button>
        </div>
      )}

      {isLookupMode && !profile && !isProfileLoading && (
        <p className="status error">
          {profileError ?? 'Impossible de charger ce profil Steam.'}
        </p>
      )}

      {isProfileLoading && <p className="status info">Verification de la connexion Steam...</p>}
      {isRecommendationsLoading && (
        <p className="status info">
          Analyse de ta bibliotheque par le moteur de recommandation...
        </p>
      )}
      {recommendationError && <p className="status error">{recommendationError}</p>}

      {recommendations && !recommendationError && (
        <>
          <div className="recommendation-toolbar">
            <div>
              <p className="library-count">
                {recommendations.jeux_possedes} jeux pris en compte
              </p>
              <p className="recommendation-caption">
                {recommendations.origine === 'modele'
                  ? 'Profil analyse par le modele MagGames.'
                  : 'Profil compare avec les jeux populaires du catalogue.'}
              </p>
            </div>
            <span className={`recommendation-origin ${recommendations.origine}`}>
              {recommendations.origine === 'modele' ? 'Modele actif' : 'Fallback catalogue'}
            </span>
          </div>
          {recommendations.origine === 'populaires' && (
            <p className="status warning">
              Le moteur n a pas produit de resultats personnalises : les jeux affiches viennent du
              catalogue.
            </p>
          )}
          <GameCatalog
            items={recommendationItems}
            columns={catalogColumns}
            selectedId={selectedRecommendationId}
            onSelect={onSelectRecommendation}
            onImageError={handleCatalogImageError}
            renderDetail={(appid) => {
              const selectedGame = recommendations.recommendations.find(
                (game) => game.appid === appid,
              )

              if (!selectedGame) {
                return null
              }

              return (
                <RecommendationDetailPanel
                  game={selectedGame}
                  onClose={onCloseRecommendation}
                />
              )
            }}
          />
          {recommendations.recommendations.length === 0 && (
            <p className="empty-state">
              Aucune recommandation n est disponible pour le moment.
            </p>
          )}
        </>
      )}
    </section>
  )
}
