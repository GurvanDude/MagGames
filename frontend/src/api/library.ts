import { requestJson } from './client'
import type { GameDetails, LibraryResponse } from '../model/library'

export function getLibrary(
  page: number,
  keyword: string,
  steamId?: string,
  signal?: AbortSignal,
) {
  const params = new URLSearchParams({ page: String(page) })

  if (keyword) {
    params.set('keyword', keyword)
  }

  if (steamId) {
    params.set('steamid', steamId)
  }

  return requestJson<LibraryResponse>(`/api/library/?${params.toString()}`, { signal })
}

export function getGameDetails(appid: number, steamId?: string, signal?: AbortSignal) {
  const params = new URLSearchParams()

  if (steamId) {
    params.set('steamid', steamId)
  }

  const query = params.toString()
  return requestJson<GameDetails>(`/api/library/${appid}/${query ? `?${query}` : ''}`, { signal })
}
