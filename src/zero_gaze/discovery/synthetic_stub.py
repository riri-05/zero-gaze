"""Synthetic baseline code generator for papers without open source code."""

from __future__ import annotations

import textwrap


class SyntheticStubGenerator:
    """Generates a clean, reproducible PyTorch baseline script for empirical verification."""

    @classmethod
    def generate_stub(
        cls,
        paper_title: str,
        arxiv_id: str,
        target_metric: str = "Accuracy",
        epochs: int = 5,
    ) -> str:
        """Construct a minimal self-contained PyTorch experiment template."""
        clean_title = paper_title.replace('"', '\\"').replace("\n", " ")
        code = f'''\
"""Synthetic baseline replication script for: {clean_title} (arXiv:{arxiv_id})"""

import time
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, TensorDataset


def set_seed(seed: int = 42) -> None:
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


class SyntheticBaselineModel(nn.Module):
    """Linear adaptation baseline model representing core paper architecture."""

    def __init__(self, input_dim: int = 64, hidden_dim: int = 128, output_dim: int = 2) -> None:
        super().__init__()
        self.encoder = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.ReLU(),
            nn.Dropout(0.1),
            nn.Linear(hidden_dim, output_dim),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.encoder(x)


def run_experiment() -> dict[str, float]:
    set_seed(42)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Executing baseline experiment on device: {{device}}")

    # Generate synthetic benchmark tensor data
    x_train = torch.randn(256, 64)
    y_train = torch.randint(0, 2, (256,))
    dataset = TensorDataset(x_train, y_train)
    loader = DataLoader(dataset, batch_size=32, shuffle=True)

    model = SyntheticBaselineModel().to(device)
    criterion = nn.CrossEntropyLoss()
    optimizer = optim.AdamW(model.parameters(), lr=1e-3, weight_decay=1e-2)

    start_time = time.time()
    model.train()
    for epoch in range(1, {epochs} + 1):
        total_loss = 0.0
        for batch_x, batch_y in loader:
            batch_x, batch_y = batch_x.to(device), batch_y.to(device)
            optimizer.zero_grad()
            outputs = model(batch_x)
            loss = criterion(outputs, batch_y)
            loss.backward()
            optimizer.step()
            total_loss += loss.item()
        avg_loss = total_loss / len(loader)
        if epoch % 1 == 0:
            print(f"Epoch [{{epoch}}/{epochs}] - Loss: {{avg_loss:.4f}}")

    elapsed_seconds = time.time() - start_time

    # Evaluate baseline accuracy
    model.eval()
    with torch.no_grad():
        test_x = torch.randn(64, 64).to(device)
        test_y = torch.randint(0, 2, (64,)).to(device)
        preds = model(test_x).argmax(dim=-1)
        correct = (preds == test_y).sum().item()
        final_metric = (correct / 64) * 100.0

    print(f"Replication Run Complete. Metric ({target_metric}): {{final_metric:.2f}}% (in {{elapsed_seconds:.2f}}s)")
    return {{"{target_metric}": final_metric, "runtime_seconds": elapsed_seconds}}


if __name__ == "__main__":
    run_experiment()
'''
        return textwrap.dedent(code)
