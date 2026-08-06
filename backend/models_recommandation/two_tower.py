import torch
import torch.nn as nn
import torch.nn.functional as F


class ItemTower(nn.Module):
    def __init__(self, input_dim: int, embedding_dim: int = 128, hidden_dim: int = 256):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, embedding_dim),
        )

    def forward(self, item_features: torch.Tensor) -> torch.Tensor:
        # item_features : (batch, input_dim)
        embedding = self.net(item_features)
        return F.normalize(embedding, dim=-1)


class UserTower(nn.Module):
    """
    Embedding utilisateur a partir de l'historique de jeux possedes,
    en reutilisant la tour item pour encoder chaque jeu de l'historique puis en
    faisant une moyenne ponderee par le temps de jeu.
    """

    def __init__(self, item_tower: ItemTower):
        super().__init__()
        self.item_tower = item_tower

    def forward(
        self,
        history_features: torch.Tensor,  # (batch, max_history, input_dim)
        history_weights: torch.Tensor,  # (batch, max_history) - log(1+playtime), 0 si padding
        history_mask: torch.Tensor,  # (batch, max_history) - 1 si jeu reel, 0 si padding
    ) -> torch.Tensor:
        batch, max_history, input_dim = history_features.shape

        flat_features = history_features.view(batch * max_history, input_dim)
        flat_embeddings = self.item_tower(flat_features)
        embeddings = flat_embeddings.view(batch, max_history, -1)

        weights = (history_weights * history_mask).unsqueeze(
            -1
        )  # (batch, max_history, 1)
        weighted_sum = (embeddings * weights).sum(dim=1)
        total_weight = weights.sum(dim=1).clamp(min=1e-6)
        user_embedding = weighted_sum / total_weight

        return F.normalize(user_embedding, dim=-1)


class TwoTowerModel(nn.Module):
    def __init__(self, input_dim: int, embedding_dim: int = 128, hidden_dim: int = 256):
        super().__init__()
        self.item_tower = ItemTower(input_dim, embedding_dim, hidden_dim)
        self.user_tower = UserTower(self.item_tower)

    def forward(
        self, history_features, history_weights, history_mask, target_item_features
    ):
        user_embedding = self.user_tower(
            history_features, history_weights, history_mask
        )
        item_embedding = self.item_tower(target_item_features)
        return user_embedding, item_embedding

    def score(
        self, user_embedding: torch.Tensor, item_embedding: torch.Tensor
    ) -> torch.Tensor:
        return (user_embedding * item_embedding).sum(dim=-1)


def in_batch_softmax_loss(
    user_embeddings: torch.Tensor,
    item_embeddings: torch.Tensor,
    item_log_q: torch.Tensor | None = None,
    temperature: float = 0.1,
) -> torch.Tensor:
    """
    item_log_q : log(probabilite d'echantillonnage) de chaque item du batch (meme ordre
    que item_embeddings). Corrige le biais du in-batch sampling : un jeu populaire sert
    de negatif beaucoup plus souvent (proportionnellement a sa frequence), ce qui pousse
    le modele a le sous-noter si on ne corrige pas (Yi et al., 2019).
    """
    logits = user_embeddings @ item_embeddings.T / temperature  # (batch, batch)
    if item_log_q is not None:
        logits = logits - item_log_q.unsqueeze(0)  # correction par colonne (candidat)
    labels = torch.arange(logits.size(0), device=logits.device)
    return F.cross_entropy(logits, labels)
