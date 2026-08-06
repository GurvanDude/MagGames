import csv
import os
import time
from pathlib import Path

import requests
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR.parent.parent / ".env")

STEAM_API_KEY = os.getenv("STEAM_API")
INPUT_CSV = BASE_DIR / "data" / "steam_ids 1.csv"
OUTPUT_CSV = BASE_DIR / "data" / "owned_games.csv"

DELAY_SECONDS = 1.2


def get_owned_games(steamid: str) -> list[dict]:
    url = "https://api.steampowered.com/IPlayerService/GetOwnedGames/v1/"
    params = {
        "key": STEAM_API_KEY,
        "steamid": steamid,
        "include_appinfo": 1,
        "include_played_free_games": 1,
        "format": "json",
    }
    response = requests.get(url, params=params, timeout=10)
    response.raise_for_status()
    return response.json().get("response", {}).get("games", [])


def load_already_done() -> set[str]:
    if not OUTPUT_CSV.exists():
        return set()
    with open(OUTPUT_CSV, newline="", encoding="utf-8") as f:
        return {row["steamid"] for row in csv.DictReader(f)}


def main():
    if not STEAM_API_KEY:
        raise SystemExit("STEAM_API manquant dans .env")

    with open(INPUT_CSV, newline="", encoding="utf-8") as f:
        steamids = [row["Steam_ID"] for row in csv.DictReader(f)]

    done = load_already_done()
    todo = [s for s in steamids if s not in done]
    print(f"{len(done)} deja traites, {len(todo)} restants")

    file_exists = OUTPUT_CSV.exists()
    with open(OUTPUT_CSV, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(["steamid", "appid", "name", "playtime_forever"])

        for i, steamid in enumerate(todo, start=1):
            try:
                games = get_owned_games(steamid)
            except requests.RequestException as e:
                print(f"[{i}/{len(todo)}] {steamid} : erreur {e}")
                time.sleep(DELAY_SECONDS)
                continue

            if not games:
                # profil prive ou sans jeux : on marque quand meme comme traite
                writer.writerow([steamid, "", "", ""])
            for game in games:
                writer.writerow(
                    [
                        steamid,
                        game["appid"],
                        game.get("name", ""),
                        game.get("playtime_forever", 0),
                    ]
                )
            f.flush()

            print(f"[{i}/{len(todo)}] {steamid} : {len(games)} jeux")
            time.sleep(DELAY_SECONDS)


if __name__ == "__main__":
    main()
