import { requestJson, API_URL } from './client'
import type { SteamProfile } from '../model/steam'

export function getSteamLoginUrl() {
  return `${API_URL}/api/auth/steam/login/`
}

export function getSteamIdLookupUrl(steamId: string) {
  const params = new URLSearchParams({ lookup_steamid: steamId })
  return `${window.location.origin}/home?${params.toString()}`
}

export function getSteamProfileById(steamId: string, signal?: AbortSignal) {
  const params = new URLSearchParams({ steamid: steamId })
  return requestJson<SteamProfile>(`/api/auth/steam/lookup/?${params.toString()}`, { signal })
}

export function getCurrentProfile(signal?: AbortSignal) {
  return requestJson<SteamProfile>('/api/auth/steam/me/', { signal })
}

export function logoutFromSteam() {
  return requestJson<{ detail: string }>('/api/auth/steam/logout/', { method: 'POST' })
}
