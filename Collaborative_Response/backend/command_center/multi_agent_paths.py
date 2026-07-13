"""
五类救援智能体 Dijkstra 路径规划模块。
POI 数据从 rescue_points.db 读取，不再实时查询 OSM。
"""
from __future__ import annotations

import json
from pathlib import Path

import networkx as nx
import osmnx as ox
from geopy.distance import geodesic

from graph_utils import load_drive_graph_from_local_or_osm
from rescue_points import get_agent_pois, AGENT_CONFIG

BASE_DIR = Path(__file__).resolve().parent


def find_agent_paths(scenario: str, end_point: tuple) -> dict:
    """
    从数据库读取五类 POI，规划 Dijkstra 路径到事故点。
    返回: { agent_key: { label, color, icon, poi: {name, lat, lon, dist_km}, path: [...] } }
    """
    lat, lon = end_point
    all_pois = get_agent_pois(scenario)

    if not all_pois:
        return {}

    # 计算直线距离并加载路网
    for p in all_pois:
        p["dist_km"] = round(geodesic((p["lat"], p["lon"]), (lat, lon)).kilometers, 2)

    graph = load_drive_graph_from_local_or_osm((lat, lon), dist=30000, network_type="drive")
    dest_node = ox.nearest_nodes(graph, lon, lat)

    # 按类型分组，每组选最近的一个计算路径
    from collections import defaultdict
    by_type = defaultdict(list)
    for p in all_pois:
        by_type[p["agent_key"]].append(p)

    results = {}
    for agent_key, pois in by_type.items():
        pois.sort(key=lambda x: x["dist_km"])
        best = pois[0]  # 最近的
        cfg = AGENT_CONFIG.get(agent_key, {})

        path = None
        try:
            orig_node = ox.nearest_nodes(graph, best["lon"], best["lat"])
            route = nx.shortest_path(graph, orig_node, dest_node, weight="length")
            path = [(graph.nodes[n]["y"], graph.nodes[n]["x"]) for n in route]
        except nx.NetworkXNoPath:
            pass

        results[agent_key] = {
            "label": cfg.get("label", agent_key),
            "color": cfg.get("color", "#888"),
            "icon": cfg.get("icon", "flag"),
            "poi": {
                "name": best["name"],
                "lat": best["lat"],
                "lon": best["lon"],
                "dist_km": best["dist_km"],
            },
            "path": path,
        }

    return results


def save_multi_agent_result(scenario: str, results: dict) -> Path:
    """保存多智能体结果到 JSON。"""
    output = {"scenario": scenario, "agents": {}}
    for key, val in results.items():
        poi = val.get("poi")
        output["agents"][key] = {
            "label": val["label"],
            "color": val["color"],
            "icon": val["icon"],
            "poi": poi,
            "has_path": val.get("path") is not None,
        }
    result_path = BASE_DIR / "multi_agent_result.json"
    with open(result_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    return result_path
