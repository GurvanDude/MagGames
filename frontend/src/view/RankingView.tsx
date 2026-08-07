import { useEffect, useRef, useState } from 'react'
import { GameCatalog, GameDetailFrame } from '../components/GameCatalog'
import type { CatalogItem, DetailField } from '../model/catalog'
import type { RankingGame, RankingGenre, RankingResponse, RankingType } from '../model/ranking'
import { handleCatalogImageError } from '../utils/catalog'
import { formatCatalogPrice, splitCatalogValues } from '../utils/formatters'

type RankingViewProps = {
  rankings: RankingResponse | null
  isRankingsLoading: boolean
  rankingError: string | null
  rankingType: RankingType
  rankingGenre: string
  catalogColumns: number
  selectedRankingId: number | null
  onRankingTypeChange: (type: RankingType) => void
  onRankingGenreChange: (genre: string) => void
  onSelectRanking: (appid: number) => void
  onCloseRanking: () => void
}

const rankingTypes: Array<{ value: RankingType; label: string }> = [
  { value: 'joues', label: 'Les plus joues' },
  { value: 'enligne', label: 'En ligne' },
  { value: 'proprietaires', label: 'Les plus possedes' },
]

const defaultGenreOptions: RankingGenre[] = [
  { value: 'tous', label: 'Tous les genres' },
]

function RankingGenreSelect({
  options,
  value,
  onChange,
}: {
  options: RankingGenre[]
  value: string
  onChange: (value: string) => void
}) {
  const [isOpen, setIsOpen] = useState(false)
  const menuRef = useRef<HTMLDivElement>(null)
  const selectedOption = options.find((option) => option.value === value) ?? options[0]

  useEffect(() => {
    if (!isOpen) {
      return
    }

    function closeOnOutsideClick(event: MouseEvent) {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
        setIsOpen(false)
      }
    }

    function closeOnEscape(event: KeyboardEvent) {
      if (event.key === 'Escape') {
        setIsOpen(false)
      }
    }

    document.addEventListener('mousedown', closeOnOutsideClick)
    document.addEventListener('keydown', closeOnEscape)

    return () => {
      document.removeEventListener('mousedown', closeOnOutsideClick)
      document.removeEventListener('keydown', closeOnEscape)
    }
  }, [isOpen])

  function selectGenre(genre: RankingGenre) {
    onChange(genre.value)
    setIsOpen(false)
  }

  return (
    <div className="ranking-genre-select" ref={menuRef}>
      <span id="ranking-genre-label">Genre</span>
      <button
        className="ranking-genre-trigger"
        type="button"
        aria-haspopup="listbox"
        aria-expanded={isOpen}
        aria-labelledby="ranking-genre-label"
        onClick={() => setIsOpen((current) => !current)}
      >
        <span>{selectedOption?.label ?? 'Tous les genres'}</span>
        <span className="ranking-genre-chevron" aria-hidden="true" />
      </button>

      {isOpen && (
        <div className="ranking-genre-options" role="listbox" aria-label="Genres Steam">
          {options.map((option) => (
            <button
              className={option.value === value ? 'active' : ''}
              key={option.value}
              type="button"
              role="option"
              aria-selected={option.value === value}
              onClick={() => selectGenre(option)}
            >
              {option.label}
            </button>
          ))}
        </div>
      )}
    </div>
  )
}

function rankingSecondary(game: RankingGame) {
  if (game.developpeur) {
    return game.developpeur
  }

  return splitCatalogValues(game.genre).join(' / ') || 'Genre non renseigne'
}

function RankingDetailPanel({
  game,
  onClose,
}: {
  game: RankingGame
  onClose: () => void
}) {
  const fields: DetailField[] = [
    { label: 'Rang', value: `#${game.rang}` },
    { label: 'Genre', value: splitCatalogValues(game.genre).join(', ') || 'Non renseigne' },
    { label: 'Developpeur', value: game.developpeur ?? 'Non renseigne' },
    { label: 'Editeur', value: game.editeur ?? 'Non renseigne' },
    { label: 'Date de sortie', value: game.date_sortie ?? 'Non renseignee' },
    { label: 'Prix', value: formatCatalogPrice(game.prix) },
    {
      label: 'Metacritic',
      value: game.metacritic === null ? 'Non renseigne' : `${game.metacritic} / 100`,
    },
    {
      label: 'Plateformes',
      value: splitCatalogValues(game.plateformes).join(', ') || 'Non renseigne',
    },
  ]

  return (
    <GameDetailFrame
      appid={game.appid}
      titleId={`ranking-detail-${game.appid}`}
      eyebrow="Fiche classement"
      title={game.nom ?? 'Jeu sans titre'}
      image={game.image}
      description={game.description}
      fields={fields}
      tone="red"
      meta={
        <p className="game-detail-meta">
          Rang precedent : {game.rang_precedent === null ? 'Non disponible' : `#${game.rang_precedent}`}
        </p>
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

export function RankingView({
  rankings,
  isRankingsLoading,
  rankingError,
  rankingType,
  rankingGenre,
  catalogColumns,
  selectedRankingId,
  onRankingTypeChange,
  onRankingGenreChange,
  onSelectRanking,
  onCloseRanking,
}: RankingViewProps) {
  const rankingItems: CatalogItem[] = rankings
    ? rankings.games.map((game) => ({
        appid: game.appid,
        name: game.nom ?? 'Jeu sans titre',
        image: game.image,
        secondary: rankingSecondary(game),
        tone: 'red',
        rank: game.rang,
      }))
    : []

  return (
    <section className="rankings-page" aria-labelledby="rankings-title">
      <header className="page-header">
        <div>
          <p className="eyebrow">Classement Steam</p>
          <h1 id="rankings-title">Top 20 des jeux</h1>
          <p className="intro">
            Les jeux les plus visibles sur Steam, filtres par genre du catalogue MagGames.
          </p>
        </div>
      </header>

      <div className="ranking-controls" aria-label="Filtres du classement">
        <div className="ranking-type-switch" role="group" aria-label="Type de classement">
          {rankingTypes.map((type) => (
            <button
              className={rankingType === type.value ? 'active' : ''}
              key={type.value}
              type="button"
              aria-pressed={rankingType === type.value}
              onClick={() => onRankingTypeChange(type.value)}
            >
              {type.label}
            </button>
          ))}
        </div>
        <RankingGenreSelect
          options={rankings?.genres ?? defaultGenreOptions}
          value={rankingGenre}
          onChange={onRankingGenreChange}
        />
      </div>

      {isRankingsLoading && <p className="status info">Chargement du classement Steam...</p>}
      {rankingError && <p className="status error">{rankingError}</p>}

      {rankings && !rankingError && (
        <>
          <div className="ranking-summary">
            <p className="library-count">Top {rankings.games.length} jeux</p>
            <p className="recommendation-caption">
              Classement {rankings.classement} - filtre : {rankings.genre_label}
            </p>
          </div>
          <GameCatalog
            items={rankingItems}
            columns={catalogColumns}
            selectedId={selectedRankingId}
            onSelect={onSelectRanking}
            onImageError={handleCatalogImageError}
            renderDetail={(appid) => {
              const game = rankings.games.find((item) => item.appid === appid)

              return game ? <RankingDetailPanel game={game} onClose={onCloseRanking} /> : null
            }}
          />
          {rankings.games.length === 0 && (
            <p className="empty-state">Aucun jeu ne correspond a ce genre dans le classement.</p>
          )}
        </>
      )}
    </section>
  )
}
