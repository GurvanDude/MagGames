import sys

import matplotlib.pyplot as plt
import pandas as pd

from run_utils import CHECKPOINT_DIR, latest_run_dir


def main():
    run_dir = CHECKPOINT_DIR / sys.argv[1] if len(sys.argv) > 1 else latest_run_dir()
    print(f"run : {run_dir.name}")

    loss_df = pd.read_csv(run_dir / "loss_history.csv")

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(
        loss_df["step"],
        loss_df["loss"],
        linewidth=0.5,
        alpha=0.4,
        label="loss par batch",
    )

    epoch_avg = loss_df.groupby("epoch")["loss"].mean()
    epoch_last_step = loss_df.groupby("epoch")["step"].max()
    ax.plot(
        epoch_last_step, epoch_avg, marker="o", color="red", label="moyenne par epoch"
    )

    ax.set_xlabel("step (batch)")
    ax.set_ylabel("loss")
    ax.set_title(f"Loss d'entrainement Two-Tower - {run_dir.name}")
    ax.legend()
    ax.grid(alpha=0.3)

    out_path = run_dir / "loss_curve.png"
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    print(f"graphique sauvegarde : {out_path}")


if __name__ == "__main__":
    main()
