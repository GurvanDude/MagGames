export type RecommendationGame = {
  appid: number
  nom: string | null
  description: string | null
  genre: string | null
  categories: string | null
  tags: string | null
  date_sortie: string | null
  prix: number | null
  metacritic: number | null
  avis_positifs: number | null
  avis_negatifs: number | null
  plateformes: string | null
  image: string | null
  developpeur: string | null
  editeur: string | null
  site_web: string | null
}

export type RecommendationResponse = {
  origine: 'modele' | 'populaires'
  modele_disponible: boolean
  modele_erreur: string | null
  jeux_possedes: number
  recommendations: RecommendationGame[]
}
