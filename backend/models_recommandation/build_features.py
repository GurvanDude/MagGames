from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.preprocessing import MultiLabelBinarizer, MinMaxScaler

BASE_DIR = Path(__file__).resolve().parent
CLEAN_DIR = BASE_DIR / "data" / "clean"
FEATURES_DIR = BASE_DIR / "data" / "features"
FEATURES_DIR.mkdir(exist_ok=True)

TOP_K_TAGS = 150


def parse_tags(raw: str) -> dict:
    """'Action:5504|FPS:4929' -> {'Action': 5504, 'FPS': 4929}"""
    result = {}
    if not raw:
        return result
    for entry in raw.split("|"):
        if ":" not in entry:
            continue
        name, count = entry.rsplit(":", 1)
        try:
            result[name] = int(float(count))
        except ValueError:
            continue
    return result


def build_item_features(jeux: pd.DataFrame) -> tuple[np.ndarray, pd.Series]:
    jeux = jeux.reset_index(drop=True)

    # --- genres (multi-hot) ---
    genre_lists = (
        jeux["genre"]
        .fillna("")
        .apply(lambda s: [g.strip() for g in s.split(",") if g.strip()])
    )
    genre_encoder = MultiLabelBinarizer()
    genre_matrix = genre_encoder.fit_transform(genre_lists)
    print(f"genres : {len(genre_encoder.classes_)} valeurs uniques")

    # --- categories (multi-hot) ---
    category_lists = (
        jeux["categories"]
        .fillna("")
        .apply(lambda s: [c.strip() for c in s.split("|") if c.strip()])
    )
    category_encoder = MultiLabelBinarizer()
    category_matrix = category_encoder.fit_transform(category_lists)
    print(f"categories : {len(category_encoder.classes_)} valeurs uniques")

    # --- tags (top-K, pondere par part des votes) ---
    parsed_tags = jeux["tags"].fillna("").apply(parse_tags)
    tag_counts_global = {}
    for tags in parsed_tags:
        for name, count in tags.items():
            tag_counts_global[name] = tag_counts_global.get(name, 0) + count
    top_tags = sorted(tag_counts_global, key=tag_counts_global.get, reverse=True)[
        :TOP_K_TAGS
    ]
    tag_index = {name: i for i, name in enumerate(top_tags)}

    tag_matrix = np.zeros((len(jeux), TOP_K_TAGS), dtype="float32")
    for row, tags in enumerate(parsed_tags):
        total_votes = sum(tags.values()) or 1
        for name, count in tags.items():
            if name in tag_index:
                tag_matrix[row, tag_index[name]] = count / total_votes
    print(f"tags : vocabulaire limite au top {TOP_K_TAGS}")

    # --- plateformes (multi-hot, vocabulaire fixe) ---
    platform_lists = (
        jeux["plateformes"]
        .fillna("")
        .apply(lambda s: [p.strip() for p in s.split("|") if p.strip()])
    )
    platform_encoder = MultiLabelBinarizer()
    platform_matrix = platform_encoder.fit_transform(platform_lists)

    # --- features numeriques ---
    prix = np.log1p(jeux["prix"].fillna(0).clip(lower=0)).to_numpy().reshape(-1, 1)
    prix = MinMaxScaler().fit_transform(prix)

    metacritic = (jeux["metacritic"].fillna(0) / 100).to_numpy().reshape(-1, 1)
    has_metacritic = jeux["has_metacritic"].astype("float32").to_numpy().reshape(-1, 1)

    positifs = jeux["avis_positifs"].fillna(0)
    negatifs = jeux["avis_negatifs"].fillna(0)
    ratio_positif = (positifs / (positifs + negatifs + 1)).to_numpy().reshape(-1, 1)
    popularite = np.log1p(positifs + negatifs).to_numpy().reshape(-1, 1)
    popularite = MinMaxScaler().fit_transform(popularite)

    features = np.hstack(
        [
            genre_matrix,
            category_matrix,
            tag_matrix,
            platform_matrix,
            prix,
            metacritic,
            has_metacritic,
            ratio_positif,
            popularite,
        ]
    ).astype("float32")

    print(f"dimension finale des features jeu : {features.shape[1]}")
    return features, jeux["appid"]


def build_interactions(biblio: pd.DataFrame) -> pd.DataFrame:
    # un jeu possede mais jamais lance n'est pas un signal de gout fiable
    # (et c'est aussi le cas des comptes bundle-hoarders : des dizaines de milliers
    # de jeux a 0 minute, aucun lien avec un vrai interet)
    biblio = biblio[biblio["minutes_jouees"] > 0].copy()

    # reference = mediane du temps joue par les autres joueurs sur CE jeu (calculee sur
    # nos donnees, pas la colonne Steam souvent vide sur les jeux peu populaires)
    reference = biblio.groupby("appid")["minutes_jouees"].transform("median")
    ratio = biblio["minutes_jouees"] / reference
    biblio["poids"] = np.log1p(ratio)

    return biblio[["steamid", "appid", "poids"]]


def main():
    jeux = pd.read_csv(CLEAN_DIR / "jeux.csv", dtype={"tags": str})
    biblio = pd.read_csv(CLEAN_DIR / "bibliotheque.csv")

    item_features, appids = build_item_features(jeux)
    np.save(FEATURES_DIR / "item_features.npy", item_features)
    appids.reset_index(drop=True).rename("appid").to_csv(
        FEATURES_DIR / "item_appid_index.csv", index_label="row"
    )

    interactions = build_interactions(biblio)
    interactions.to_csv(FEATURES_DIR / "interactions.csv", index=False)

    print(
        f"Ecrit : item_features.npy {item_features.shape}, interactions.csv ({len(interactions)} lignes)"
    )


if __name__ == "__main__":
    main()
