import { useEffect, useState } from 'react'
import type { AppView } from '../components/AppHeader'
import { getGameDetails, getLibrary } from '../api/library'
import { getRecommendations, getRelatedRecommendations } from '../api/recommendation'
import { getRanking } from '../api/rankings'
import {
  getCurrentProfile,
  getSteamIdLookupUrl,
  getSteamProfileById,
  getSteamLoginUrl,
  logoutFromSteam as logoutSteamAccount,
} from '../api/steam'
import type { GameDetails, LibraryResponse } from '../model/library'
import type { RecommendationGame, RecommendationResponse } from '../model/recommendation'
import type { RankingResponse, RankingType } from '../model/ranking'
import type { SteamProfile } from '../model/steam'
import { getCatalogColumnCount } from '../utils/catalog'

const errorMessages: Record<string, string> = {
  connexion: 'La connexion Steam a echoue. Relance la connexion pour reessayer.',
  'cle-steam': 'La cle API Steam manque dans le fichier .env du backend.',
  'api-steam': 'Steam a refuse ou mal repondu pendant la recuperation du profil.',
  'profil-steam': 'Steam a valide la connexion, mais aucun profil joueur n a ete renvoye.',
  'steamid-invalide': 'Le SteamID64 doit contenir exactement 17 chiffres.',
}

function getViewFromPath(pathname: string): AppView {
  if (pathname === '/library') {
    return 'library'
  }

  if (pathname === '/suggestions') {
    return 'suggestions'
  }

  if (pathname === '/classement') {
    return 'ranking'
  }

  return 'home'
}

function getPathFromView(view: AppView) {
  if (view === 'home') {
    return '/home'
  }

  if (view === 'ranking') {
    return '/classement'
  }

  return `/${view}`
}

function getErrorMessage(error: unknown, fallback: string) {
  return error instanceof Error ? error.message : fallback
}

function isAbortError(error: unknown) {
  return error instanceof Error && error.name === 'AbortError'
}

export function useAppController() {
  const params = new URLSearchParams(window.location.search)
  const isConnectedFromSteam = params.get('connecte') === '1'
  const lookupSteamId = params.get('lookup_steamid')
  const isLookupMode = Boolean(lookupSteamId)
  const errorCode = params.get('erreur')
  const errorMessage = errorCode ? errorMessages[errorCode] : null

  const [view, setView] = useState<AppView>(() => getViewFromPath(window.location.pathname))
  const [profile, setProfile] = useState<SteamProfile | null>(null)
  const [profileError, setProfileError] = useState<string | null>(null)
  const [isProfileLoading, setIsProfileLoading] = useState(true)
  const [library, setLibrary] = useState<LibraryResponse | null>(null)
  const [isLibraryLoading, setIsLibraryLoading] = useState(false)
  const [libraryError, setLibraryError] = useState<string | null>(null)
  const [libraryPage, setLibraryPage] = useState(1)
  const [librarySearch, setLibrarySearch] = useState('')
  const [librarySearchQuery, setLibrarySearchQuery] = useState('')
  const [selectedGameId, setSelectedGameId] = useState<number | null>(null)
  const [selectedRecommendationId, setSelectedRecommendationId] = useState<number | null>(null)
  const [gameDetails, setGameDetails] = useState<Record<number, GameDetails>>({})
  const [gameDetailsLoading, setGameDetailsLoading] = useState(false)
  const [gameDetailsError, setGameDetailsError] = useState<string | null>(null)
  const [recommendations, setRecommendations] = useState<RecommendationResponse | null>(null)
  const [isRecommendationsLoading, setIsRecommendationsLoading] = useState(false)
  const [recommendationError, setRecommendationError] = useState<string | null>(null)
  const [relatedRecommendations, setRelatedRecommendations] = useState<
    Record<number, RecommendationGame[]>
  >({})
  const [isRelatedLoading, setIsRelatedLoading] = useState(false)
  const [relatedError, setRelatedError] = useState<string | null>(null)
  const [rankings, setRankings] = useState<RankingResponse | null>(null)
  const [isRankingsLoading, setIsRankingsLoading] = useState(false)
  const [rankingError, setRankingError] = useState<string | null>(null)
  const [rankingType, setRankingType] = useState<RankingType>('joues')
  const [rankingGenre, setRankingGenre] = useState('tous')
  const [selectedRankingId, setSelectedRankingId] = useState<number | null>(null)
  const [catalogColumns, setCatalogColumns] = useState(getCatalogColumnCount)

  function navigateTo(nextView: AppView, preserveLookup = true) {
    const lookupQuery = preserveLookup && lookupSteamId
      ? `?lookup_steamid=${encodeURIComponent(lookupSteamId)}`
      : ''
    const nextPath = `${getPathFromView(nextView)}${lookupQuery}`

    if (`${window.location.pathname}${window.location.search}` !== nextPath) {
      window.history.pushState({}, '', nextPath)
    }

    setView(nextView)
  }

  function loginWithSteam() {
    window.location.href = getSteamLoginUrl()
  }

  function loginWithSteamId(steamId: string) {
    window.location.href = getSteamIdLookupUrl(steamId)
  }

  function goToLibraryPage(nextPage: number) {
    setSelectedGameId(null)
    setGameDetailsError(null)
    setLibraryPage(nextPage)
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }

  function handleLibrarySearchChange(value: string) {
    setSelectedGameId(null)
    setGameDetailsError(null)
    setLibrarySearch(value)
  }

  function toggleGameDetails(appid: number) {
    setGameDetailsError(null)
    setRelatedError(null)
    setSelectedGameId((current) => (current === appid ? null : appid))
  }

  function handleRankingTypeChange(nextType: RankingType) {
    setRankingType(nextType)
    setSelectedRankingId(null)
  }

  function handleRankingGenreChange(nextGenre: string) {
    setRankingGenre(nextGenre)
    setSelectedRankingId(null)
  }

  async function handleLogout() {
    try {
      if (!isLookupMode) {
        await logoutSteamAccount()
      }
    } catch {
      // The local UI is reset even if the server session has already expired.
    } finally {
      setProfile(null)
      setLibrary(null)
      setProfileError(null)
      setLibraryError(null)
      setLibraryPage(1)
      setLibrarySearch('')
      setLibrarySearchQuery('')
      setSelectedGameId(null)
      setSelectedRecommendationId(null)
      setGameDetails({})
      setGameDetailsLoading(false)
      setGameDetailsError(null)
      setRecommendations(null)
      setIsRecommendationsLoading(false)
      setRecommendationError(null)
      setRelatedRecommendations({})
      setIsRelatedLoading(false)
      setRelatedError(null)
      setRankings(null)
      setIsRankingsLoading(false)
      setRankingError(null)
      setRankingType('joues')
      setRankingGenre('tous')
      setSelectedRankingId(null)
      navigateTo('home', false)
    }
  }

  useEffect(() => {
    if (window.location.pathname === '/') {
      window.history.replaceState({}, '', '/home')
    }

    function handlePopState() {
      setView(getViewFromPath(window.location.pathname))
    }

    window.addEventListener('popstate', handlePopState)

    return () => {
      window.removeEventListener('popstate', handlePopState)
    }
  }, [])

  useEffect(() => {
    function updateCatalogColumns() {
      setCatalogColumns(getCatalogColumnCount())
    }

    window.addEventListener('resize', updateCatalogColumns)

    return () => {
      window.removeEventListener('resize', updateCatalogColumns)
    }
  }, [])

  useEffect(() => {
    const timeout = window.setTimeout(() => {
      setLibrarySearchQuery(librarySearch.trim())
      setLibraryPage(1)
    }, 300)

    return () => {
      window.clearTimeout(timeout)
    }
  }, [librarySearch])

  useEffect(() => {
    if (!lookupSteamId) {
      return
    }

    const steamId = lookupSteamId
    const controller = new AbortController()
    let isCurrentRequest = true

    async function loadLookupProfile() {
      setIsProfileLoading(true)
      setProfile(null)
      setProfileError(null)

      try {
        const data = await getSteamProfileById(steamId, controller.signal)

        if (isCurrentRequest) {
          setProfile(data)
        }
      } catch (error) {
        if (isCurrentRequest && !isAbortError(error)) {
          setProfileError(
            getErrorMessage(error, 'Impossible de recuperer ce profil Steam.'),
          )
        }
      } finally {
        if (isCurrentRequest) {
          setIsProfileLoading(false)
        }
      }
    }

    void loadLookupProfile()

    return () => {
      isCurrentRequest = false
      controller.abort()
    }
  }, [lookupSteamId])

  useEffect(() => {
    if (lookupSteamId || profile) {
      return
    }

    const controller = new AbortController()
    let isCurrentRequest = true

    async function loadProfile() {
      setIsProfileLoading(true)

      try {
        const data = await getCurrentProfile(controller.signal)

        if (isCurrentRequest) {
          setProfile(data)
          setProfileError(null)
        }
      } catch (error) {
        if (isCurrentRequest && !isAbortError(error) && isConnectedFromSteam) {
          setProfileError(
            getErrorMessage(error, 'Impossible de recuperer le profil Steam.'),
          )
        }
      } finally {
        if (isCurrentRequest) {
          setIsProfileLoading(false)
        }
      }
    }

    void loadProfile()

    return () => {
      isCurrentRequest = false
      controller.abort()
    }
  }, [isConnectedFromSteam, lookupSteamId, profile])

  useEffect(() => {
    if (!profile || selectedGameId === null || gameDetails[selectedGameId]) {
      return
    }

    const controller = new AbortController()
    let isCurrentRequest = true
    const appid = selectedGameId

    async function loadGameDetails() {
      setGameDetailsLoading(true)
      setGameDetailsError(null)

      try {
        const data = await getGameDetails(
          appid,
          lookupSteamId ?? undefined,
          controller.signal,
        )

        if (isCurrentRequest) {
          setGameDetails((current) => ({ ...current, [appid]: data }))
        }
      } catch (error) {
        if (isCurrentRequest && !isAbortError(error)) {
          setGameDetailsError(
            getErrorMessage(error, 'Impossible de charger les details du jeu.'),
          )
        }
      } finally {
        if (isCurrentRequest) {
          setGameDetailsLoading(false)
        }
      }
    }

    void loadGameDetails()

    return () => {
      isCurrentRequest = false
      controller.abort()
    }
  }, [gameDetails, lookupSteamId, profile, selectedGameId])

  useEffect(() => {
    if (
      !profile ||
      selectedGameId === null ||
      relatedRecommendations[selectedGameId]
    ) {
      return
    }

    const controller = new AbortController()
    let isCurrentRequest = true
    const appid = selectedGameId

    async function loadRelatedRecommendations() {
      setIsRelatedLoading(true)
      setRelatedError(null)

      try {
        const data = await getRelatedRecommendations(
          appid,
          lookupSteamId ?? undefined,
          controller.signal,
        )

        if (isCurrentRequest) {
          setRelatedRecommendations((current) => ({
            ...current,
            [appid]: data.recommendations,
          }))
        }
      } catch (error) {
        if (isCurrentRequest && !isAbortError(error)) {
          setRelatedError(getErrorMessage(error, 'Suggestions liees indisponibles.'))
        }
      } finally {
        if (isCurrentRequest) {
          setIsRelatedLoading(false)
        }
      }
    }

    void loadRelatedRecommendations()

    return () => {
      isCurrentRequest = false
      controller.abort()
    }
  }, [lookupSteamId, profile, relatedRecommendations, selectedGameId])

  useEffect(() => {
    if (!profile) {
      return
    }

    const controller = new AbortController()
    let isCurrentRequest = true

    async function loadLibrary() {
      setIsLibraryLoading(true)
      setLibraryError(null)

      try {
        const data = await getLibrary(
          libraryPage,
          librarySearchQuery,
          lookupSteamId ?? undefined,
          controller.signal,
        )

        if (isCurrentRequest) {
          setLibrary(data)
        }
      } catch (error) {
        if (isCurrentRequest && !isAbortError(error)) {
          setLibraryError(getErrorMessage(error, 'Impossible de charger la bibliotheque.'))
        }
      } finally {
        if (isCurrentRequest) {
          setIsLibraryLoading(false)
        }
      }
    }

    void loadLibrary()

    return () => {
      isCurrentRequest = false
      controller.abort()
    }
  }, [libraryPage, librarySearchQuery, lookupSteamId, profile])

  useEffect(() => {
    if (!profile || view !== 'suggestions' || recommendations) {
      return
    }

    const controller = new AbortController()
    let isCurrentRequest = true

    async function loadRecommendations() {
      setIsRecommendationsLoading(true)
      setRecommendationError(null)

      try {
        const data = await getRecommendations(
          20,
          lookupSteamId ?? undefined,
          controller.signal,
        )

        if (isCurrentRequest) {
          setRecommendations(data)
          setSelectedRecommendationId(null)
        }
      } catch (error) {
        if (isCurrentRequest && !isAbortError(error)) {
          setRecommendationError(
            getErrorMessage(error, 'Impossible de charger les suggestions.'),
          )
        }
      } finally {
        if (isCurrentRequest) {
          setIsRecommendationsLoading(false)
        }
      }
    }

    void loadRecommendations()

    return () => {
      isCurrentRequest = false
      controller.abort()
    }
  }, [lookupSteamId, profile, recommendations, view])

  useEffect(() => {
    if (view !== 'ranking') {
      return
    }

    const controller = new AbortController()
    let isCurrentRequest = true

    async function loadRanking() {
      setIsRankingsLoading(true)
      setRankingError(null)

      try {
        const data = await getRanking(rankingType, rankingGenre, controller.signal)

        if (isCurrentRequest) {
          setRankings(data)
          setSelectedRankingId(null)
        }
      } catch (error) {
        if (isCurrentRequest && !isAbortError(error)) {
          setRankingError(
            getErrorMessage(error, 'Impossible de charger le classement Steam.'),
          )
        }
      } finally {
        if (isCurrentRequest) {
          setIsRankingsLoading(false)
        }
      }
    }

    void loadRanking()

    return () => {
      isCurrentRequest = false
      controller.abort()
    }
  }, [rankingGenre, rankingType, view])

  return {
    view,
    header: {
      activeView: view,
      profile,
      isLookupMode,
      onNavigate: navigateTo,
      onLogin: loginWithSteam,
      onLogout: handleLogout,
    },
    home: {
      profile,
      isLookupMode,
      library,
      errorMessage,
      profileError,
      onLogin: loginWithSteam,
      onLoginWithId: loginWithSteamId,
      onNavigate: navigateTo,
    },
    library: {
      profile,
      isLookupMode,
      isProfileLoading,
      library,
      isLibraryLoading,
      libraryError,
      librarySearch,
      catalogColumns,
      selectedGameId,
      gameDetails,
      gameDetailsLoading,
      gameDetailsError,
      relatedRecommendations,
      isRelatedLoading,
      relatedError,
      onLogin: loginWithSteam,
      onPageChange: goToLibraryPage,
      onSearchChange: handleLibrarySearchChange,
      onSelectGame: toggleGameDetails,
      onCloseGame: () => setSelectedGameId(null),
    },
    suggestions: {
      profile,
      isLookupMode,
      isProfileLoading,
      profileError,
      recommendations,
      isRecommendationsLoading,
      recommendationError,
      catalogColumns,
      selectedRecommendationId,
      onLogin: loginWithSteam,
      onSelectRecommendation: setSelectedRecommendationId,
      onCloseRecommendation: () => setSelectedRecommendationId(null),
    },
    ranking: {
      rankings,
      isRankingsLoading,
      rankingError,
      rankingType,
      rankingGenre,
      catalogColumns,
      selectedRankingId,
      onRankingTypeChange: handleRankingTypeChange,
      onRankingGenreChange: handleRankingGenreChange,
      onSelectRanking: setSelectedRankingId,
      onCloseRanking: () => setSelectedRankingId(null),
    },
  }
}
