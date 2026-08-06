import shutil
from pathlib import Path

import faiss
import numpy as np
import torch

from run_utils import latest_run_dir
from two_tower import TwoTowerModel

BASE_DIR = Path(__file__).resolve().parent
FEATURES_DIR = BASE_DIR / "data" / "features"
EXPORT_DIR = BASE_DIR / "data" / "export"

EMBEDDING_DIM = 128
HIDDEN_DIM = 256


def main():
    run_dir = latest_run_dir()
    print(f"export du run : {run_dir.name}")

    item_features = np.load(FEATURES_DIR / "item_features.npy")
    n_items, dim = item_features.shape

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = TwoTowerModel(dim, embedding_dim=EMBEDDING_DIM, hidden_dim=HIDDEN_DIM).to(
        device
    )
    model.load_state_dict(torch.load(run_dir / "final.pt", map_location=device))
    model.eval()

    with torch.no_grad():
        item_embeddings = model.item_tower(torch.from_numpy(item_features).to(device))
    item_embeddings = item_embeddings.cpu().numpy().astype("float32")

    EXPORT_DIR.mkdir(parents=True, exist_ok=True)

    # embeddings deja normalises (L2) dans le modele -> produit scalaire = similarite cosinus
    index = faiss.IndexFlatIP(item_embeddings.shape[1])
    index.add(item_embeddings)
    faiss.write_index(index, str(EXPORT_DIR / "item_index.faiss"))

    np.save(EXPORT_DIR / "item_embeddings.npy", item_embeddings)
    shutil.copy(FEATURES_DIR / "item_features.npy", EXPORT_DIR / "item_features.npy")
    shutil.copy(
        FEATURES_DIR / "item_appid_index.csv", EXPORT_DIR / "item_appid_index.csv"
    )
    shutil.copy(run_dir / "final.pt", EXPORT_DIR / "model.pt")
    shutil.copy(run_dir / "config.json", EXPORT_DIR / "config.json")

    print(f"exporte dans {EXPORT_DIR} :")
    print(
        "  model.pt, item_embeddings.npy, item_index.faiss, item_features.npy, item_appid_index.csv, config.json"
    )


if __name__ == "__main__":
    main()
