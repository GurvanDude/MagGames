export type OwnedGame = {
  appid: number
  name: string
  image: string
  playtime: number
}

export type LibraryResponse = {
  games: OwnedGame[]
  count: number
  total_count: number
  total_playtime: number
  page: number
  total_pages: number
  next: string | null
  previous: string | null
}

export type GameDetails = {
  appid: number
  name: string
  image: string
  description: string
  release_date: string | null
  genres: string[]
  developers: string[]
  publishers: string[]
  categories: string[]
  platforms: string[]
  website: string | null
  playtime: number
  achievements: {
    obtained: number | null
    total: number | null
  }
}
