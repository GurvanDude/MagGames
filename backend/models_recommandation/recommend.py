from functools import lru_cache
from pathlib import Path

import faiss
import numpy as np
import pandas as pd
import torch

from two_tower import TwoTowerModel

EXPORT_DIR = Path(__file__).resolve().parent / "data" / "export"
MAX_HISTORY = 200
EMBEDDING_DIM = 128
HIDDEN_DIM = 256


@lru_cache(maxsize=1)
def _load():
    item_features = np.load(EXPORT_DIR / "item_features.npy")
    appid_index = pd.read_csv(EXPORT_DIR / "item_appid_index.csv")
    appid_to_row = dict(zip(appid_index["appid"], appid_index["row"]))
    row_to_appid = dict(zip(appid_index["row"], appid_index["appid"]))

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = TwoTowerModel(
        item_features.shape[1], embedding_dim=EMBEDDING_DIM, hidden_dim=HIDDEN_DIM
    ).to(device)
    model.load_state_dict(torch.load(EXPORT_DIR / "model.pt", map_location=device))
    model.eval()

    index = faiss.read_index(str(EXPORT_DIR / "item_index.faiss"))

    return item_features, appid_to_row, row_to_appid, model, device, index


def get_recommendations(
    owned_appids: list[int], playtimes: dict[int, int] | None = None, top_k: int = 10
) -> list[int]:
    """Retourne jusqu'a top_k appid recommandes (jeux deja possedes exclus)."""
    item_features, appid_to_row, row_to_appid, model, device, index = _load()
    playtimes = playtimes or {}

    pairs = [
        (appid_to_row[a], playtimes.get(a, 0))
        for a in owned_appids
        if a in appid_to_row
    ]
    if not pairs:
        return (
            []
        )  # pas d'historique exploitable : le caller peut retomber sur une recommandation par popularite

    pairs.sort(key=lambda x: -x[1])
    pairs = pairs[:MAX_HISTORY]
    rows = [r for r, _ in pairs]
    n = len(rows)

    features = np.zeros((1, MAX_HISTORY, item_features.shape[1]), dtype="float32")
    weights = np.zeros((1, MAX_HISTORY), dtype="float32")
    mask = np.zeros((1, MAX_HISTORY), dtype="float32")

    features[0, :n] = item_features[rows]
    weights[0, :n] = [np.log1p(max(w, 0)) for _, w in pairs]
    mask[0, :n] = 1.0

    with torch.no_grad():
        user_embedding = model.user_tower(
            torch.from_numpy(features).to(device),
            torch.from_numpy(weights).to(device),
            torch.from_numpy(mask).to(device),
        )

    query = user_embedding.cpu().numpy().astype("float32")
    _, candidate_rows = index.search(query, top_k + n)

    owned_set = set(rows)
    recommended = []
    for row in candidate_rows[0]:
        if row < 0 or row in owned_set:
            continue
        recommended.append(int(row_to_appid[row]))
        if len(recommended) >= top_k:
            break

    return recommended
