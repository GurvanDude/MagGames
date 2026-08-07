import { requestJson } from './client'
import type {
  RelatedRecommendationResponse,
  RecommendationResponse,
} from '../model/recommendation'

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

export function getRelatedRecommendations(
  appid: number,
  steamId?: string,
  signal?: AbortSignal,
) {
  const params = new URLSearchParams({ limit: '4' })

  if (steamId) {
    params.set('steamid', steamId)
  }

  return requestJson<RelatedRecommendationResponse>(
    '/api/recommendations/related/' + appid + '/?' + params.toString(),
    { signal },
  )
}
