from pathlib import Path

import numpy as np
import pandas as pd
import torch

from run_utils import latest_run_dir
from two_tower import TwoTowerModel

BASE_DIR = Path(__file__).resolve().parent
FEATURES_DIR = BASE_DIR / "data" / "features"

MAX_HISTORY = 200
EMBEDDING_DIM = 128
HIDDEN_DIM = 256
K_VALUES = [10, 20, 50]
EVAL_BATCH = 512


def build_user_histories(
    train_interactions: pd.DataFrame, max_history: int = MAX_HISTORY
):
    """Par steamid : historique plafonne (pour l'embedding) + ensemble complet possede (pour le masquage)."""
    capped_rows, capped_weights, full_owned = {}, {}, {}

    for steamid, group in train_interactions.groupby("steamid"):
        full_owned[steamid] = group["row"].to_numpy()

        top = group.sort_values("poids", ascending=False).head(max_history)
        capped_rows[steamid] = top["row"].to_numpy()
        capped_weights[steamid] = top["poids"].to_numpy(dtype="float32")

    return capped_rows, capped_weights, full_owned


def main():
    item_features = np.load(FEATURES_DIR / "item_features.npy")
    appid_index = pd.read_csv(FEATURES_DIR / "item_appid_index.csv")
    appid_to_row = dict(zip(appid_index["appid"], appid_index["row"]))
    n_items, dim = item_features.shape

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"device : {device}")

    run_dir = latest_run_dir()
    print(f"run evalue : {run_dir.name}")

    model = TwoTowerModel(dim, embedding_dim=EMBEDDING_DIM, hidden_dim=HIDDEN_DIM).to(
        device
    )
    model.load_state_dict(
        torch.load(run_dir / "final.pt", map_location=device)
    )
    model.eval()

    item_features_gpu = torch.from_numpy(item_features).to(device)
    with torch.no_grad():
        item_embeddings = model.item_tower(
            item_features_gpu
        )  # (n_items, embedding_dim)

    train_interactions = pd.read_csv(FEATURES_DIR / "train_interactions.csv")
    train_interactions["row"] = train_interactions["appid"].map(appid_to_row)
    train_interactions = train_interactions.dropna(subset=["row"])
    train_interactions["row"] = train_interactions["row"].astype(int)

    # baseline : popularite = nb de fois qu'un jeu apparait dans le train
    popularity = np.zeros(n_items, dtype="float32")
    counts = train_interactions["row"].value_counts()
    popularity[counts.index.to_numpy()] = counts.to_numpy()
    popularity_gpu = torch.from_numpy(popularity).to(device)

    capped_rows, capped_weights, full_owned = build_user_histories(train_interactions)

    test_interactions = pd.read_csv(FEATURES_DIR / "test_interactions.csv")
    test_interactions["row"] = test_interactions["appid"].map(appid_to_row)
    test_interactions = test_interactions.dropna(subset=["row"])
    test_interactions["row"] = test_interactions["row"].astype(int)
    test_interactions = test_interactions[
        test_interactions["steamid"].isin(capped_rows)
    ]
    rows = test_interactions.to_dict("records")

    print(f"evaluation sur {len(rows)} utilisateurs")

    hits_model = {k: 0 for k in K_VALUES}
    ndcg_model = {k: 0.0 for k in K_VALUES}
    hits_pop = {k: 0 for k in K_VALUES}
    ndcg_pop = {k: 0.0 for k in K_VALUES}

    for start in range(0, len(rows), EVAL_BATCH):
        chunk = rows[start : start + EVAL_BATCH]
        b = len(chunk)

        history_features = np.zeros((b, MAX_HISTORY, dim), dtype="float32")
        history_weights = np.zeros((b, MAX_HISTORY), dtype="float32")
        history_mask = np.zeros((b, MAX_HISTORY), dtype="float32")

        for i, r in enumerate(chunk):
            item_rows = capped_rows[r["steamid"]]
            n = len(item_rows)
            history_features[i, :n] = item_features[item_rows]
            history_weights[i, :n] = capped_weights[r["steamid"]]
            history_mask[i, :n] = 1.0

        history_features_t = torch.from_numpy(history_features).to(device)
        history_weights_t = torch.from_numpy(history_weights).to(device)
        history_mask_t = torch.from_numpy(history_mask).to(device)

        with torch.no_grad():
            user_embeddings = model.user_tower(
                history_features_t, history_weights_t, history_mask_t
            )
            scores = user_embeddings @ item_embeddings.T  # (b, n_items)

        scores_pop = popularity_gpu.unsqueeze(0).expand(b, -1).clone()

        # on ne peut pas recommander un jeu deja possede : on l'exclut du classement
        for i, r in enumerate(chunk):
            owned = full_owned.get(r["steamid"])
            if owned is not None and len(owned) > 0:
                owned_t = torch.from_numpy(owned).to(device)
                scores[i, owned_t] = -1e9
                scores_pop[i, owned_t] = -1e9

        target_rows = torch.tensor([r["row"] for r in chunk], device=device)
        arange_b = torch.arange(b, device=device)
        target_scores = scores[arange_b, target_rows]
        target_scores_pop = scores_pop[arange_b, target_rows]

        rank_model = (scores > target_scores.unsqueeze(1)).sum(dim=1) + 1
        rank_pop = (scores_pop > target_scores_pop.unsqueeze(1)).sum(dim=1) + 1

        for k in K_VALUES:
            hits_model[k] += (rank_model <= k).sum().item()
            ndcg_model[k] += (
                (1.0 / torch.log2(rank_model[rank_model <= k].float() + 1)).sum().item()
            )
            hits_pop[k] += (rank_pop <= k).sum().item()
            ndcg_pop[k] += (
                (1.0 / torch.log2(rank_pop[rank_pop <= k].float() + 1)).sum().item()
            )

        print(f"  {start + b}/{len(rows)} utilisateurs evalues")

    n = len(rows)
    print("\nresultats (modele Two-Tower vs baseline popularite) :")
    for k in K_VALUES:
        print(
            f"  Recall@{k} : modele {hits_model[k]/n:.4f} | popularite {hits_pop[k]/n:.4f}"
        )
        print(
            f"  NDCG@{k}   : modele {ndcg_model[k]/n:.4f} | popularite {ndcg_pop[k]/n:.4f}"
        )


if __name__ == "__main__":
    main()
