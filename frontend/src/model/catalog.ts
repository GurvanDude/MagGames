import type { ReactNode } from 'react'

export type CatalogTone = 'blue' | 'red'

export type CatalogItem = {
  appid: number
  name: string
  image: string | null
  secondary: string
  tone: CatalogTone
  rank?: number
}

export type DetailField = {
  label: string
  value: ReactNode
}
