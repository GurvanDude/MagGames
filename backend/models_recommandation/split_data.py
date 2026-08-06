from pathlib import Path

import pandas as pd

BASE_DIR = Path(__file__).resolve().parent
FEATURES_DIR = BASE_DIR / "data" / "features"

SEED = 42


def main():
    interactions = pd.read_csv(FEATURES_DIR / "interactions.csv")

    counts = interactions.groupby("steamid")["appid"].transform("count")
    eligible = interactions[counts >= 2]
    print(
        f"{(counts < 2).sum()} utilisateurs a une seule interaction, exclus du split (gardes en train)"
    )

    shuffled = eligible.sample(frac=1, random_state=SEED)
    test = shuffled.groupby("steamid", sort=False).head(1)
    train = interactions.drop(test.index)

    train.to_csv(FEATURES_DIR / "train_interactions.csv", index=False)
    test.to_csv(FEATURES_DIR / "test_interactions.csv", index=False)

    print(
        f"train : {len(train)} interactions, {train['steamid'].nunique()} utilisateurs"
    )
    print(f"test  : {len(test)} interactions (1 par utilisateur eligible)")


if __name__ == "__main__":
    main()
