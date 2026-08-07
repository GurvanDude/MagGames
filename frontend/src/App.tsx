import { AppHeader } from './components/AppHeader'
import { HomeView } from './view/HomeView'
import { LibraryView } from './view/LibraryView'
import { SuggestionsView } from './view/SuggestionsView'
import { RankingView } from './view/RankingView'
import { useAppController } from './hooks/useAppController'
import './App.css'

function App() {
  const controller = useAppController()

  return (
    <main className={`dashboard-page view-${controller.view}`}>
      <AppHeader {...controller.header} />

      {controller.view === 'home' && <HomeView {...controller.home} />}
      {controller.view === 'library' && <LibraryView {...controller.library} />}
      {controller.view === 'suggestions' && (
        <SuggestionsView {...controller.suggestions} />
      )}
      {controller.view === 'ranking' && <RankingView {...controller.ranking} />}
    </main>
  )
}

export default App
