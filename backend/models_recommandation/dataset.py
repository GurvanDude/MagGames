from pathlib import Path

import numpy as np
import pandas as pd
import torch
from torch.utils.data import DataLoader, Dataset

BASE_DIR = Path(__file__).resolve().parent
FEATURES_DIR = BASE_DIR / "data" / "features"

MAX_HISTORY = 200


class TwoTowerDataset(Dataset):
    def __init__(
        self,
        interactions_csv: Path,
        item_features: np.ndarray,
        appid_to_row: dict,
        max_history: int = MAX_HISTORY,
    ):
        self.max_history = max_history
        self.dim = dim = item_features.shape[1]

        interactions = pd.read_csv(interactions_csv)
        interactions["row"] = interactions["appid"].map(appid_to_row)
        interactions = interactions.dropna(subset=["row"])
        interactions["row"] = interactions["row"].astype(int)

        user_groups = list(interactions.groupby("steamid"))

        # precalcule l'historique (features/poids/masque) de chaque utilisateur une
        # seule fois : un utilisateur contribue jusqu'a max_history exemples, inutile
        # de re-extraire les memes lignes de item_features a chaque __getitem__
        self.history_features = np.zeros((len(user_groups), max_history, dim), dtype="float32")
        self.history_weights = np.zeros((len(user_groups), max_history), dtype="float32")
        self.history_mask = np.zeros((len(user_groups), max_history), dtype="float32")
        # ligne (index dans item_features) de chaque jeu de l'historique : necessaire
        # pour retrouver quel jeu est la cible d'un exemple (ex: correction logQ)
        self.history_rows = np.zeros((len(user_groups), max_history), dtype="int64")
        self.examples: list[tuple[int, int]] = []

        user_idx = 0
        for _, group in user_groups:
            group = group.sort_values("poids", ascending=False).head(max_history)
            n = len(group)
            if n < 2:
                continue

            rows = group["row"].to_numpy()
            self.history_features[user_idx, :n] = item_features[rows]
            self.history_weights[user_idx, :n] = group["poids"].to_numpy(dtype="float32")
            self.history_mask[user_idx, :n] = 1.0
            self.history_rows[user_idx, :n] = rows
            self.examples.extend((user_idx, pos) for pos in range(n))
            user_idx += 1

        # coupe l'espace alloue en trop pour les utilisateurs exclus (< 2 interactions)
        self.history_features = self.history_features[:user_idx]
        self.history_weights = self.history_weights[:user_idx]
        self.history_mask = self.history_mask[:user_idx]
        self.history_rows = self.history_rows[:user_idx]

        ram_go = self.history_features.nbytes / 1e9
        print(f"dataset : {len(self.examples)} exemples, {user_idx} utilisateurs, {ram_go:.2f} Go en RAM")

    def __len__(self) -> int:
        return len(self.examples)

    def __getitem__(self, idx: int):
        user_idx, target_pos = self.examples[idx]

        mask = self.history_mask[user_idx].copy()
        mask[target_pos] = 0.0  # exclut la cible de son propre historique

        history_features = self.history_features[user_idx]
        target_features = history_features[target_pos]
        weights = self.history_weights[user_idx]

        return (
            torch.from_numpy(history_features),
            torch.from_numpy(weights),
            torch.from_numpy(mask),
            torch.from_numpy(target_features),
        )


def load_dataset(split: str, max_history: int = MAX_HISTORY) -> TwoTowerDataset:
    """split : 'train' ou 'test'"""
    item_features = np.load(FEATURES_DIR / "item_features.npy")
    appid_index = pd.read_csv(FEATURES_DIR / "item_appid_index.csv")
    appid_to_row = dict(zip(appid_index["appid"], appid_index["row"]))

    csv_path = FEATURES_DIR / f"{split}_interactions.csv"
    return TwoTowerDataset(csv_path, item_features, appid_to_row, max_history)


if __name__ == "__main__":
    dataset = load_dataset("train")
    loader = DataLoader(dataset, batch_size=1024, shuffle=True, num_workers=0)

    history_features, history_weights, history_mask, target_features = next(
        iter(loader)
    )
    print("history_features:", history_features.shape)
    print("history_weights :", history_weights.shape)
    print("history_mask    :", history_mask.shape)
    print("target_features :", target_features.shape)
