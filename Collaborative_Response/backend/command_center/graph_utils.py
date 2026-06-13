from __future__ import annotations

from pathlib import Path

import osmnx as ox


BASE_DIR = Path(__file__).resolve().parent
# 本地缓存仅用于加速已知区域的反复推演。
# 若新场景坐标不在缓存范围内，请删除对应 .graphml 文件或将其移走，
# 脚本会自动从 OSM 拉取新路网。
GRAPH_CANDIDATES = (
    # BASE_DIR / "wuhan_drive_network.graphml",
    # BASE_DIR / "wuhan_drive_full.graphml",
)


def load_drive_graph_from_local_or_osm(
    point: tuple[float, float],
    *,
    dist: int | float,
    network_type: str = "drive",
    simplify: bool = False,
):
    for graph_path in GRAPH_CANDIDATES:
        if graph_path.exists():
            try:
                return ox.load_graphml(graph_path)
            except Exception:
                continue

    return ox.graph_from_point(point, dist=dist, network_type=network_type, simplify=simplify)
