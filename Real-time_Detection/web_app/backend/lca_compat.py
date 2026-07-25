"""Runtime compatibility for LCA-YOLO26 checkpoints."""

from __future__ import annotations

import torch
import torch.nn as nn


def register_lca_modules() -> None:
    """Register LCA-YOLO26 custom layer in the active Ultralytics process."""
    import ultralytics.nn.modules as modules
    import ultralytics.nn.modules.block as block
    from ultralytics.nn.modules.conv import Conv

    if hasattr(block, "LCA"):
        return

    class LCA(nn.Module):
        """Leak-aware coordinate attention for lightweight neck feature calibration."""

        def __init__(self, c1: int, c2: int, reduction: int = 32):
            super().__init__()
            self.proj = Conv(c1, c2, 1, 1) if c1 != c2 else nn.Identity()
            hidden = max(8, c2 // reduction)
            self.pool_h = nn.AdaptiveAvgPool2d((None, 1))
            self.pool_w = nn.AdaptiveAvgPool2d((1, None))
            self.conv1 = Conv(c2, hidden, 1, 1)
            self.conv_h = nn.Conv2d(hidden, c2, 1, 1, 0)
            self.conv_w = nn.Conv2d(hidden, c2, 1, 1, 0)
            self.gamma = nn.Parameter(torch.zeros(1))

        def forward(self, x: torch.Tensor) -> torch.Tensor:
            x = self.proj(x)
            _, _, h, w = x.shape
            x_h = self.pool_h(x)
            x_w = self.pool_w(x).permute(0, 1, 3, 2)
            y = self.conv1(torch.cat((x_h, x_w), dim=2))
            a_h, a_w = torch.split(y, [h, w], dim=2)
            a_w = a_w.permute(0, 1, 3, 2)
            a_h = self.conv_h(a_h).sigmoid()
            a_w = self.conv_w(a_w).sigmoid()
            return x * (1.0 + self.gamma * a_h * a_w)

    LCA.__module__ = block.__name__
    block.LCA = LCA
    modules.LCA = LCA

    try:
        import ultralytics.nn.tasks as tasks
        tasks.LCA = LCA
    except Exception:
        pass

    try:
        torch.serialization.add_safe_globals([LCA])
    except Exception:
        pass
