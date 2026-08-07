export function formatPlaytime(minutes: number) {
  if (minutes < 60) {
    return `${minutes} min`
  }

  return `${Math.round(minutes / 60)} h`
}

export function splitCatalogValues(value: string | null) {
  return value
    ?.split(/[|,]/)
    .map((item) => item.trim())
    .filter(Boolean) ?? []
}

export function formatCatalogPrice(price: number | null) {
  if (price === null || Number.isNaN(price)) {
    return 'Prix indisponible'
  }

  return price === 0 ? 'Gratuit' : `${price.toFixed(2)} $`
}
