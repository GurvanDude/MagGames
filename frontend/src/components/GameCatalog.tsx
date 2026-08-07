import type { ReactNode, SyntheticEvent } from 'react'
import logoUrl from '../assets/maggames-logo.png'
import type { CatalogItem, CatalogTone, DetailField } from '../model/catalog'
import { handleCatalogImageError } from '../utils/catalog'
import { SteamStoreLink } from './SteamStoreLink'

export type { CatalogItem, CatalogTone, DetailField } from '../model/catalog'

type GameCatalogProps = {
  items: CatalogItem[]
  columns: number
  selectedId: number | null
  onSelect: (appid: number) => void
  onImageError?: (event: SyntheticEvent<HTMLImageElement>) => void
  renderDetail?: (appid: number) => ReactNode
}

function splitIntoRows<T>(items: T[], rowSize: number) {
  const rows: T[][] = []

  for (let index = 0; index < items.length; index += rowSize) {
    rows.push(items.slice(index, index + rowSize))
  }

  return rows
}

function GameCard({
  item,
  isSelected,
  onSelect,
  onImageError,
}: {
  item: CatalogItem
  isSelected: boolean
  onSelect: () => void
  onImageError: (event: SyntheticEvent<HTMLImageElement>) => void
}) {
  return (
    <button
      className={`game-card ${item.tone} ${isSelected ? 'is-selected' : ''}`}
      type="button"
      aria-expanded={isSelected}
      onClick={onSelect}
    >
      {item.rank !== undefined && (
        <span className="game-card-rank" aria-label={`Rang ${item.rank}`}>
          {String(item.rank).padStart(2, '0')}
        </span>
      )}
      <img
        src={item.image ?? logoUrl}
        alt=""
        onError={onImageError}
      />
      <div>
        <h2>{item.name}</h2>
        <p>{item.secondary}</p>
      </div>
    </button>
  )
}

export function GameCatalog({
  items,
  columns,
  selectedId,
  onSelect,
  onImageError,
  renderDetail,
}: GameCatalogProps) {
  const rows = splitIntoRows(items, columns)

  function handleImageError(event: SyntheticEvent<HTMLImageElement>) {
    if (onImageError) {
      onImageError(event)
      return
    }

    handleCatalogImageError(event)
  }

  return (
    <div className="game-catalog">
      {rows.map((row, rowIndex) => {
        const selectedItem = row.find((item) => item.appid === selectedId)

        return (
          <div className="game-row" key={`row-${rowIndex}`}>
            {row.map((item) => (
              <GameCard
                key={item.appid}
                item={item}
                isSelected={item.appid === selectedId}
                onSelect={() => onSelect(item.appid)}
                onImageError={handleImageError}
              />
            ))}
            {selectedItem && renderDetail?.(selectedItem.appid)}
          </div>
        )
      })}
    </div>
  )
}

type GameDetailFrameProps = {
  appid: number
  titleId: string
  eyebrow: string
  title: string
  image: string | null
  description?: string | null
  fields: DetailField[]
  tone: CatalogTone
  isLoading?: boolean
  error?: string | null
  meta?: ReactNode
  aside?: ReactNode
  children?: ReactNode
  onClose: () => void
  onImageError: (event: SyntheticEvent<HTMLImageElement>) => void
}

export function GameDetailFrame({
  appid,
  titleId,
  eyebrow,
  title,
  image,
  description,
  fields,
  tone,
  isLoading = false,
  error = null,
  meta,
  aside,
  children,
  onClose,
  onImageError,
}: GameDetailFrameProps) {
  return (
    <section
      className={`game-detail-panel ${tone === 'red' ? 'recommendation-detail-panel' : ''}`}
      aria-labelledby={titleId}
    >
      <div className="game-detail-main">
        <div className="game-detail-image">
          <img src={image ?? logoUrl} alt="" onError={onImageError} />
        </div>
        <div className="game-detail-content">
          <div className="game-detail-heading">
            <div>
              <p className="detail-eyebrow">{eyebrow}</p>
              <h2 id={titleId}>{title}</h2>
            </div>
            <button className="detail-close" type="button" aria-label="Fermer" onClick={onClose}>
              x
            </button>
          </div>

          {isLoading && <p className="detail-status">Recuperation des informations Steam...</p>}
          {error && <p className="detail-status error">{error}</p>}
          {description !== undefined && (
            <p className="game-detail-description">
              {description || 'Aucune description disponible pour ce jeu.'}
            </p>
          )}
          {fields.length > 0 && (
            <dl className="game-facts">
              {fields.map((field) => (
                <div key={field.label}>
                  <dt>{field.label}</dt>
                  <dd>{field.value}</dd>
                </div>
              ))}
            </dl>
          )}
          {meta}
          <div className="game-detail-actions">
            <SteamStoreLink appid={appid} />
            {children}
          </div>
        </div>
      </div>
      {aside}
    </section>
  )
}
