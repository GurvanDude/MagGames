import { requestJson } from './client'
import type { RankingResponse, RankingType } from '../model/ranking'

const rankingPaths: Record<RankingType, string> = {
  joues: '/api/top/joues/',
  enligne: '/api/top/enligne/',
  proprietaires: '/api/top/proprietaires/',
}

export function getRanking(
  type: RankingType,
  genre: string,
  signal?: AbortSignal,
) {
  const params = new URLSearchParams({
    limit: '20',
    page: '1',
    genre,
  })

  return requestJson<RankingResponse>(
    `${rankingPaths[type]}?${params.toString()}`,
    { signal },
  )
}
