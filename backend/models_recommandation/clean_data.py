from pathlib import Path

import pandas as pd

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
CLEAN_DIR = DATA_DIR / "clean"
CLEAN_DIR.mkdir(exist_ok=True)


def clean_joueurs() -> pd.DataFrame:
    joueurs = pd.read_csv(DATA_DIR / "joueurs.csv")
    public = joueurs[joueurs["statut"] == "public"].copy()
    public = public.drop_duplicates(subset="steamid")
    return public


def clean_bibliotheque(public_steamids: set) -> pd.DataFrame:
    biblio = pd.read_csv(DATA_DIR / "bibliotheque.csv")

    biblio = biblio[biblio["steamid"].isin(public_steamids)]
    biblio = biblio.dropna(subset=["appid"])

    biblio = biblio.groupby(["steamid", "appid"], as_index=False).agg(
        minutes_jouees=("minutes_jouees", "max"),
        minutes_2semaines=("minutes_2semaines", "max"),
    )
    return biblio


def clean_jeux() -> pd.DataFrame:
    jeux = pd.read_csv(DATA_DIR / "jeux.csv")
    jeux = jeux.drop_duplicates(subset="appid")

    jeux["has_metacritic"] = jeux["metacritic"] > 0
    for col in ["prix", "genre", "categories", "tags", "developpeur", "editeur"]:
        jeux[col] = jeux[col].fillna("" if jeux[col].dtype == object else 0)

    # sans genre/categorie/tag, la tour item n'a aucun signal de contenu a apprendre
    has_content = (
        (jeux["genre"] != "") | (jeux["categories"] != "") | (jeux["tags"] != "")
    )
    jeux = jeux[has_content]

    return jeux


def main():
    joueurs = clean_joueurs()
    print(f"joueurs : {len(joueurs)} profils publics")

    biblio = clean_bibliotheque(set(joueurs["steamid"]))
    print(f"bibliotheque : {len(biblio)} interactions apres dedup")

    jeux = clean_jeux()
    print(f"jeux : {len(jeux)} jeux avec contenu exploitable")

    # garder dans bibliotheque que des jeux presents dans jeux nettoye
    biblio = biblio[biblio["appid"].isin(jeux["appid"])]
    print(f"bibliotheque : {len(biblio)} interactions apres filtrage sur jeux valides")

    joueurs.to_csv(CLEAN_DIR / "joueurs.csv", index=False)
    biblio.to_csv(CLEAN_DIR / "bibliotheque.csv", index=False)
    jeux.to_csv(CLEAN_DIR / "jeux.csv", index=False)
    print(f"Fichiers nettoyes ecrits dans {CLEAN_DIR}")


if __name__ == "__main__":
    main()
