import { requestJson } from './client'
import type { RecommendationResponse } from '../model/recommendation'

export function getRecommendations(
  limit: number,
  steamId?: string,
  signal?: AbortSignal,
) {
  const params = new URLSearchParams({ limit: String(limit) })

  if (steamId) {
    params.set('steamid', steamId)
  }

  return requestJson<RecommendationResponse>(`/api/recommendations/?${params.toString()}`, { signal })
}
