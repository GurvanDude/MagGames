import type { SyntheticEvent } from 'react'
import logoUrl from '../assets/maggames-logo.png'

export function getCatalogColumnCount() {
  if (window.innerWidth <= 700) {
    return 1
  }

  if (window.innerWidth <= 1100) {
    return 3
  }

  return 4
}

export function handleCatalogImageError(event: SyntheticEvent<HTMLImageElement>) {
  if (event.currentTarget.src !== logoUrl) {
    event.currentTarget.src = logoUrl
    event.currentTarget.classList.add('game-image-fallback')
  }
}
