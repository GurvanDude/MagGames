import './App.css'

const API_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

const errorMessages: Record<string, string> = {
  connexion: 'La connexion Steam a echoue. Relance la connexion pour reessayer.',
  'openid-reseau': 'Le backend n arrive pas a verifier la connexion aupres de Steam.',
  'openid-invalide': 'Steam n a pas valide cette tentative. Repars de ce bouton et evite de recharger la page Steam.',
  'steamid-invalide': 'Steam a repondu, mais le SteamID renvoye n est pas reconnu.',
  'cle-steam': 'La cle API Steam manque dans le fichier .env du backend.',
  'api-steam': 'Steam a refuse ou mal repondu pendant la recuperation du profil.',
  'profil-steam': 'Steam a valide la connexion, mais aucun profil joueur n a ete renvoye.',
}

function App() {
  const params = new URLSearchParams(window.location.search)
  const isConnected = params.get('connecte') === '1'
  const errorCode = params.get('erreur')
  const errorMessage = errorCode ? errorMessages[errorCode] : null

  function loginWithSteam() {
    window.location.href = `${API_URL}/api/auth/steam/login/`
  }

  return (
    <main className="home-page">
      <section className="home-panel" aria-labelledby="home-title">
        <p className="eyebrow">MagGames</p>
        <h1 id="home-title">Trouve ton prochain jeu Steam</h1>
        <p className="intro">
          Connecte ton compte Steam pour recuperer ta bibliotheque et preparer
          des recommandations basees sur tes vrais jeux.
        </p>

        <button className="steam-button" type="button" onClick={loginWithSteam}>
          Se connecter avec Steam
        </button>

        {isConnected && (
          <p className="status success">
            Connexion Steam reussie. La bibliotheque arrive a la prochaine etape.
          </p>
        )}

        {errorMessage && <p className="status error">{errorMessage}</p>}
      </section>
    </main>
  )
}

export default App
