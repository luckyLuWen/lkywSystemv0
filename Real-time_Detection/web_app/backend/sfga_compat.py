"""Runtime compatibility for SFGA-YOLO26 checkpoints.

The SFGA-YOLO26M checkpoint was trained with custom Ultralytics modules
(`SFGA` and `C3k2SFGA`). The production environment uses the stock
Ultralytics package, so these classes must be registered before loading
the checkpoint.
"""

from __future__ import annotations

import torch
import torch.nn as nn
import torch.nn.functional as F


def register_sfga_modules() -> None:
    """Register SFGA-YOLO26 custom layers in the active Ultralytics process."""
    import ultralytics.nn.modules as modules
    import ultralytics.nn.modules.block as block
    from ultralytics.nn.modules.block import C3k2
    from ultralytics.nn.modules.conv import Conv

    if hasattr(block, "C3k2SFGA") and hasattr(block, "SFGA"):
        return

    class SFGA(nn.Module):
        """Smoke-Flame Guided Attention for smoke/fire occlusion and tiny flame cues."""

        def __init__(self, c1: int, c2: int, k: int = 7, reduction: int = 16, residual: bool = True):
            super().__init__()
            if k not in (3, 5, 7, 9):
                raise ValueError(f"SFGA kernel size k must be one of (3, 5, 7, 9), got {k}.")

            self.proj = Conv(c1, c2, 1, 1) if c1 != c2 else nn.Identity()
            hidden = max(c2 // reduction, 8)
            self.channel_mlp = nn.Sequential(
                nn.Conv2d(c2, hidden, 1, bias=True),
                nn.SiLU(inplace=True),
                nn.Conv2d(hidden, c2, 1, bias=True),
            )
            self.spatial_attn = nn.Sequential(
                nn.Conv2d(2, 1, kernel_size=k, stride=1, padding=k // 2, bias=False),
                nn.Sigmoid(),
            )
            self.edge_attn = nn.Sequential(
                nn.Conv2d(c2, c2, kernel_size=3, stride=1, padding=1, groups=c2, bias=False),
                nn.Conv2d(c2, c2, kernel_size=1, stride=1, bias=True),
                nn.Sigmoid(),
            )
            self.residual = residual
            self.gamma = nn.Parameter(torch.zeros(1))

        def forward(self, x: torch.Tensor) -> torch.Tensor:
            x = self.proj(x)

            avg_pool = F.adaptive_avg_pool2d(x, 1)
            max_pool = F.adaptive_max_pool2d(x, 1)
            channel_gate = torch.sigmoid(self.channel_mlp(avg_pool) + self.channel_mlp(max_pool))

            avg_map = x.mean(dim=1, keepdim=True)
            max_map = x.amax(dim=1, keepdim=True)
            spatial_gate = self.spatial_attn(torch.cat((avg_map, max_map), dim=1))

            local_mean = F.avg_pool2d(x, kernel_size=3, stride=1, padding=1, count_include_pad=False)
            edge_gate = self.edge_attn((x - local_mean).abs())

            y = x * channel_gate * spatial_gate * edge_gate
            return x + self.gamma * y if self.residual else y

    class C3k2SFGA(C3k2):
        """C3k2 block followed by SFGA for SFGA-YOLO26 neck features."""

        def __init__(
            self,
            c1: int,
            c2: int,
            n: int = 1,
            c3k: bool = False,
            e: float = 0.5,
            attn: bool = False,
            g: int = 1,
            shortcut: bool = True,
            k: int = 7,
            reduction: int = 16,
        ):
            super().__init__(c1, c2, n, c3k, e, g, shortcut)
            self.sfga = SFGA(c2, c2, k=k, reduction=reduction, residual=True)

        def forward(self, x: torch.Tensor) -> torch.Tensor:
            return self.sfga(super().forward(x))

    SFGA.__module__ = block.__name__
    C3k2SFGA.__module__ = block.__name__

    block.SFGA = SFGA
    block.C3k2SFGA = C3k2SFGA
    modules.SFGA = SFGA
    modules.C3k2SFGA = C3k2SFGA

    try:
        import ultralytics.nn.tasks as tasks

        tasks.SFGA = SFGA
        tasks.C3k2SFGA = C3k2SFGA
    except Exception:
        pass

    try:
        torch.serialization.add_safe_globals([SFGA, C3k2SFGA])
    except Exception:
        pass
