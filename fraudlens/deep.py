"""Deep-learning baselines (Papers 1, 2, 10 and 12 in the literature set).

* MLP: a standard feed-forward network with class weighting.
* 1D-CNN: the transaction's feature vector is treated as a one-channel
  sequence so convolutions can learn local feature interactions, the same
  idea as reshaping tabular data for a CNN in Paper 1.

Both use a positive-class weight in the loss and early stopping on
validation PR-AUC. They exist to test, on the same data and split, whether
deep learning beats gradient-boosted trees on tabular transactions.
"""
from __future__ import annotations

import copy

import numpy as np
import torch
from sklearn.metrics import average_precision_score
from sklearn.preprocessing import StandardScaler
from torch import nn

from . import config


class MLP(nn.Module):
    def __init__(self, d: int):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(d, 256), nn.BatchNorm1d(256), nn.ReLU(), nn.Dropout(0.2),
            nn.Linear(256, 128), nn.BatchNorm1d(128), nn.ReLU(), nn.Dropout(0.2),
            nn.Linear(128, 64), nn.ReLU(), nn.Linear(64, 1),
        )

    def forward(self, x):
        return self.net(x).squeeze(-1)


class CNN1D(nn.Module):
    def __init__(self, d: int):
        super().__init__()
        self.conv = nn.Sequential(
            nn.Conv1d(1, 32, kernel_size=3, padding=1), nn.BatchNorm1d(32), nn.ReLU(),
            nn.Conv1d(32, 64, kernel_size=3, padding=1), nn.BatchNorm1d(64), nn.ReLU(),
            nn.AdaptiveMaxPool1d(8),
        )
        self.head = nn.Sequential(nn.Flatten(), nn.Linear(64 * 8, 128), nn.ReLU(), nn.Dropout(0.2),
                                  nn.Linear(128, 1))

    def forward(self, x):
        return self.head(self.conv(x.unsqueeze(1))).squeeze(-1)


class TorchClassifier:
    def __init__(self, arch: str = "mlp", epochs: int = 15, batch_size: int = 2048, lr: float = 1e-3,
                 patience: int = 3, seed: int = config.SEED):
        self.arch, self.epochs, self.batch_size, self.lr = arch, epochs, batch_size, lr
        self.patience, self.seed = patience, seed
        self.history: list[float] = []

    def _net(self, d: int) -> nn.Module:
        return MLP(d) if self.arch == "mlp" else CNN1D(d)

    def fit(self, X, y, X_val, y_val):
        torch.manual_seed(self.seed)
        torch.set_num_threads(config.N_JOBS)
        self.scaler = StandardScaler().fit(X)
        Xt = torch.tensor(self.scaler.transform(X), dtype=torch.float32)
        yt = torch.tensor(y, dtype=torch.float32)
        Xv = torch.tensor(self.scaler.transform(X_val), dtype=torch.float32)
        self.model = self._net(X.shape[1])
        pw = torch.tensor((len(y) - y.sum()) / max(1, y.sum()), dtype=torch.float32)
        loss_fn = nn.BCEWithLogitsLoss(pos_weight=pw)
        opt = torch.optim.Adam(self.model.parameters(), lr=self.lr, weight_decay=1e-5)
        gen = torch.Generator().manual_seed(self.seed)
        best, best_state, bad = -1.0, None, 0
        for _ in range(self.epochs):
            self.model.train()
            perm = torch.randperm(len(Xt), generator=gen)
            for i in range(0, len(Xt), self.batch_size):
                idx = perm[i:i + self.batch_size]
                opt.zero_grad()
                loss = loss_fn(self.model(Xt[idx]), yt[idx])
                loss.backward()
                opt.step()
            ap = average_precision_score(y_val, self._predict(Xv))
            self.history.append(float(ap))
            if ap > best:
                best, best_state, bad = ap, copy.deepcopy(self.model.state_dict()), 0
            else:
                bad += 1
                if bad >= self.patience:
                    break
        self.model.load_state_dict(best_state)
        return self

    @torch.no_grad()
    def _predict(self, Xt: torch.Tensor) -> np.ndarray:
        self.model.eval()
        out = [torch.sigmoid(self.model(Xt[i:i + 65536])) for i in range(0, len(Xt), 65536)]
        return torch.cat(out).numpy()

    def predict_proba(self, X) -> np.ndarray:
        p = self._predict(torch.tensor(self.scaler.transform(X), dtype=torch.float32))
        return np.column_stack([1 - p, p])
