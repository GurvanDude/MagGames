import json
import time
from pathlib import Path

import pandas as pd
import torch

from dataset import load_dataset
from two_tower import TwoTowerModel, in_batch_softmax_loss

BASE_DIR = Path(__file__).resolve().parent
FEATURES_DIR = BASE_DIR / "data" / "features"
CHECKPOINT_DIR = BASE_DIR / "checkpoints"

BATCH_SIZE = 2048
EPOCHS = 30
LEARNING_RATE = 1e-3
EMBEDDING_DIM = 128
HIDDEN_DIM = 256


def main():
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"device : {device}")

    run_id = time.strftime("%Y%m%d_%H%M%S")
    run_dir = CHECKPOINT_DIR / run_id
    run_dir.mkdir(parents=True)
    print(f"run : {run_id} (checkpoints/{run_id}/)")

    train_dataset = load_dataset("train")

    history_features = torch.from_numpy(train_dataset.history_features).to(device)
    history_weights = torch.from_numpy(train_dataset.history_weights).to(device)
    history_mask = torch.from_numpy(train_dataset.history_mask).to(device)
    examples = torch.tensor(train_dataset.examples, dtype=torch.long, device=device)
    print(
        f"donnees transferees sur {device} ({history_features.element_size() * history_features.nelement() / 1e9:.2f} Go)"
    )

    n_examples = examples.shape[0]
    n_batches = (n_examples + BATCH_SIZE - 1) // BATCH_SIZE

    config = {
        "batch_size": BATCH_SIZE,
        "epochs": EPOCHS,
        "learning_rate": LEARNING_RATE,
        "embedding_dim": EMBEDDING_DIM,
        "hidden_dim": HIDDEN_DIM,
        "max_history": train_dataset.max_history,
        "input_dim": train_dataset.dim,
        "n_examples": n_examples,
        "n_users": history_features.shape[0],
    }
    (run_dir / "config.json").write_text(json.dumps(config, indent=2))

    model = TwoTowerModel(
        train_dataset.dim, embedding_dim=EMBEDDING_DIM, hidden_dim=HIDDEN_DIM
    ).to(device)
    optimizer = torch.optim.Adam(model.parameters(), lr=LEARNING_RATE)

    loss_history = []  # (step, epoch, batch, loss)
    step = 0

    for epoch in range(1, EPOCHS + 1):
        model.train()
        total_loss = 0.0
        epoch_start = time.time()

        order = torch.randperm(n_examples, device=device)

        for batch_idx in range(n_batches):
            batch_positions = order[
                batch_idx * BATCH_SIZE : (batch_idx + 1) * BATCH_SIZE
            ]
            user_idx = examples[batch_positions, 0]
            target_pos = examples[batch_positions, 1]
            b = user_idx.shape[0]
            arange_b = torch.arange(b, device=device)

            batch_history_features = history_features[user_idx]
            batch_history_weights = history_weights[user_idx]
            batch_mask = history_mask[user_idx].clone()
            batch_mask[arange_b, target_pos] = 0.0

            batch_target_features = batch_history_features[arange_b, target_pos]

            user_embeddings, item_embeddings = model(
                batch_history_features,
                batch_history_weights,
                batch_mask,
                batch_target_features,
            )
            loss = in_batch_softmax_loss(user_embeddings, item_embeddings)

            optimizer.zero_grad()
            loss.backward()
            optimizer.step()

            loss_value = loss.item()
            total_loss += loss_value
            step += 1
            loss_history.append((step, epoch, batch_idx + 1, loss_value))

            if (batch_idx + 1) % 50 == 0:
                print(
                    f"  epoch {epoch} - batch {batch_idx + 1}/{n_batches} - loss {loss_value:.4f}"
                )

        avg_loss = total_loss / n_batches
        elapsed = time.time() - epoch_start
        print(
            f"epoch {epoch}/{EPOCHS} - loss moyenne : {avg_loss:.4f} - duree : {elapsed:.0f}s ({n_batches / elapsed:.1f} batches/s)"
        )
        torch.save(model.state_dict(), run_dir / f"epoch_{epoch:03d}.pt")

    torch.save(model.state_dict(), run_dir / "final.pt")

    loss_df = pd.DataFrame(loss_history, columns=["step", "epoch", "batch", "loss"])
    loss_df.to_csv(run_dir / "loss_history.csv", index=False)

    print(
        f"Entrainement termine, run sauvegarde dans checkpoints/{run_id}/ (final.pt, config.json, loss_history.csv)"
    )


if __name__ == "__main__":
    main()
