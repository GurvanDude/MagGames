const API_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

export async function requestJson<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, {
    ...init,
    credentials: 'include',
  })
  const contentType = response.headers.get('content-type') ?? ''

  if (!contentType.includes('application/json')) {
    await response.text()

    if (path.includes('/api/recommendations/')) {
      throw new Error(
        `Le catalogue de recommandations est indisponible (HTTP ${response.status}). Initialise data/maggames.db.`,
      )
    }

    throw new Error(`Le serveur a renvoye une reponse invalide (HTTP ${response.status}).`)
  }

  const data = await response.json()

  if (!response.ok) {
    throw new Error(data.detail ?? `La requete a echoue (HTTP ${response.status}).`)
  }

  return data as T
}

export { API_URL }
