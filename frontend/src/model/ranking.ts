import type { RecommendationGame } from './recommendation'

export type RankingType = 'joues' | 'enligne' | 'proprietaires'

export type RankingGame = RecommendationGame & {
  rang: number
  rang_precedent: number | null
}

export type RankingGenre = {
  value: string
  label: string
}

export type RankingResponse = {
  classement: RankingType
  genre: string
  genre_label: string
  genres: RankingGenre[]
  count: number
  page: number
  pages: number
  page_size: number
  games: RankingGame[]
}
