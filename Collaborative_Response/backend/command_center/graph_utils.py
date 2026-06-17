from __future__ import annotations

import hashlib
from pathlib import Path

import osmnx as ox


BASE_DIR = Path(__file__).resolve().parent
CACHE_DIR = BASE_DIR / "cache"
CACHE_DIR.mkdir(exist_ok=True)

# 已损坏的缓存文件列表（零字节或其他无效文件）
BROKEN_CACHE_FILES = {
    CACHE_DIR / "graph_1441b4f147eb.graphml",
    CACHE_DIR / "graph_35ac6f6c3f19.graphml",
}


def _cleanup_broken_cache():
    for f in BROKEN_CACHE_FILES:
        if f.exists():
            f.unlink(missing_ok=True)


_cleanup_broken_cache()


def _cache_path(center: tuple[float, float], dist: int | float, network_type: str) -> Path:
    key = f"{center[0]:.4f}_{center[1]:.4f}_{int(dist)}_{network_type}"
    name = hashlib.sha256(key.encode()).hexdigest()[:12]
    return CACHE_DIR / f"graph_{name}.graphml"


def _cache_path_bbox(north: float, south: float, east: float, west: float, network_type: str) -> Path:
    key = f"bbox_{north:.3f}_{south:.3f}_{east:.3f}_{west:.3f}_{network_type}"
    name = hashlib.sha256(key.encode()).hexdigest()[:12]
    return CACHE_DIR / f"graph_{name}.graphml"


def load_drive_graph_from_local_or_osm(
    point: tuple[float, float],
    *,
    dist: int | float,
    network_type: str = "drive",
    simplify: bool = False,
):
    # 1. 查找本地 GraphML 缓存
    cache_file = _cache_path(point, dist, network_type)
    if cache_file.exists():
        try:
            print(f"  [缓存命中] 从本地加载路网: {cache_file.name}")
            return ox.load_graphml(cache_file)
        except Exception:
            cache_file.unlink(missing_ok=True)

    # 2. 从 OSM 拉取
    print(f"  [OSM下载] 正在从 OpenStreetMap 拉取路网 (中心={point}, 半径≈{dist/1000:.0f}km)...")
    G = ox.graph_from_point(point, dist=dist, network_type=network_type, simplify=simplify)

    # 3. 保存缓存供后续使用
    try:
        ox.save_graphml(G, cache_file)
        print(f"  [缓存保存] 路网已缓存至: {cache_file.name}")
    except Exception:
        pass

    return G


def load_drive_graph_bbox(
    north: float,
    south: float,
    east: float,
    west: float,
    *,
    network_type: str = "drive",
    simplify: bool = False,
):
    """通过 bounding box 下载路网，适合长距离路径（比圆形区域小 70%+）。"""
    cache_file = _cache_path_bbox(north, south, east, west, network_type)
    if cache_file.exists():
        try:
            print(f"  [缓存命中] 从本地加载路网(bbox): {cache_file.name}")
            return ox.load_graphml(cache_file)
        except Exception:
            cache_file.unlink(missing_ok=True)

    print(f"  [OSM下载] 正在从 OSM 拉取路网 (bbox: N={north:.3f} S={south:.3f} E={east:.3f} W={west:.3f})...")
    G = ox.graph_from_bbox(bbox=(north, south, east, west), network_type=network_type, simplify=simplify)

    try:
        ox.save_graphml(G, cache_file)
        print(f"  [缓存保存] 路网已缓存至: {cache_file.name}")
    except Exception:
        pass

    return G
