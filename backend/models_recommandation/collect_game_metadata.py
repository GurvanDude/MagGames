import csv
import time
from pathlib import Path

import requests

BASE_DIR = Path(__file__).resolve().parent
OWNED_GAMES_CSV = BASE_DIR / "data" / "owned_games.csv"
OUTPUT_CSV = BASE_DIR / "data" / "game_metadata.csv"

DELAY_SECONDS = 1.5


def get_unique_appids() -> set[str]:
    with open(OWNED_GAMES_CSV, newline="", encoding="utf-8") as f:
        return {row["appid"] for row in csv.DictReader(f) if row["appid"]}


def load_already_done() -> set[str]:
    if not OUTPUT_CSV.exists():
        return set()
    with open(OUTPUT_CSV, newline="", encoding="utf-8") as f:
        return {row["appid"] for row in csv.DictReader(f)}


def get_app_details(appid: str, max_retries: int = 3) -> dict | None:
    url = "https://store.steampowered.com/api/appdetails"
    params = {"appids": appid, "cc": "fr", "l": "french"}

    for attempt in range(max_retries):
        response = requests.get(url, params=params, timeout=10)
        if response.status_code == 429:
            wait = 30 * (attempt + 1)
            print(f"429 recu pour {appid}, pause {wait}s...")
            time.sleep(wait)
            continue
        response.raise_for_status()
        payload = response.json().get(appid, {})
        return payload["data"] if payload.get("success") else None

    raise RuntimeError(f"Trop de 429 consecutifs pour {appid}")


def main():
    appids = sorted(get_unique_appids(), key=int)
    done = load_already_done()
    todo = [a for a in appids if a not in done]
    print(f"{len(done)} deja traites, {len(todo)} restants")

    file_exists = OUTPUT_CSV.exists()
    with open(OUTPUT_CSV, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(
                [
                    "appid",
                    "name",
                    "genres",
                    "categories",
                    "is_free",
                    "price_eur",
                    "discount_percent",
                    "release_date",
                    "developers",
                    "publishers",
                ]
            )

        for i, appid in enumerate(todo, start=1):
            try:
                data = get_app_details(appid)
            except (requests.RequestException, RuntimeError) as e:
                print(f"[{i}/{len(todo)}] {appid} : erreur {e}")
                time.sleep(DELAY_SECONDS)
                continue

            if data is None:
                writer.writerow([appid, "", "", "", "", "", "", "", "", ""])
                print(f"[{i}/{len(todo)}] {appid} : pas de donnees (retire du store ?)")
                f.flush()
                time.sleep(DELAY_SECONDS)
                continue

            genres = ";".join(g["description"] for g in data.get("genres", []))
            categories = ";".join(c["description"] for c in data.get("categories", []))
            is_free = data.get("is_free", False)
            price = data.get("price_overview", {})
            price_eur = (
                (price.get("final", 0) / 100) if price else (0 if is_free else "")
            )
            discount = price.get("discount_percent", 0) if price else 0
            release_date = data.get("release_date", {}).get("date", "")
            developers = ";".join(data.get("developers", []))
            publishers = ";".join(data.get("publishers", []))

            writer.writerow(
                [
                    appid,
                    data.get("name", ""),
                    genres,
                    categories,
                    is_free,
                    price_eur,
                    discount,
                    release_date,
                    developers,
                    publishers,
                ]
            )
            f.flush()

            print(f"[{i}/{len(todo)}] {appid} : {data.get('name', '?')}")
            time.sleep(DELAY_SECONDS)


if __name__ == "__main__":
    main()
