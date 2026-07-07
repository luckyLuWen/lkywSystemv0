import pandas as pd
import numpy as np
import folium
import osmnx as ox
import networkx as nx
from folium.plugins import TimestampedGeoJson
import warnings
from datetime import datetime, timezone
from geopy.distance import geodesic
import os 
from scipy.interpolate import splprep, splev 
import json
import argparse
from graph_utils import load_drive_graph_from_local_or_osm, load_drive_graph_bbox

warnings.filterwarnings("ignore")

# ==================== 1. 接收前端指令与全局配置 ====================
parser = argparse.ArgumentParser()
parser.add_argument('--ugv_block', type=int, default=1)
parser.add_argument('--uav_smoke', type=int, default=1)
# 默认策略设为 RCD 逆向推演以展示最佳效果
parser.add_argument('--strategy', type=str, default='rcd')
parser.add_argument('--end_point', type=str, default='leak', choices=['leak', 'crash'],
                    help='终点选择: leak=油罐车泄露现场, crash=货车追尾现场')
parser.add_argument('--compare', type=int, default=0,
                    help='是否开启对比模式: 1=同时生成基线算法路径进行对比')
args = parser.parse_args()

UGV_BLOCKED = (args.ugv_block == 1)
UAV_SMOKE = (args.uav_smoke == 1)
SYNC_STRATEGY = str(args.strategy).strip().lower()
COMPARE = (args.compare == 1)

CAR_SPEED = 22.22  # 80 km/h (长途救援真实车速)
UAV_SPEED = 20.0   # 20 m/s (大型救援无人机)

# 起点按终点分别配置：不同灾情场景由最近的消防站出警
START_POINTS = {
    'leak':  (30.510, 114.920),                           # 黄冈市黄州区路口镇专职消防队
    'crash': (30.380, 113.150),                           # 仙桃市郑场镇专职消防队
}
START_POINT_NAMES = {
    'leak':  '黄冈市黄州区路口镇专职消防队',
    'crash': '仙桃市郑场镇专职消防队',
}

END_POINTS = {
    'leak':  (30.63101, 114.89209),                       # 油罐车泄漏现场
    'crash': (30.385469, 113.104833),                     # 货车追尾现场
}
END_POINT_NAMES = {
    'leak':  '市区道路-油罐车泄漏现场',
    'crash': '高速公路-货车追尾现场',
}
START_POINT = START_POINTS[args.end_point]
START_POINT_NAME = START_POINT_NAMES[args.end_point]
END_POINT = END_POINTS[args.end_point]
END_POINT_NAME = END_POINT_NAMES[args.end_point]

# 禁飞区 & 拥堵区 — 双层管制体系（核心区+缓冲区），含完整元数据
NFZ_CONFIG = {
    'leak': {
        'nfz': [{  # 核心禁飞区：黄冈城铁站沿线（铁路走廊不规则多边形）
            'polygon': [
                [30.555, 114.890], [30.559, 114.896], [30.564, 114.893],
                [30.571, 114.898], [30.576, 114.904], [30.573, 114.910],
                [30.567, 114.913], [30.560, 114.909], [30.554, 114.913],
                [30.549, 114.907], [30.550, 114.901], [30.552, 114.895],
            ],
            'name': '黄冈城铁站沿线限飞区',
            'level': 'RESTRICTED',
            'ceiling': '300m AGL',
            'reason': '铁路枢纽安全保障',
            'authority': '黄冈市应急管理局',
            'effective': '全时段',
        }],
        'buffer': [{  # 缓冲区（核心区外扩200-400m）
            'polygon': [
                [30.553, 114.887], [30.557, 114.894], [30.562, 114.891],
                [30.569, 114.896], [30.575, 114.902], [30.573, 114.909],
                [30.567, 114.912], [30.561, 114.908], [30.556, 114.912],
                [30.551, 114.908], [30.552, 114.902], [30.554, 114.896],
            ],
        }],
        'congestion': [  # 黄州城区早高峰拥堵区
            [30.526, 114.887], [30.532, 114.895], [30.537, 114.902],
            [30.542, 114.907], [30.548, 114.903], [30.546, 114.895],
            [30.542, 114.888], [30.536, 114.883], [30.529, 114.882],
        ],
        'congestion_name': '黄州城区早高峰拥堵区',
        'congestion_info': '07:00-09:00 常态拥堵 | 通行延时+40%',
    },
    'crash': {
        'nfz': [{  # 核心禁飞区：跨路径中段（迫使UAV绕行）
            'polygon': [
                [30.379, 113.136], [30.381, 113.139], [30.384, 113.138],
                [30.386, 113.134], [30.385, 113.127], [30.383, 113.123],
                [30.380, 113.124], [30.378, 113.128], [30.377, 113.133],
            ],
            'name': '郑场镇中心限飞区',
            'level': 'RESTRICTED',
            'ceiling': '200m AGL',
            'reason': '人口密集区低空安全',
            'authority': '仙桃市应急管理局',
            'effective': '全时段',
        }],
        'buffer': [{  # 缓冲区（外扩250m）
            'polygon': [
                [30.377, 113.138], [30.380, 113.141], [30.385, 113.140],
                [30.388, 113.135], [30.387, 113.126], [30.384, 113.121],
                [30.379, 113.122], [30.376, 113.127], [30.375, 113.133],
            ],
        }],
        'congestion': [  # 集镇集市拥堵区（路径西段，与NFZ不重叠）
            [30.382, 113.115], [30.384, 113.118], [30.387, 113.116],
            [30.386, 113.111], [30.383, 113.109], [30.381, 113.112],
        ],
        'congestion_name': '郑场镇集贸市场拥堵区',
        'congestion_info': '逢集日 06:00-12:00 | 通行延时+60%',
    },
}
NFZ_LIST = NFZ_CONFIG[args.end_point]['nfz']
NEW_NFZ_LIST = NFZ_CONFIG[args.end_point]['buffer']
CONGESTION_ZONE_POLYGON = NFZ_CONFIG[args.end_point]['congestion']
GRID_RES = 100.0   # 适配约35km大范围网格 
START_TIME = pd.Timestamp('2025-01-01 09:00:00')
ANIMATION_INTERVAL = 1.0

# ==================== 2. 辅助与算法 ====================
def calculate_distance(lat1, lon1, lat2, lon2):
    return geodesic((lat1, lon1), (lat2, lon2)).meters

# 统一路网 bbox：覆盖全部起点+终点的矩形走廊，比圆形区域小 70%+，避免切换终点时重复下载
_PAD = 0.05  # 每边约 5km 缓冲
_ALL_LATS = [p[0] for p in START_POINTS.values()] + [p[0] for p in END_POINTS.values()]
_ALL_LONS = [p[1] for p in START_POINTS.values()] + [p[1] for p in END_POINTS.values()]
UNIFIED_BBOX = (
    max(_ALL_LATS) + _PAD,   # north
    min(_ALL_LATS) - _PAD,   # south
    max(_ALL_LONS) + _PAD,   # east
    min(_ALL_LONS) - _PAD,   # west
)

def interpolate_path(df, interval=1.0):
    if len(df) < 2: return df
    max_time = df['time_s'].max()
    time_points = np.arange(0, max_time + interval, interval)
    interp_lat = np.interp(time_points, df['time_s'].values, df['lat'].values)
    interp_lon = np.interp(time_points, df['time_s'].values, df['lon'].values)
    result = pd.DataFrame({'time_s': time_points, 'lat': interp_lat, 'lon': interp_lon})
    if 'alt' in df.columns: 
        result['alt'] = np.interp(time_points, df['time_s'].values, df['alt'].values)
    result['timestamp'] = START_TIME + pd.to_timedelta(result['time_s'], unit='s')
    return result

def b_spline_smooth(waypoints, num_points=200, k=3):
    if len(waypoints) < k + 1: return waypoints
    lats = [p[0] for p in waypoints]
    lons = [p[1] for p in waypoints]
    alts = [p[2] for p in waypoints]
    try:
        tck, u = splprep([lats, lons, alts], s=0.000005, k=k)
        u_new = np.linspace(0, 1, num_points)
        new_points = splev(u_new, tck)
        return [[new_points[0][i], new_points[1][i], new_points[2][i]] for i in range(len(u_new))]
    except:
        return waypoints

def _point_in_polygon(lat, lon, polygon):
    """射线法判断点是否在多边形内。polygon: [[lat, lon], ...]"""
    n = len(polygon)
    inside = False
    j = n - 1
    for i in range(n):
        lat_i, lon_i = polygon[i][0], polygon[i][1]
        lat_j, lon_j = polygon[j][0], polygon[j][1]
        # 水平射线（向东）与多边形边的交点计数
        if ((lat_i > lat) != (lat_j > lat)) and \
           (lon < (lon_j - lon_i) * (lat - lat_i) / (lat_j - lat_i) + lon_i):
            inside = not inside
        j = i
    return inside

# ==================== 3. 路径生成 ====================
def generate_car_path():
    try:
        straight_dist = calculate_distance(START_POINT[0], START_POINT[1], END_POINT[0], END_POINT[1])
        fetch_radius = max(int(straight_dist * 1.15), 5000)  # 至少 5km 半径
        print(f"正在拉取底层真实路网... (半径: {fetch_radius/1000:.1f} km)")
        G = load_drive_graph_from_local_or_osm(
            START_POINT,
            dist=fetch_radius,
            network_type='drive',
            simplify=False,
        )
        lats, lons = [p[0] for p in CONGESTION_ZONE_POLYGON], [p[1] for p in CONGESTION_ZONE_POLYGON]
        min_lat, max_lat, min_lon, max_lon = min(lats), max(lats), min(lons), max(lons)
        for u, v, k, data in G.edges(keys=True, data=True):
            length = data.get('length', 1.0)
            u_node, v_node = G.nodes[u], G.nodes[v]
            if UGV_BLOCKED and ((min_lat <= u_node['y'] <= max_lat and min_lon <= u_node['x'] <= max_lon) or \
               (min_lat <= v_node['y'] <= max_lat and min_lon <= v_node['x'] <= max_lon)):
                data['weight'] = length * 99999
            else:
                data['weight'] = length
        orig = ox.nearest_nodes(G, START_POINT[1], START_POINT[0])
        dest = ox.nearest_nodes(G, END_POINT[1], END_POINT[0])
        route = nx.shortest_path(G, orig, dest, weight='weight')
        path_coords = [(G.nodes[n]['y'], G.nodes[n]['x']) for n in route]
        if path_coords[0][0] != START_POINT[0]: path_coords.insert(0, START_POINT)
        # 确保终点精确对齐到事故点坐标，避免无人机/无人车终点偏离
        if calculate_distance(path_coords[-1][0], path_coords[-1][1], END_POINT[0], END_POINT[1]) > 10:
            path_coords.append(END_POINT)
        df = pd.DataFrame(path_coords, columns=['lat', 'lon'])
        df['dist'] = 0.0
        for i in range(1, len(df)): df.loc[i, 'dist'] = calculate_distance(df.loc[i-1,'lat'], df.loc[i-1,'lon'], df.loc[i,'lat'], df.loc[i,'lon'])
        total_time = df['dist'].sum() / CAR_SPEED
        df['time_s'] = np.linspace(0, total_time, len(df))
        df['timestamp'] = START_TIME + pd.to_timedelta(df['time_s'], unit='s')
        return df, total_time, G
    except Exception as e:
        print(f"  [错误] 车辆路径规划失败: {e}")
        import traceback
        traceback.print_exc()
        df = pd.DataFrame([START_POINT, END_POINT], columns=['lat', 'lon'])
        df['dist'] = [0, calculate_distance(START_POINT[0], START_POINT[1], END_POINT[0], END_POINT[1])]
        df['time_s'] = [0, df['dist'].sum() / CAR_SPEED]
        df['timestamp'] = [START_TIME, START_TIME + pd.to_timedelta(df['time_s'].iloc[-1], unit='s')]
        return df, df['time_s'].iloc[-1], None

def generate_uav_path(car_time):
    pad = 0.05
    min_lat, max_lat = min(START_POINT[0], END_POINT[0]) - pad, max(START_POINT[0], END_POINT[0]) + pad
    min_lon, max_lon = min(START_POINT[1], END_POINT[1]) - pad, max(START_POINT[1], END_POINT[1]) + pad
    rows, cols = int(calculate_distance(min_lat, min_lon, max_lat, min_lon) / GRID_RES), int(calculate_distance(min_lat, min_lon, min_lat, max_lon) / GRID_RES)
    grid = np.zeros((rows, cols), dtype=int)
    
    if UAV_SMOKE:
        for nfz in NFZ_LIST + NEW_NFZ_LIST:
            if 'polygon' in nfz:
                poly = nfz['polygon']
                for ri in range(rows):
                    for ci in range(cols):
                        cell_lat = min_lat + (ri / rows) * (max_lat - min_lat)
                        cell_lon = min_lon + (ci / cols) * (max_lon - min_lon)
                        if _point_in_polygon(cell_lat, cell_lon, poly):
                            grid[ri][ci] = 1
            else:
                r = int((nfz['center'][0] - min_lat) / (max_lat - min_lat) * rows)
                c = int((nfz['center'][1] - min_lon) / (max_lon - min_lon) * cols)
                rad_grid = int(nfz['radius'] * 1.1 / GRID_RES)
                y, x = np.ogrid[-r:rows-r, -c:cols-c]
                grid[x*x + y*y <= rad_grid*rad_grid] = 1
            
    start_node = (min(rows-1, int((START_POINT[0] - min_lat) / (max_lat - min_lat) * rows)), min(cols-1, int((START_POINT[1] - min_lon) / (max_lon - min_lon) * cols)))
    end_node = (min(rows-1, int((END_POINT[0] - min_lat) / (max_lat - min_lat) * rows)), min(cols-1, int((END_POINT[1] - min_lon) / (max_lon - min_lon) * cols)))
    G = nx.grid_2d_graph(rows, cols)
    G.add_edges_from([((x, y), (x+1, y+1)) for x in range(rows-1) for y in range(cols-1)] + [((x+1, y), (x, y+1)) for x in range(rows-1) for y in range(cols-1)], weight=1.414)
    G.remove_nodes_from([n for n in G.nodes if grid[n[0]][n[1]] == 1])
    try: path = nx.astar_path(G, start_node, end_node, heuristic=lambda a, b: ((a[0]-b[0])**2 + (a[1]-b[1])**2)**0.5)
    except: path = [start_node, end_node]

    raw_waypoints = [[min_lat + (r / rows) * (max_lat - min_lat), min_lon + (c / cols) * (max_lon - min_lon), 100] for r, c in path]
    raw_df = pd.DataFrame(raw_waypoints, columns=['lat', 'lon', 'alt'])
    smooth_waypoints = b_spline_smooth(raw_waypoints, num_points=len(raw_waypoints)*5, k=3)
    # 确保无人机起/终点精确对齐，与无人车一致
    if smooth_waypoints:
        smooth_waypoints[0][0] = START_POINT[0]
        smooth_waypoints[0][1] = START_POINT[1]
        smooth_waypoints[-1][0] = END_POINT[0]
        smooth_waypoints[-1][1] = END_POINT[1]
    df = pd.DataFrame(smooth_waypoints, columns=['lat', 'lon', 'alt'])

    total_dist = sum([calculate_distance(df.iloc[i-1]['lat'], df.iloc[i-1]['lon'], df.iloc[i]['lat'], df.iloc[i]['lon']) for i in range(1, len(df))])
    fly_time = total_dist / UAV_SPEED

    # 计算延迟
    if SYNC_STRATEGY == 'independent':
        delay = 0.0
    else:
        delay = max(0, car_time - fly_time)

    df['time_s'] = np.linspace(0, fly_time, len(df)) + delay
    df['timestamp'] = START_TIME + pd.to_timedelta(df['time_s'], unit='s')
    return df, raw_df, delay

# ==================== 3b. 基线对比算法 ====================
def generate_car_path_bfs(G=None):
    """基线算法：BFS — 最少边数路径，忽略道路长度权重，对比 Dijkstra 加权最短路径"""
    try:
        if G is None:
            straight_dist = calculate_distance(START_POINT[0], START_POINT[1], END_POINT[0], END_POINT[1])
            fetch_radius = max(int(straight_dist * 1.15), 5000)
            G = load_drive_graph_from_local_or_osm(
                START_POINT, dist=fetch_radius, network_type='drive', simplify=False,
            )
        lats, lons = [p[0] for p in CONGESTION_ZONE_POLYGON], [p[1] for p in CONGESTION_ZONE_POLYGON]
        min_lat, max_lat, min_lon, max_lon = min(lats), max(lats), min(lons), max(lons)
        blocked_edges = set()
        for u, v, k, data in G.edges(keys=True, data=True):
            u_node, v_node = G.nodes[u], G.nodes[v]
            if UGV_BLOCKED and ((min_lat <= u_node['y'] <= max_lat and min_lon <= u_node['x'] <= max_lon) or \
               (min_lat <= v_node['y'] <= max_lat and min_lon <= v_node['x'] <= max_lon)):
                blocked_edges.add((u, v))
        if UGV_BLOCKED:
            G.remove_edges_from(blocked_edges)
        orig = ox.nearest_nodes(G, START_POINT[1], START_POINT[0])
        dest = ox.nearest_nodes(G, END_POINT[1], END_POINT[0])
        route = nx.shortest_path(G, orig, dest, weight=None)  # BFS: weight=None = 所有边权重为1
        path_coords = [(G.nodes[n]['y'], G.nodes[n]['x']) for n in route]
        if path_coords[0][0] != START_POINT[0]: path_coords.insert(0, START_POINT)
        # 确保终点精确对齐到事故点坐标，避免无人机/无人车终点偏离
        if calculate_distance(path_coords[-1][0], path_coords[-1][1], END_POINT[0], END_POINT[1]) > 10:
            path_coords.append(END_POINT)
        df = pd.DataFrame(path_coords, columns=['lat', 'lon'])
        df['dist'] = 0.0
        for i in range(1, len(df)): df.loc[i, 'dist'] = calculate_distance(df.loc[i-1,'lat'], df.loc[i-1,'lon'], df.loc[i,'lat'], df.loc[i,'lon'])
        total_time = df['dist'].sum() / CAR_SPEED
        df['time_s'] = np.linspace(0, total_time, len(df))
        df['timestamp'] = START_TIME + pd.to_timedelta(df['time_s'], unit='s')
        return df, total_time
    except Exception: return pd.DataFrame([START_POINT, END_POINT], columns=['lat', 'lon']), 100

def generate_uav_path_greedy():
    """基线算法：Greedy Best-First — 每次只朝目标方向移动，不考虑全局代价，对比 A* 最优路径"""
    pad = 0.05
    min_lat = min(START_POINT[0], END_POINT[0]) - pad
    max_lat = max(START_POINT[0], END_POINT[0]) + pad
    min_lon = min(START_POINT[1], END_POINT[1]) - pad
    max_lon = max(START_POINT[1], END_POINT[1]) + pad
    rows = int(calculate_distance(min_lat, min_lon, max_lat, min_lon) / GRID_RES)
    cols = int(calculate_distance(min_lat, min_lon, min_lat, max_lon) / GRID_RES)
    grid = np.zeros((rows, cols), dtype=int)
    if UAV_SMOKE:
        for nfz in NFZ_LIST + NEW_NFZ_LIST:
            if 'polygon' in nfz:
                poly = nfz['polygon']
                for ri in range(rows):
                    for ci in range(cols):
                        cell_lat = min_lat + (ri / rows) * (max_lat - min_lat)
                        cell_lon = min_lon + (ci / cols) * (max_lon - min_lon)
                        if _point_in_polygon(cell_lat, cell_lon, poly):
                            grid[ri][ci] = 1
            else:
                r = int((nfz['center'][0] - min_lat) / (max_lat - min_lat) * rows)
                c = int((nfz['center'][1] - min_lon) / (max_lon - min_lon) * cols)
                rad = int(nfz['radius'] * 1.1 / GRID_RES)
                y, x = np.ogrid[-r:rows-r, -c:cols-c]
                grid[x*x + y*y <= rad*rad] = 1
    start_node = (min(rows-1, int((START_POINT[0]-min_lat)/(max_lat-min_lat)*rows)),
                  min(cols-1, int((START_POINT[1]-min_lon)/(max_lon-min_lon)*cols)))
    end_node = (min(rows-1, int((END_POINT[0]-min_lat)/(max_lat-min_lat)*rows)),
                min(cols-1, int((END_POINT[1]-min_lon)/(max_lon-min_lon)*cols)))

    # 8-directional neighbor offsets
    directions = [(-1,0),(1,0),(0,-1),(0,1),(-1,-1),(-1,1),(1,-1),(1,1)]
    def heuristic(a, b): return ((a[0]-b[0])**2 + (a[1]-b[1])**2)**0.5

    visited = {start_node}
    path = [start_node]
    current = start_node
    max_steps = rows * cols
    while current != end_node and len(path) < max_steps:
        candidates = []
        for dr, dc in directions:
            nb = (current[0]+dr, current[1]+dc)
            if nb not in visited and 0 <= nb[0] < rows and 0 <= nb[1] < cols and grid[nb[0]][nb[1]] == 0:
                candidates.append(nb)
        if not candidates:
            break  # stuck — no valid moves
        # Greedy: pick the neighbor closest to the goal (ignore path cost)
        current = min(candidates, key=lambda n: heuristic(n, end_node))
        visited.add(current)
        path.append(current)

    raw_waypoints = [[min_lat+(r/rows)*(max_lat-min_lat), min_lon+(c/cols)*(max_lon-min_lon), 100] for r,c in path]
    raw_df = pd.DataFrame(raw_waypoints, columns=['lat','lon','alt'])
    smooth_waypoints = b_spline_smooth(raw_waypoints, num_points=len(raw_waypoints)*5, k=3)
    if smooth_waypoints:
        smooth_waypoints[0][0] = START_POINT[0]
        smooth_waypoints[0][1] = START_POINT[1]
        smooth_waypoints[-1][0] = END_POINT[0]
        smooth_waypoints[-1][1] = END_POINT[1]
    df = pd.DataFrame(smooth_waypoints, columns=['lat','lon','alt'])
    total_dist = sum(calculate_distance(df.iloc[i-1]['lat'], df.iloc[i-1]['lon'], df.iloc[i]['lat'], df.iloc[i]['lon']) for i in range(1, len(df)))
    fly_time = total_dist / UAV_SPEED
    delay_b = 0.0 if SYNC_STRATEGY == 'independent' else max(0, 0 - fly_time)  # baseline delay
    df['time_s'] = np.linspace(0, fly_time, len(df))
    df['timestamp'] = START_TIME + pd.to_timedelta(df['time_s'], unit='s')
    return df, raw_df, fly_time

# ==================== 4. 生成 Folium ====================
def create_visualization(car_df, uav_df, raw_uav_df, car_interp, uav_interp, delay,
                         output_filename='2d_deduction.html',
                         car_bfs_df=None, car_bfs_interp=None, uav_greedy_df=None, uav_greedy_interp=None):
    map_center = [(START_POINT[0] + END_POINT[0]) / 2, (START_POINT[1] + END_POINT[1]) / 2]
    m = folium.Map(location=map_center, zoom_start=11, tiles="OpenStreetMap", detect_retina=True, control_scale=True)

    # --- 添加城市边界遮罩 ---
    if args.end_point == 'crash':
        mask_file = 'xiantao.json'
        border_files = ['xiantao.json']
    else:
        mask_file = 'huanggang_wuhan.json'
        border_files = ['huanggang.json', 'wuhan.json']

    base_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', 'vue-project_all', 'public', 'Dashboard')
    mask_path = os.path.join(base_path, mask_file)

    if os.path.exists(mask_path):
        import json
        with open(mask_path, 'r', encoding='utf-8') as f:
            mask_data = json.load(f)
            
        features = mask_data.get('features', [])
        if features:
            geom = features[0].get('geometry', {})
            geom_type = geom.get('type')
            coords = geom.get('coordinates', [])
            
            mask_locations = [
                [[-90.0, -180.0], [90.0, -180.0], [90.0, 180.0], [-90.0, 180.0], [-90.0, -180.0]]
            ]
            
            def swap_coords(ring):
                return [[pt[1], pt[0]] for pt in ring]

            if geom_type == 'Polygon':
                for ring in coords:
                    mask_locations.append(swap_coords(ring))
            elif geom_type == 'MultiPolygon':
                for poly in coords:
                    for ring in poly:
                        mask_locations.append(swap_coords(ring))
            
            folium.Polygon(
                locations=mask_locations,
                color='none',
                fill_color='#070b19',
                fill_opacity=0.75,
            ).add_to(m)

            # 计算城市边界并自动缩放以在视图中完整显示城市
            city_lats = [pt[0] for ring in mask_locations[1:] for pt in ring]
            city_lons = [pt[1] for ring in mask_locations[1:] for pt in ring]
            if city_lats and city_lons:
                m.fit_bounds([[min(city_lats), min(city_lons)], [max(city_lats), max(city_lons)]])

    # 加载高亮边界（文件损坏时跳过，不影响路径规划核心功能）
    for b_file in border_files:
        b_path = os.path.join(base_path, b_file)
        if os.path.exists(b_path):
            try:
                with open(b_path, 'r', encoding='utf-8') as f:
                    b_data = json.load(f)
                folium.GeoJson(
                    b_data,
                    style_function=lambda x: {'color': '#00e5ff', 'weight': 3, 'fillOpacity': 0, 'dashArray': '5, 5'}
                ).add_to(m)
            except (json.JSONDecodeError, Exception):
                print(f"  [警告] 边界文件 {b_file} 损坏，跳过加载")
    # -----------------------

    car_path_group = folium.FeatureGroup(name='车辆路径 (UGV Path)', show=True).add_to(m)
    uav_path_group = folium.FeatureGroup(name='无人机路径 (UAV Path)', show=True).add_to(m)

    if COMPARE and car_bfs_interp is not None:
        car_base_group = folium.FeatureGroup(name='车辆-基线BFS (UGV Baseline)', show=True).add_to(m)
    if COMPARE and uav_greedy_interp is not None:
        uav_base_group = folium.FeatureGroup(name='无人机-基线Greedy (UAV Baseline)', show=True).add_to(m)

    if UAV_SMOKE:
        # === 双层禁飞区渲染（航空图风格）===
        for nfz in NFZ_LIST:
            if 'polygon' in nfz:
                poly = nfz['polygon']
                info = nfz.get('name', '核心禁飞区')
                level = nfz.get('level', 'RESTRICTED')
                ceiling = nfz.get('ceiling', '300m AGL')
                reason = nfz.get('reason', '')
                authority = nfz.get('authority', '')
                effective = nfz.get('effective', '全时段')
                # 计算中心点
                cen_lat = sum(p[0] for p in poly) / len(poly)
                cen_lon = sum(p[1] for p in poly) / len(poly)
                # 边界标记点
                for i, (plat, plon) in enumerate(poly):
                    folium.CircleMarker(
                        location=[plat, plon], radius=3,
                        color='#dc2626', fill=True, fill_opacity=0.9,
                        tooltip=f'{info} 边界桩 #{i+1}'
                    ).add_to(m)
                # 中心名称标签
                folium.Marker(
                    location=[cen_lat, cen_lon],
                    icon=folium.DivIcon(
                        html=f'<div style="font-size:11px;font-weight:700;color:#dc2626;'
                             f'background:rgba(255,255,255,0.85);padding:2px 8px;border-radius:4px;'
                             f'border:1px solid #dc2626;white-space:nowrap;">'
                             f'&#x1F6AB; {info}</div>',
                        icon_size=(200, 24), icon_anchor=(100, 12)
                    )
                ).add_to(m)
                # 详细弹出面板
                popup_html = f'''
                    <div style="font-family:Microsoft YaHei,sans-serif;min-width:220px">
                      <div style="font-size:14px;font-weight:700;color:#dc2626;margin-bottom:8px;
                                  border-bottom:2px solid #dc2626;padding-bottom:4px">
                        &#x1F6AB; {info}</div>
                      <table style="font-size:11px;color:#334155;width:100%;border-collapse:collapse">
                        <tr><td style="padding:3px 0;color:#64748b" colspan="2">管制信息</td></tr>
                        <tr><td style="padding:2px 0">管制等级</td>
                            <td style="color:#dc2626;font-weight:700">{level}</td></tr>
                        <tr><td style="padding:2px 0">限飞高度</td>
                            <td style="font-weight:600">{ceiling}</td></tr>
                        <tr><td style="padding:2px 0">管制原因</td><td>{reason}</td></tr>
                        <tr><td style="padding:3px 0;color:#64748b" colspan="2">管理信息</td></tr>
                        <tr><td style="padding:2px 0">发布单位</td><td>{authority}</td></tr>
                        <tr><td style="padding:2px 0">生效时段</td><td>{effective}</td></tr>
                        <tr><td style="padding:3px 0;color:#64748b" colspan="2">区域信息</td></tr>
                        <tr><td style="padding:2px 0">区域面积</td>
                            <td>约 {sum(abs((poly[(i+1)%len(poly)][1]-p[1])*(poly[(i+1)%len(poly)][0]+p[0])) for i,p in enumerate(poly))/2*111000*96000/1e6:.1f} km²</td></tr>
                        <tr><td style="padding:2px 0">顶点数</td><td>{len(poly)} 个控制点</td></tr>
                      </table></div>'''
                folium.Polygon(
                    locations=poly,
                    color='#dc2626', weight=3, dash_array='8, 4',
                    fill=True, fill_opacity=0.3,
                    popup=folium.Popup(popup_html, max_width=300),
                    tooltip=f'&#x1F6AB; {info} | {level} | {ceiling}'
                ).add_to(m)

        for buf in NEW_NFZ_LIST:
            if 'polygon' in buf:
                poly_b = buf['polygon']
                folium.Polygon(
                    locations=poly_b,
                    color='#d97706', weight=2, dash_array='2, 6',
                    fill=True, fill_opacity=0.12,
                    tooltip='&#x26A0; 限飞缓冲区 | 需提前报备飞行计划 | 审批时限: 24h'
                ).add_to(m)

    if UGV_BLOCKED:
        # === 拥堵区渲染（交通态势风格）===
        cong_name = NFZ_CONFIG[args.end_point].get('congestion_name', '拥堵地段')
        cong_info = NFZ_CONFIG[args.end_point].get('congestion_info', '')
        cen_lat = sum(p[0] for p in CONGESTION_ZONE_POLYGON) / len(CONGESTION_ZONE_POLYGON)
        cen_lon = sum(p[1] for p in CONGESTION_ZONE_POLYGON) / len(CONGESTION_ZONE_POLYGON)
        # 拥堵区中心标签
        folium.Marker(
            location=[cen_lat, cen_lon],
            icon=folium.DivIcon(
                html=f'<div style="font-size:10px;font-weight:600;color:#2563eb;'
                     f'background:rgba(255,255,255,0.8);padding:1px 6px;border-radius:3px;'
                     f'border:1px dashed #2563eb;white-space:nowrap;">'
                     f'&#x1F6D1; {cong_name}</div>',
                icon_size=(180, 20), icon_anchor=(90, 10)
            )
        ).add_to(m)
        # 内部填充 + 外边框
        cong_popup = f'''
            <div style="font-family:Microsoft YaHei,sans-serif;min-width:200px">
              <div style="font-size:14px;font-weight:700;color:#2563eb;margin-bottom:6px;
                          border-bottom:2px solid #2563eb;padding-bottom:4px">
                &#x1F6D1; {cong_name}</div>
              <div style="font-size:11px;color:#475569;margin-bottom:6px">{cong_info}</div>
              <div style="font-size:10px;color:#94a3b8">建议: 规划路径自动绕行该区域</div>
            </div>'''
        folium.Polygon(
            locations=CONGESTION_ZONE_POLYGON,
            color='#2563eb', weight=3, dash_array='10, 5',
            fill=True, fill_opacity=0.2,
            popup=folium.Popup(cong_popup, max_width=260),
            tooltip=f'&#x1F6D1; {cong_name} | {cong_info}'
        ).add_to(m)

    folium.Marker(START_POINT, icon=folium.Icon(color='green', icon='home'), tooltip=f'起点：{START_POINT_NAME}').add_to(m)
    folium.Marker(END_POINT, icon=folium.Icon(color='red', icon='fire'), tooltip=f'终点：{END_POINT_NAME}').add_to(m)

    # 当前算法 — 车：蓝色实线 / 飞机：紫色虚线
    folium.PolyLine(car_interp[['lat', 'lon']].values.tolist(), color='#0000ff', weight=5, opacity=0.7).add_to(car_path_group)
    folium.PolyLine(uav_interp[['lat', 'lon']].values.tolist(), color='#ff00ff', weight=3, opacity=0.7, dash_array='5, 5').add_to(uav_path_group)

    # 基线算法 — 车：绿色虚线(BFS) / 飞机：橙色虚线(Greedy)
    if COMPARE and car_bfs_interp is not None:
        folium.PolyLine(car_bfs_interp[['lat', 'lon']].values.tolist(), color='#22c55e', weight=5, opacity=0.6, dash_array='8, 6').add_to(car_base_group)
    if COMPARE and uav_greedy_interp is not None:
        folium.PolyLine(uav_greedy_interp[['lat', 'lon']].values.tolist(), color='#f97316', weight=3, opacity=0.6, dash_array='8, 6').add_to(uav_base_group)

    car_feature = {'type': 'Feature', 'geometry': {'type': 'LineString', 'coordinates': list(map(list, car_interp[['lon', 'lat']].values))}, 'properties': {'times': list(car_interp['timestamp'].dt.strftime('%Y-%m-%dT%H:%M:%S')), 'style': {'color': '#0000ff', 'weight': 5}, 'icon': 'circle', 'iconstyle': {'fillColor': '#0000ff', 'radius': 6}}}
    uav_feature = {'type': 'Feature', 'geometry': {'type': 'LineString', 'coordinates': list(map(list, uav_interp[['lon', 'lat']].values))}, 'properties': {'times': list(uav_interp['timestamp'].dt.strftime('%Y-%m-%dT%H:%M:%S')), 'style': {'color': '#ff00ff', 'weight': 3}, 'icon': 'circle', 'iconstyle': {'fillColor': '#ff00ff', 'radius': 6}}}
    
    duration = int((max(car_interp['timestamp'].max(), uav_interp['timestamp'].max()) - START_TIME).total_seconds())
    
    folium.plugins.TimestampedGeoJson(
        {'type': 'FeatureCollection', 'features': [car_feature, uav_feature]}, 
        period='PT1S', 
        add_last_point=True, 
        duration=f"PT{duration}S", 
        transition_time=1000, 
        loop=False, 
        auto_play=True
    ).add_to(m)

    # 效能评估报告面板 (左上角)
    time_diff = abs(car_df['time_s'].iloc[-1] - uav_df['time_s'].iloc[-1])
    if SYNC_STRATEGY == 'independent': strategy_name = "极速独立模式 (ISD)"
    elif SYNC_STRATEGY == 'wait': strategy_name = "基地待命模式 (CAS)"
    else: strategy_name = "RCD 逆向推演 (本文)"

    car_dist = car_df['dist'].sum() / 1000 if 'dist' in car_df.columns else 0
    uav_dist = sum(calculate_distance(uav_df.iloc[i-1]['lat'], uav_df.iloc[i-1]['lon'], uav_df.iloc[i]['lat'], uav_df.iloc[i]['lon']) for i in range(1, len(uav_df))) / 1000

    compare_rows = ''
    if COMPARE:
        bfs_dist = car_bfs_df['dist'].sum() / 1000 if car_bfs_df is not None and 'dist' in car_bfs_df.columns else 0
        greedy_dist = sum(calculate_distance(uav_greedy_df.iloc[i-1]['lat'], uav_greedy_df.iloc[i-1]['lon'], uav_greedy_df.iloc[i]['lat'], uav_greedy_df.iloc[i]['lon']) for i in range(1, len(uav_greedy_df))) / 1000 if uav_greedy_df is not None and len(uav_greedy_df) > 1 else 0
        car_saving_pct = ((bfs_dist - car_dist) / bfs_dist * 100) if bfs_dist > 0 else 0
        uav_saving_pct = ((greedy_dist - uav_dist) / greedy_dist * 100) if greedy_dist > 0 else 0
        car_saving_km = bfs_dist - car_dist
        uav_saving_km = greedy_dist - uav_dist
        compare_rows = f'''
            <hr style="margin: 10px 0; border: 0; border-top: 1px solid rgba(0, 229, 255, 0.2);">
            <div style="background: rgba(0, 229, 255, 0.05); border: 1px solid rgba(0, 229, 255, 0.2); border-radius: 6px; padding: 10px 12px; margin-bottom: 6px;">
                <div style="font-size: 12px; font-weight: 700; color: #00e5ff; text-align: center; margin-bottom: 10px;">
                    ★ 算法优越性分析 ★
                </div>

                <!-- UGV 对比 -->
                <div style="margin-bottom: 8px;">
                    <div style="font-size: 11px; font-weight: 600; color: #94a3b8; margin-bottom: 5px;">
                        <span style="display:inline-block;width:12px;height:12px;background:#f97316;border-radius:3px;margin-right:6px;vertical-align:middle;"></span>
                        <span style="color:#fdba74;">基准算法</span>
                        <span style="float:right;color:#fdba74;">BFS: {bfs_dist:.1f} km</span>
                    </div>
                    <div style="font-size: 11px; font-weight: 600; color: #94a3b8;">
                        <span style="display:inline-block;width:12px;height:12px;background:#2563eb;border-radius:3px;margin-right:6px;vertical-align:middle;"></span>
                        <span style="color:#93c5fd;">本文算法</span>
                        <span style="float:right;color:#93c5fd;">Dijkstra: {car_dist:.1f} km</span>
                    </div>
                    <div style="background: rgba(34, 197, 94, 0.15); border: 1px solid rgba(34, 197, 94, 0.3); border-radius: 4px; padding: 3px 8px; margin-top: 4px; text-align: center;">
                        <span style="font-size: 11px; font-weight: 700; color: #4ade80;">
                            ▼ 车辆路径优化 <b>{car_saving_km:.1f} km</b>（缩短 <b>{car_saving_pct:.1f}%</b>）
                        </span>
                    </div>
                </div>

                <!-- UAV 对比 -->
                <div>
                    <div style="font-size: 11px; font-weight: 600; color: #94a3b8; margin-bottom: 5px;">
                        <span style="display:inline-block;width:12px;height:12px;background:#f97316;border-radius:3px;margin-right:6px;vertical-align:middle;"></span>
                        <span style="color:#fdba74;">基准算法</span>
                        <span style="float:right;color:#fdba74;">Greedy: {greedy_dist:.1f} km</span>
                    </div>
                    <div style="font-size: 11px; font-weight: 600; color: #94a3b8;">
                        <span style="display:inline-block;width:12px;height:12px;background:#2563eb;border-radius:3px;margin-right:6px;vertical-align:middle;"></span>
                        <span style="color:#93c5fd;">本文算法</span>
                        <span style="float:right;color:#93c5fd;">A*: {uav_dist:.1f} km</span>
                    </div>
                    <div style="background: rgba(34, 197, 94, 0.15); border: 1px solid rgba(34, 197, 94, 0.3); border-radius: 4px; padding: 3px 8px; margin-top: 4px; text-align: center;">
                        <span style="font-size: 11px; font-weight: 700; color: #4ade80;">
                            ▼ 无人机路径优化 <b>{uav_saving_km:.1f} km</b>（缩短 <b>{uav_saving_pct:.1f}%</b>）
                        </span>
                    </div>
                </div>

                <!-- 总结 -->
                <div style="background: rgba(34, 197, 94, 0.3); border: 1px solid rgba(34, 197, 94, 0.5); border-radius: 4px; padding: 5px 10px; margin-top: 8px; text-align: center;">
                    <span style="font-size: 11px; font-weight: 700; color: #dcfce7;">
                        综合路径总节省 <b>{(car_saving_km + uav_saving_km):.1f} km</b>（平均优化 <b>{((car_saving_pct + uav_saving_pct) / 2):.1f}%</b>）
                    </span>
                </div>
            </div>
        '''

    ui_html = f'''
    <div style="position: fixed; top: 110px; left: 40px; z-index: 1000; width: 300px; 
                background: rgba(6, 22, 40, 0.85); padding: 15px; border-radius: 8px; 
                border: 1px solid rgba(0, 229, 255, 0.4); backdrop-filter: blur(8px); 
                box-shadow: 0 4px 20px rgba(0,0,0,0.4); font-family: 'Microsoft YaHei', sans-serif; color: #fff;">
        <h4 style="margin: 0 0 12px; color: #00e5ff; text-align: center; border-bottom: 1px solid rgba(0, 229, 255, 0.2); padding-bottom: 8px;">ISD/CAS/RCD 效能对比</h4>
        <div style="font-size: 13px; line-height: 1.6;">
            <div style="display: flex; justify-content: space-between;"><span>协同机制:</span> <b style="color: #00e5ff;">{strategy_name}</b></div>
            <div style="display: flex; justify-content: space-between; margin-top: 4px;"><span>车辆(UGV)耗时:</span> <b style="color: #e6faff;">{car_df['time_s'].iloc[-1]/60:.1f} min</b></div>
            <div style="display: flex; justify-content: space-between; margin-top: 4px;"><span>无人机(UAV)飞行:</span> <b style="color: #e6faff;">{(uav_df['time_s'].iloc[-1]-delay)/60:.1f} min</b></div>
            <div style="display: flex; justify-content: space-between; background: rgba(245, 158, 11, 0.1); border: 1px solid rgba(245, 158, 11, 0.2); border-radius: 4px; padding: 2px 6px; margin-top: 4px;">
                <span>无人机地面待机:</span> <b style="color:#fbbf24;">{delay:.1f} s</b>
            </div>
            <hr style="margin: 10px 0; border: 0; border-top: 1px solid rgba(0, 229, 255, 0.2);">
            <div style="display: flex; justify-content: space-between; color: #fb7185;"><span>协同终端时间差:</span> <b>{time_diff:.1f} s</b></div>
            {compare_rows}
        </div>
    </div>
    '''
    
    m.get_root().html.add_child(folium.Element(ui_html))

    # 终点切换 + 障碍物开关 + 协同策略 + 对比模式 控制面板
    leak_selected = 'selected' if args.end_point == 'leak' else ''
    crash_selected = 'selected' if args.end_point == 'crash' else ''
    block_on  = 'selected' if UGV_BLOCKED else ''
    block_off = 'selected' if not UGV_BLOCKED else ''
    strat_rcd = 'selected' if SYNC_STRATEGY == 'rcd' else ''
    strat_ind = 'selected' if SYNC_STRATEGY == 'independent' else ''
    strat_wait = 'selected' if SYNC_STRATEGY == 'wait' else ''
    cmp_on  = 'selected' if COMPARE else ''
    cmp_off = 'selected' if not COMPARE else ''
    selector_html = f'''
    <div style="position: fixed; top: 20px; left: 50%; transform: translateX(-50%); z-index: 9999;
                background: rgba(15, 23, 42, 0.95); padding: 12px 24px; border-radius: 10px;
                border: 1px solid rgba(0, 229, 255, 0.35); box-shadow: 0 4px 20px rgba(0,0,0,0.4);
                display: flex; align-items: center; gap: 14px; font-family: 'Microsoft YaHei', sans-serif; flex-wrap: wrap;">
        <span style="color: #94a3b8; font-size: 13px; font-weight: 500; white-space: nowrap;">终点：</span>
        <select id="endpoint-selector" style="padding: 6px 32px 6px 12px; border: 1px solid rgba(0, 229, 255, 0.3);
                border-radius: 6px; background: rgba(2, 10, 22, 0.85); color: #e6faff; font-size: 13px;
                cursor: pointer; outline: none;">
            <option value="leak" {leak_selected}>油罐车泄露现场</option>
            <option value="crash" {crash_selected}>货车追尾现场</option>
        </select>
        <span style="color: #94a3b8; font-size: 13px; font-weight: 500; white-space: nowrap;">障碍物：</span>
        <select id="obstacle-selector" style="padding: 6px 32px 6px 12px; border: 1px solid rgba(0, 229, 255, 0.3);
                border-radius: 6px; background: rgba(2, 10, 22, 0.85); color: #e6faff; font-size: 13px;
                cursor: pointer; outline: none;">
            <option value="1" {block_on}>开启（含禁飞区/拥堵区）</option>
            <option value="0" {block_off}>关闭（无障碍直连路径）</option>
        </select>
        <span style="color: #94a3b8; font-size: 13px; font-weight: 500; white-space: nowrap;">策略：</span>
        <select id="strategy-selector" style="padding: 6px 32px 6px 12px; border: 1px solid rgba(0, 229, 255, 0.3);
                border-radius: 6px; background: rgba(2, 10, 22, 0.85); color: #e6faff; font-size: 13px;
                cursor: pointer; outline: none;">
            <option value="rcd" {strat_rcd}>RCD 逆向推演</option>
            <option value="independent" {strat_ind}>ISD 极速独立</option>
            <option value="wait" {strat_wait}>CAS 基地待命</option>
        </select>
        <span style="color: #f97316; font-size: 13px; font-weight: 500; white-space: nowrap;">对比：</span>
        <select id="compare-selector" style="padding: 6px 32px 6px 12px; border: 1px solid rgba(249, 115, 22, 0.4);
                border-radius: 6px; background: rgba(2, 10, 22, 0.85); color: #fdba74; font-size: 13px;
                cursor: pointer; outline: none;">
            <option value="0" {cmp_off}>关闭对比</option>
            <option value="1" {cmp_on}>开启对比 (Dijkstra/A* vs BFS/Greedy)</option>
        </select>
        <button id="replan-btn" onclick="replanPath()" style="padding: 6px 18px; border: 1px solid rgba(0, 229, 255, 0.25);
                border-radius: 6px; background: rgba(0, 229, 255, 0.1); color: #00e5ff; font-size: 13px;
                cursor: pointer; white-space: nowrap; transition: all 0.2s;"
                onmouseover="this.style.background='rgba(0,229,255,0.2)'"
                onmouseout="this.style.background='rgba(0,229,255,0.1)'">重新规划路径</button>
        <span id="replan-status" style="color: #f97316; font-size: 12px; display: none;">规划中...</span>
    </div>
    <script>
    var _replanTimer = null;
    async function replanPath() {{
        var ep = document.getElementById('endpoint-selector');
        var ob = document.getElementById('obstacle-selector');
        var st = document.getElementById('strategy-selector');
        var cp = document.getElementById('compare-selector');
        var btn = document.getElementById('replan-btn');
        var status = document.getElementById('replan-status');
        btn.disabled = true;
        status.style.display = 'inline';
        status.style.color = '#f97316';
        var startTime = Date.now();
        if (_replanTimer) clearInterval(_replanTimer);
        _replanTimer = setInterval(function() {{
            var elapsed = Math.floor((Date.now() - startTime) / 1000);
            status.textContent = '规划中... (' + elapsed + 's)';
        }}, 1000);
        var controller = new AbortController();
        var timer = setTimeout(function() {{ controller.abort(); }}, 180000);
        try {{
            var params = '?end_point=' + encodeURIComponent(ep.value)
                       + '&ugv_block=' + encodeURIComponent(ob.value)
                       + '&uav_smoke=' + encodeURIComponent(ob.value)
                       + '&strategy=' + encodeURIComponent(st.value)
                       + '&compare=' + encodeURIComponent(cp.value);
            var resp = await fetch('/api/run_3d_strategy' + params, {{ signal: controller.signal }});
            clearTimeout(timer);
            clearInterval(_replanTimer);
            if (!resp.ok) throw new Error('HTTP ' + resp.status);
            location.reload();
        }} catch(e) {{
            clearTimeout(timer);
            clearInterval(_replanTimer);
            if (e.name === 'AbortError') {{
                status.textContent = '规划超时(>3分钟)，请重试';
            }} else {{
                status.textContent = '规划失败: ' + e.message;
            }}
            status.style.color = '#ef4444';
            btn.disabled = false;
        }}
    }}
    </script>
    '''
    m.get_root().html.add_child(folium.Element(selector_html))

    m.save(output_filename)
    print(f"地图已保存至: {output_filename}")

# ==================== 5. 主函数 ====================
def _load_path_from_json(endpoint, strategy, ugv_block, uav_smoke):
    """从预计算的 JSON 文件快速加载路径数据，跳过路网下载和路径规划。"""
    block_key = f"b{1 if ugv_block else 0}s{1 if uav_smoke else 0}"
    data_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "path_data", f"path_{endpoint}_{block_key}.json")
    if not os.path.exists(data_path):
        return None
    with open(data_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    if data.get('strategy', '') != strategy:
        return None
    if data.get('ugv_block') != ugv_block or data.get('uav_smoke') != uav_smoke:
        return None
    metrics = data.get('metrics', {})
    car_df = pd.DataFrame(data['car_path'])
    uav_df = pd.DataFrame(data['uav_path'])
    car_time = metrics.get('car_time_min', 0) * 60
    delay = metrics.get('delay_sec', 0)
    return car_df, uav_df, car_time, delay

def save_to_czml(uav_df, car_df, delay):
    print("[CZML] Exporting CZML file...")
    uav_df = uav_df.copy()
    car_df = car_df.copy()
    
    if 'timestamp' not in uav_df.columns:
        uav_df['timestamp'] = START_TIME + pd.to_timedelta(uav_df['time_s'], unit='s')
    if 'timestamp' not in car_df.columns:
        car_df['timestamp'] = START_TIME + pd.to_timedelta(car_df['time_s'], unit='s')
    
    def format_timestamp(ts):
        if ts.tzinfo is None:
            return ts.strftime('%Y-%m-%dT%H:%M:%S') + 'Z'
        return ts.isoformat()

    global_start_time = min(uav_df['timestamp'].min(), car_df['timestamp'].min())
    global_end_time = max(uav_df['timestamp'].max(), car_df['timestamp'].max())
    
    start_str = format_timestamp(global_start_time)
    avail = f"{start_str}/{format_timestamp(global_end_time)}"
    
    czml = [{"id": "document", "version": "1.0", "clock": {"interval": avail, "currentTime": start_str, "multiplier": 10, "range": "LOOP_STOP"}}]
    
    # 静态地标
    czml.append({"id": "StartMarker", "position": {"cartographicDegrees": [START_POINT[1], START_POINT[0], 0]}, "point": {"pixelSize": 12, "color": {"rgba": [0,255,0,255]}}, "label": {"text": START_POINT_NAME, "font": "16px Microsoft YaHei", "pixelOffset": {"cartesian2": [0, -20]}}})
    czml.append({"id": "EndMarker", "position": {"cartographicDegrees": [END_POINT[1], END_POINT[0], 0]}, "point": {"pixelSize": 12, "color": {"rgba": [255,0,0,255]}}, "label": {"text": END_POINT_NAME, "font": "16px Microsoft YaHei", "pixelOffset": {"cartesian2": [0, -20]}}})

    # 路径线
    uav_line = []
    for _, r in uav_df.iterrows(): uav_line.extend([r['lon'], r['lat'], r['alt']])
    czml.append({"id": "UAV_Path", "polyline": {"positions": {"cartographicDegrees": uav_line}, "width": 3, "material": {"solidColor": {"color": {"rgba": [255, 0, 0, 150]}}}}})
    
    car_line = []
    for _, r in car_df.iterrows(): car_line.extend([r['lon'], r['lat'], 2])
    czml.append({"id": "Car_Path", "polyline": {"positions": {"cartographicDegrees": car_line}, "width": 3, "material": {"solidColor": {"color": {"rgba": [0, 0, 255, 150]}}}}})

    # 动态对象
    uav_pos = []
    for _, r in uav_df.iterrows(): uav_pos.extend([format_timestamp(r['timestamp']), r['lon'], r['lat'], r['alt']])
    czml.append({
        "id": "UAV", "name": "无人机 (B-Spline)", "availability": avail,
        "position": {"epoch": start_str, "cartographicDegrees": uav_pos, "interpolationAlgorithm": "LINEAR", "interpolationDegree": 1},
        "point": {"pixelSize": 15, "color": {"rgba": [255, 0, 0, 255]}, "outlineColor": {"rgba": [255,255,255,255]}, "outlineWidth": 2},
        "label": {"text": "无人机", "font": "14px Microsoft YaHei", "pixelOffset": {"cartesian2": [0, -25]}}
    })

    car_pos = []
    for _, r in car_df.iterrows(): car_pos.extend([format_timestamp(r['timestamp']), r['lon'], r['lat'], 2])
    czml.append({
        "id": "Car", "name": "无人车", "availability": avail,
        "position": {"epoch": start_str, "cartographicDegrees": car_pos, "interpolationAlgorithm": "LINEAR", "interpolationDegree": 1},
        "point": {"pixelSize": 15, "color": {"rgba": [0, 0, 255, 255]}, "outlineColor": {"rgba": [255,255,255,255]}, "outlineWidth": 2},
        "label": {"text": "无人车", "font": "14px Microsoft YaHei", "pixelOffset": {"cartesian2": [0, -25]}}
    })

    # 障碍物
    for i, nfz in enumerate(NFZ_LIST + NEW_NFZ_LIST):
        color = [255, 0, 0, 100] if i < len(NFZ_LIST) else [255, 165, 0, 100]
        if 'polygon' in nfz:
            poly_coords = []
            for p in nfz['polygon']:
                poly_coords.extend([p[1], p[0], 200])
            czml.append({
                "id": f"NFZ_{i}", "polygon": {
                    "positions": {"cartographicDegrees": poly_coords},
                    "material": {"solidColor": {"color": {"rgba": color}}},
                    "extrudedHeight": 400
                }
            })
        else:
            czml.append({
                "id": f"NFZ_{i}", "position": {"cartographicDegrees": [nfz['center'][1], nfz['center'][0], 200]},
                "cylinder": {"length": 400, "topRadius": nfz['radius'], "bottomRadius": nfz['radius'],
                             "material": {"solidColor": {"color": {"rgba": color}}}}
            })
    poly = []
    for p in CONGESTION_ZONE_POLYGON: poly.extend([p[1], p[0], 0])
    czml.append({"id": "Congestion", "polygon": {"positions": {"cartographicDegrees": poly}, "material": {"solidColor": {"color": {"rgba": [0, 0, 255, 80]}}}}})

    czml_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "mission.czml")
    with open(czml_path, "w", encoding='utf-8') as f: 
        json.dump(czml, f, ensure_ascii=False, indent=2)
    print("[CZML] CZML file generated successfully!")

if __name__ == '__main__':
    # 快速重载：如果路径数据 JSON 已存在且策略匹配，直接加载跳过路网下载和路径规划
    cached = _load_path_from_json(args.end_point, SYNC_STRATEGY, UGV_BLOCKED, UAV_SMOKE)
    if cached and not COMPARE:
        car_df, uav_df, car_time, delay = cached
        raw_uav_df = uav_df  # 快速模式复用平滑路径
        print(f"[快速模式] 从缓存 JSON 加载路径 (终点={args.end_point})，跳过路网下载与路径规划")
        car_bfs_df, car_bfs_interp = None, None
        uav_greedy_df, uav_greedy_interp = None, None
    else:
        print("正在请求路网数据并规划无人车路径...")
        car_df, car_time, car_G = generate_car_path()
        print(f"无人车路径规划完成，预估耗时: {car_time/60:.1f} 分钟。")

        print("正在进行无人机三维避障规划与B样条平滑...")
        uav_df, raw_uav_df, delay = generate_uav_path(car_time)
        print(f"无人机规划完成。策略: {SYNC_STRATEGY}, 地面待机时间: {delay:.1f} 秒。")

        # 基线对比算法
        car_bfs_df, car_bfs_interp = None, None
        uav_greedy_df, uav_greedy_interp = None, None
        if COMPARE:
            print("--- 对比模式：正在运行基线算法 ---")
            print("  [基线] BFS 车辆路径 (最少边数, 忽略道路长度)...")
            car_bfs_df, _ = generate_car_path_bfs(G=car_G.copy() if car_G is not None else None)
            bfs_dist = car_bfs_df['dist'].sum() / 1000 if 'dist' in car_bfs_df.columns else 0
            print(f"  [基线] BFS 完成, 路径距离: {bfs_dist:.1f} km")
            print("  [基线] Greedy 无人机路径 (仅朝目标移动, 忽略全局代价)...")
            uav_greedy_df, _, _ = generate_uav_path_greedy()
            greedy_dist = sum(calculate_distance(uav_greedy_df.iloc[i-1]['lat'], uav_greedy_df.iloc[i-1]['lon'], uav_greedy_df.iloc[i]['lat'], uav_greedy_df.iloc[i]['lon']) for i in range(1, len(uav_greedy_df))) / 1000 if len(uav_greedy_df) > 1 else 0
            print(f"  [基线] Greedy 完成, 路径距离: {greedy_dist:.1f} km")
            car_bfs_interp = interpolate_path(car_bfs_df, ANIMATION_INTERVAL)
            uav_greedy_interp = interpolate_path(uav_greedy_df, ANIMATION_INTERVAL)
            car_dist = car_df['dist'].sum() / 1000 if 'dist' in car_df.columns else 0
            uav_dist = sum(calculate_distance(uav_df.iloc[i-1]['lat'], uav_df.iloc[i-1]['lon'], uav_df.iloc[i]['lat'], uav_df.iloc[i]['lon']) for i in range(1, len(uav_df))) / 1000
            print(f"  算法优越性: Dijkstra={car_dist:.1f} vs BFS={bfs_dist:.1f} km (节省{(bfs_dist-car_dist)/bfs_dist*100:.1f}%)")
            print(f"  算法优越性: A*={uav_dist:.1f} vs Greedy={greedy_dist:.1f} km (节省{(greedy_dist-uav_dist)/greedy_dist*100:.1f}%)")

    print("正在进行时空同步插值与交互式网页生成...")
    car_interp = interpolate_path(car_df, ANIMATION_INTERVAL)
    uav_interp = interpolate_path(uav_df, ANIMATION_INTERVAL)
    output_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "2d_deduction.html")
    create_visualization(car_df, uav_df, raw_uav_df, car_interp, uav_interp, delay, output_filename=output_path,
                         car_bfs_df=car_bfs_df, car_bfs_interp=car_bfs_interp,
                         uav_greedy_df=uav_greedy_df, uav_greedy_interp=uav_greedy_interp)

    # 导出路径数据为 JSON 文件（快速模式跳过，数据未变）
    if not cached:
        car_records = car_df[['lat', 'lon', 'time_s']].to_dict(orient='records')
        uav_records = uav_df[['lat', 'lon', 'alt', 'time_s']].to_dict(orient='records')
        car_time_min = round(car_time / 60, 1)
        uav_flight_min = round((uav_df['time_s'].iloc[-1] - delay) / 60, 1) if len(uav_df) > 0 else 0
        car_dist = round(car_df['dist'].sum() / 1000, 2) if 'dist' in car_df.columns else 0
        path_data = {
            'end_point': args.end_point,
            'end_point_name': END_POINT_NAME,
            'strategy': SYNC_STRATEGY,
            'ugv_block': UGV_BLOCKED,
            'uav_smoke': UAV_SMOKE,
            'start_point': {'lat': START_POINT[0], 'lon': START_POINT[1], 'name': START_POINT_NAME},
            'end_point_coord': {'lat': END_POINT[0], 'lon': END_POINT[1]},
            'car_path': car_records,
            'uav_path': uav_records,
            'metrics': {
                'car_time_min': car_time_min,
                'uav_flight_time_min': uav_flight_min,
                'delay_sec': round(delay, 1),
                'car_dist_km': car_dist,
            }
        }
        block_key = f"b{1 if UGV_BLOCKED else 0}s{1 if UAV_SMOKE else 0}"
        data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "path_data")
        os.makedirs(data_dir, exist_ok=True)
        data_path = os.path.join(data_dir, f"path_{args.end_point}_{block_key}.json")
        with open(data_path, 'w', encoding='utf-8') as f:
            json.dump(path_data, f, ensure_ascii=False, indent=2)
        print(f"路径数据已导出至: {data_path}")

    # 同时更新 path_result.json 供 API metrics 接口使用
    result_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "path_result.json")
    car_time_min = round(car_time / 60, 1)
    uav_flight_min = round((uav_df['time_s'].iloc[-1] - delay) / 60, 1) if len(uav_df) > 0 else 0
    result_data = {
        'end_point': args.end_point,
        'end_point_name': END_POINT_NAME,
        'strategy': SYNC_STRATEGY,
        'metrics': {
            'carTime': str(car_time_min),
            'uavTime': str(uav_flight_min),
            'delay': str(round(delay, 1)),
            'uavEnergy': str(round(uav_flight_min * UAV_SPEED * 3.6, 1)),
        },
        'obstacles': (
            [{'type': 'polygon', 'color': '#3b82f6',
              'positions': [p for point in CONGESTION_ZONE_POLYGON for p in [point[1], point[0]]]}]
            + ([{'type': 'polygon', 'color': '#ef4444',
                 'positions': [p for point in NFZ_LIST[0]['polygon'] for p in [point[1], point[0]]]}]
               if NFZ_LIST and 'polygon' in NFZ_LIST[0] else
               [{'type': 'cylinder', 'center': [NFZ_LIST[0]['center'][1], NFZ_LIST[0]['center'][0]],
                 'radius': NFZ_LIST[0]['radius'], 'color': '#ef4444', 'height': 200}]
               if NFZ_LIST else [])
        ) if UGV_BLOCKED or UAV_SMOKE else [],
        'updated_at': datetime.now(timezone.utc).isoformat() if 'timezone' in dir() else datetime.now().isoformat(),
    }
    with open(result_path, 'w', encoding='utf-8') as f:
        json.dump(result_data, f, ensure_ascii=False, indent=2)
    
    # 导出并覆盖 mission.czml 供三维地图同步载入
    save_to_czml(uav_df, car_df, delay)
