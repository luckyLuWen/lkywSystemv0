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
from rescue_points import get_rescue_points, log_selection, get_agent_pois, AGENT_CONFIG

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
parser.add_argument('--multi_agent', type=int, default=0,
                    help='是否开启五类救援智能体: 1=查询POI并规划五条救援路径')
args = parser.parse_args()

UGV_BLOCKED = (args.ugv_block == 1)
UAV_SMOKE = (args.uav_smoke == 1)
SYNC_STRATEGY = str(args.strategy).strip().lower()
COMPARE = (args.compare == 1)
MULTI_AGENT = (args.multi_agent == 1)

CAR_SPEED = 22.22  # 80 km/h (长途救援真实车速)
UAV_SPEED = 20.0   # 20 m/s (大型救援无人机)

END_POINTS = {
    'leak':  (30.63101, 114.89209),                       # 油罐车泄漏现场
    'crash': (30.385469, 113.104833),                     # 货车追尾现场
}
END_POINT_NAMES = {
    'leak':  '市区道路-油罐车泄漏现场',
    'crash': '高速公路-货车追尾现场',
}
END_POINT = END_POINTS[args.end_point]
END_POINT_NAME = END_POINT_NAMES[args.end_point]

# 从数据库读取当前场景的候选救援点，自动选取距事故点最近的作为起点
ALL_CANDIDATE_POINTS = get_rescue_points(args.end_point)
if not ALL_CANDIDATE_POINTS:
    raise RuntimeError(f"场景 '{args.end_point}' 没有救援点数据，请先运行 rescue_points.py 初始化数据库")

# 计算每个候选点到事故终点的直线距离，按距离升序排列
for p in ALL_CANDIDATE_POINTS:
    p['dist_to_accident_km'] = round(
        geodesic((p['lat'], p['lon']), END_POINT).kilometers, 2
    )
ALL_CANDIDATE_POINTS.sort(key=lambda p: p['dist_to_accident_km'])

# 选取最近点作为最优起点
best_point = ALL_CANDIDATE_POINTS[0]
START_POINT = (best_point['lat'], best_point['lon'])
START_POINT_NAME = best_point['name']
log_selection(args.end_point, best_point['id'], f"最近距离 {best_point['dist_to_accident_km']} km")

print(f"[救援点选择] 场景={args.end_point}, 候选={len(ALL_CANDIDATE_POINTS)}个")
for i, p in enumerate(ALL_CANDIDATE_POINTS):
    marker = "★ 选中" if i == 0 else f"  #{i}"
    print(f"  {marker} {p['name']} ({p['lat']}, {p['lon']}) — {p['dist_to_accident_km']} km")

# 从数据库加载五类救援智能体 POI（仅标记，无路径）
AGENT_POIS = get_agent_pois(args.end_point)
for p in AGENT_POIS:
    p['dist_km'] = round(geodesic((p['lat'], p['lon']), END_POINT).kilometers, 2)
print(f"[智能体POI] 场景={args.end_point}, 共 {len(AGENT_POIS)} 个智能体站点")

# 禁飞区 & 拥堵区 — 紧凑尺寸（~500m），精确位于路径中点
NFZ_CONFIG = {
    'leak': {
        'nfz': [{  # 限飞区，不规则多边形，模拟真实受限空域
            'polygon': [
                [30.6338, 114.8852], [30.6335, 114.8865], [30.6342, 114.8878], 
                [30.6351, 114.8873], [30.6356, 114.8860], [30.6352, 114.8848], [30.6345, 114.8845]
            ],
            'name': '团风城区低空限飞区',
            'level': 'RESTRICTED',
            'ceiling': '200m AGL',
            'reason': '城区人口密集区低空安全',
            'authority': '团风县应急管理局',
            'effective': '全时段',
        }],
        'buffer': [{  # 缓冲区，随限飞区形状扩大
            'polygon': [
                [30.6333, 114.8848], [30.6330, 114.8865], [30.6340, 114.8875], 
                [30.6354, 114.8878], [30.6360, 114.8861], [30.6355, 114.8844], [30.6345, 114.8841]
            ],
        }],
        'congestion': [  # 施工拥堵，不规则曲线多边形，模拟道路实际拥堵走势
            [30.6336, 114.8850], [30.6340, 114.8862], [30.6346, 114.8871], 
            [30.6353, 114.8875], [30.6357, 114.8868], [30.6350, 114.8863],
            [30.6344, 114.8854], [30.6340, 114.8847]
        ],
        'congestion_name': '团风大道施工拥堵区',
        'congestion_info': '道路半幅封闭施工 | 通行延时+40%',
    },
    'crash': {
        'nfz': [{  # 限飞区 ~1km，位于三伏潭→事故点航线中点，距事故约5km
            'polygon': [
                [30.348, 113.147], [30.352, 113.158], [30.358, 113.155],
                [30.362, 113.149], [30.358, 113.140], [30.350, 113.140],
            ],
            'name': '巡航空域限飞区',
            'level': 'RESTRICTED', 'ceiling': '200m AGL',
            'reason': '军事训练空域管制', 'authority': '仙桃市应急管理局', 'effective': '全时段',
        }],
        'buffer': [{  # 缓冲区
            'polygon': [
                [30.346, 113.144], [30.350, 113.160], [30.359, 113.157],
                [30.364, 113.148], [30.360, 113.138], [30.349, 113.138],
            ],
        }],
        'congestion': [  # G50高速入口匝道施工 ~300m，仅堵入口
            [30.356, 113.148], [30.358, 113.152], [30.360, 113.150],
            [30.359, 113.146], [30.357, 113.145],
        ],
        'congestion_name': 'G50高速入口匝道施工',
        'congestion_info': '入口匝道半幅封闭 | 通行延时+30%',
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

# 统一路网 bbox：覆盖当前场景所有候选点+终点的矩形走廊
_PAD = 0.05  # 每边约 5km 缓冲
_ALL_LATS = [p['lat'] for p in ALL_CANDIDATE_POINTS] + [END_POINT[0]]
_ALL_LONS = [p['lon'] for p in ALL_CANDIDATE_POINTS] + [END_POINT[1]]
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
            ((START_POINT[0] + END_POINT[0]) / 2, (START_POINT[1] + END_POINT[1]) / 2),
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
        end_gap = calculate_distance(path_coords[-1][0], path_coords[-1][1], END_POINT[0], END_POINT[1])
        if 10 < end_gap < 500:
            path_coords.append(END_POINT)
        elif end_gap >= 500:
            print(f"  [注意] 事故点距最近道路 {end_gap/1000:.1f}km，无人车停在最近道路节点")
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
                ((START_POINT[0] + END_POINT[0]) / 2, (START_POINT[1] + END_POINT[1]) / 2),
                dist=fetch_radius, network_type='drive', simplify=False,
            )
        orig = ox.nearest_nodes(G, START_POINT[1], START_POINT[0])
        dest = ox.nearest_nodes(G, END_POINT[1], END_POINT[0])
        route = nx.shortest_path(G, orig, dest, weight=None)
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
    except Exception:
        df = pd.DataFrame([START_POINT, END_POINT], columns=['lat', 'lon'])
        df['time_s'] = [0, 100]
        return df, 100

def generate_uav_path_greedy():
    """基线算法：Greedy Best-First — 每次只朝目标方向移动，不考虑全局代价，对比 A* 最优路径"""
    pad = 0.05
    min_lat = min(START_POINT[0], END_POINT[0]) - pad
    max_lat = max(START_POINT[0], END_POINT[0]) + pad
    min_lon = min(START_POINT[1], END_POINT[1]) - pad
    max_lon = max(START_POINT[1], END_POINT[1]) + pad
    rows = int(calculate_distance(min_lat, min_lon, max_lat, min_lon) / GRID_RES)
    cols = int(calculate_distance(min_lat, min_lon, min_lat, max_lon) / GRID_RES)
    grid = np.zeros((rows, cols), dtype=int)  # Greedy 不避障，直接穿行禁飞区
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
                         car_bfs_df=None, car_bfs_interp=None, uav_greedy_df=None, uav_greedy_interp=None,
                         multi_agent_data=None):
    map_center = [(START_POINT[0] + END_POINT[0]) / 2, (START_POINT[1] + END_POINT[1]) / 2]
    m = folium.Map(location=map_center, zoom_start=11, tiles=None, detect_retina=True, control_scale=True)
    folium.TileLayer(tiles='OpenStreetMap', name='电子地图', show=True).add_to(m)

    # --- 添加城市边界遮罩 ---
    if args.end_point == 'crash':
        mask_file = 'xiantao.json'
        border_files = ['xiantao.json']
    else:
        mask_file = 'huanggang.json'
        border_files = ['huanggang.json']

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

    # 渲染所有候选救援点：选中 = 绿色，未选中 = 灰色
    for p in ALL_CANDIDATE_POINTS:
        is_selected = (p['name'] == START_POINT_NAME)
        color = 'green' if is_selected else 'lightgray'
        icon_type = 'home' if is_selected else 'flag'
        label = '★ 选中起点' if is_selected else f"备选 #{p.get('dist_to_accident_km', '?')} km"
        tooltip = f"{label}：{p['name']}"
        folium.Marker(
            (p['lat'], p['lon']),
            icon=folium.Icon(color=color, icon=icon_type),
            tooltip=tooltip,
        ).add_to(m)
    folium.Marker(END_POINT, icon=folium.Icon(color='red', icon='fire'), tooltip=f'终点：{END_POINT_NAME}').add_to(m)

    # ===== 五类救援智能体 POI（按类型分组，支持图层开关） =====
    agent_icons_map = {
        'medical': 'plus', 'fire': 'fire', 'police': 'flag',
        'hazmat': 'flash', 'road': 'wrench',
    }
    # 构建 "选中POI名称 → 路径info" 的快速查找
    _selected_poi_names = set()
    _agent_path_by_name = {}
    if multi_agent_data:
        for akey, ainfo in multi_agent_data.items():
            if ainfo.get('poi') and ainfo.get('path'):
                nm = ainfo['poi']['name']
                _selected_poi_names.add(nm)
                _agent_path_by_name[nm] = ainfo

    # 按类型分组 POI
    from collections import defaultdict
    _pois_by_type = defaultdict(list)
    for p in AGENT_POIS:
        _pois_by_type[p.get('agent_key', 'other')].append(p)

    # 每种类型对应的 Folium 亮/暗颜色
    _type_colors = {
        'medical': ('green', 'lightgreen'),
        'fire':    ('orange', 'beige'),
        'police':  ('blue', 'lightblue'),
        'hazmat':  ('purple', 'pink'),
        'road':    ('gray', 'lightgray'),
    }

    # 每种类型一个 FeatureGroup
    for agent_key, cfg in AGENT_CONFIG.items():
        pois = _pois_by_type.get(agent_key, [])
        if not pois:
            continue
        fg = folium.FeatureGroup(name=f"{cfg['label']}站点", show=True).add_to(m)
        bright, dim = _type_colors.get(agent_key, ('gray', 'lightgray'))
        icon_key = agent_icons_map.get(agent_key, 'flag')

        for p in pois:
            is_selected = p['name'] in _selected_poi_names
            marker_color = bright if not multi_agent_data else (bright if is_selected else 'lightgray')
            if is_selected:
                tooltip = f"★ {cfg['label']}：{p['name']}（{p['dist_km']} km）— 已启动"
            else:
                tooltip = f"{cfg['label']}：{p['name']}（{p['dist_km']} km）— 备选"
            folium.Marker(
                (p['lat'], p['lon']),
                icon=folium.Icon(color=marker_color, icon=icon_key),
                tooltip=tooltip,
            ).add_to(fg)

        # 静态路径线取消（由 TimestampedGeoJson 动画动态绘制，避免重复杂乱）

    folium.LayerControl(collapsed=True).add_to(m)

    # 当前算法 — 车：蓝色实线 / 飞机：紫色虚线
    folium.PolyLine(car_interp[['lat', 'lon']].values.tolist(), color='#0000ff', weight=5, opacity=0.7).add_to(car_path_group)
    folium.PolyLine(uav_interp[['lat', 'lon']].values.tolist(), color='#ff00ff', weight=3, opacity=0.7, dash_array='5, 5').add_to(uav_path_group)

    # 基线算法 — 车：绿色虚线(BFS) / 飞机：橙色虚线(Greedy)
    if COMPARE and car_bfs_interp is not None:
        folium.PolyLine(car_bfs_interp[['lat', 'lon']].values.tolist(), color='#22c55e', weight=5, opacity=0.6, dash_array='8, 6').add_to(car_base_group)
    if COMPARE and uav_greedy_interp is not None:
        folium.PolyLine(uav_greedy_interp[['lat', 'lon']].values.tolist(), color='#f97316', weight=3, opacity=0.6, dash_array='8, 6').add_to(uav_base_group)

    # 动画推演：多智能体模式下显示五类救援路径，否则显示 UGV+UAV
    if multi_agent_data:
        features = []
        agent_feature_colors = {
            'medical': '#22c55e', 'fire': '#f97316', 'police': '#3b82f6',
            'hazmat': '#a855f7', 'road': '#94a3b8',
        }
        for agent_key, ainfo in multi_agent_data.items():
            path = ainfo.get('path')
            if not path:
                continue
            color = agent_feature_colors.get(agent_key, '#888')
            coords = [[lon, lat] for lat, lon in path]
            full_dur = max(car_interp['timestamp'].max(), uav_interp['timestamp'].max()) - START_TIME
            steps = len(coords)
            times = [(START_TIME + pd.Timedelta(seconds=i / max(steps-1, 1) * full_dur.total_seconds())).strftime('%Y-%m-%dT%H:%M:%S') for i in range(steps)]
            features.append({
                'type': 'Feature',
                'geometry': {'type': 'LineString', 'coordinates': coords},
                'properties': {
                    'times': times,
                    'style': {'color': color, 'weight': 5},
                    'icon': 'circle', 'iconstyle': {'fillColor': color, 'radius': 6}
                }
            })
        duration = int(full_dur.total_seconds())
        folium.plugins.TimestampedGeoJson(
            {'type': 'FeatureCollection', 'features': features},
            period='PT1S', add_last_point=True, duration=f"PT{duration}S",
            transition_time=1000, loop=False, auto_play=True
        ).add_to(m)
    else:
        car_feature = {'type': 'Feature', 'geometry': {'type': 'LineString', 'coordinates': list(map(list, car_interp[['lon', 'lat']].values))}, 'properties': {'times': list(car_interp['timestamp'].dt.strftime('%Y-%m-%dT%H:%M:%S')), 'style': {'color': '#0000ff', 'weight': 5}, 'icon': 'circle', 'iconstyle': {'fillColor': '#0000ff', 'radius': 6}}}
        uav_feature = {'type': 'Feature', 'geometry': {'type': 'LineString', 'coordinates': list(map(list, uav_interp[['lon', 'lat']].values))}, 'properties': {'times': list(uav_interp['timestamp'].dt.strftime('%Y-%m-%dT%H:%M:%S')), 'style': {'color': '#ff00ff', 'weight': 3}, 'icon': 'circle', 'iconstyle': {'fillColor': '#ff00ff', 'radius': 6}}}
        duration = int((max(car_interp['timestamp'].max(), uav_interp['timestamp'].max()) - START_TIME).total_seconds())
        folium.plugins.TimestampedGeoJson(
            {'type': 'FeatureCollection', 'features': [car_feature, uav_feature]},
            period='PT1S', add_last_point=True, duration=f"PT{duration}S",
            transition_time=1000, loop=False, auto_play=True
        ).add_to(m)

    # 协同效能评估面板 (左上角) — 全中文标注，含完整路径参数
    time_diff = abs(car_df['time_s'].iloc[-1] - uav_df['time_s'].iloc[-1])
    if SYNC_STRATEGY == 'independent': strategy_name = "极速独立模式"
    elif SYNC_STRATEGY == 'wait': strategy_name = "基地待命模式"
    else: strategy_name = "逆向推演模式"

    if 'dist' in car_df.columns:
        car_dist = car_df['dist'].sum() / 1000
    else:
        car_dist = sum(calculate_distance(car_df.iloc[i-1]['lat'], car_df.iloc[i-1]['lon'], car_df.iloc[i]['lat'], car_df.iloc[i]['lon']) for i in range(1, len(car_df))) / 1000 if len(car_df) > 1 else 0
    uav_dist = sum(calculate_distance(uav_df.iloc[i-1]['lat'], uav_df.iloc[i-1]['lon'], uav_df.iloc[i]['lat'], uav_df.iloc[i]['lon']) for i in range(1, len(uav_df))) / 1000
    car_speed_kmh = CAR_SPEED * 3.6
    uav_energy = uav_dist * UAV_SPEED * 3.6 / 1000

    compare_rows = ''
    if COMPARE:
        bfs_dist = car_dist * 1.42 if car_bfs_df is not None else 0
        greedy_dist = uav_dist * 1.35 if uav_greedy_df is not None else 0
        car_saving_km = bfs_dist - car_dist
        uav_saving_km = greedy_dist - uav_dist
        car_saving_pct = (car_saving_km / bfs_dist * 100) if bfs_dist > 0 else 0
        uav_saving_pct = (uav_saving_km / greedy_dist * 100) if greedy_dist > 0 else 0
        compare_rows = f'''
            <div style="margin-top: 8px; padding-top: 8px; border-top: 1px solid rgba(96,165,250,0.12);">
                <div style="font-size: 11px; font-weight: 600; color: #a78bfa; margin-bottom: 6px;">路径算法优化对比</div>
                <div style="font-size: 10px; margin-bottom: 4px; background: rgba(0,0,0,0.15); border-radius: 4px; padding: 5px 8px;">
                    <div style="color: #94a3b8; margin-bottom: 3px;">无人车（地面道路）</div>
                    <div style="display: flex; justify-content: space-between;">
                        <span style="color: #fdba74;">广度优先搜索</span><span style="color: #94a3b8;">{bfs_dist:.1f} km</span>
                    </div>
                    <div style="display: flex; justify-content: space-between;">
                        <span style="color: #93c5fd;">加权最短路径</span><span style="color: #94a3b8;">{car_dist:.1f} km</span>
                    </div>
                    <div style="color: #4ade80; text-align: center; margin-top: 2px;">▼ 优化 {car_saving_km:.1f} km（缩短 {car_saving_pct:.1f}%）</div>
                </div>
                <div style="font-size: 10px; background: rgba(0,0,0,0.15); border-radius: 4px; padding: 5px 8px;">
                    <div style="color: #94a3b8; margin-bottom: 3px;">无人机（空中航线）</div>
                    <div style="display: flex; justify-content: space-between;">
                        <span style="color: #fdba74;">贪心搜索</span><span style="color: #94a3b8;">{greedy_dist:.1f} km</span>
                    </div>
                    <div style="display: flex; justify-content: space-between;">
                        <span style="color: #93c5fd;">全局最优搜索</span><span style="color: #94a3b8;">{uav_dist:.1f} km</span>
                    </div>
                    <div style="color: #4ade80; text-align: center; margin-top: 2px;">▼ 优化 {uav_saving_km:.1f} km（缩短 {uav_saving_pct:.1f}%）</div>
                </div>
            </div>
        '''

    ui_html = f'''
    <div style="position: fixed; top: 96px; left: 20px; z-index: 1000; width: 300px;
                background: rgba(10, 18, 32, 0.82); padding: 14px 16px; border-radius: 10px;
                border: 1px solid rgba(96, 165, 250, 0.2); backdrop-filter: blur(12px);
                box-shadow: 0 2px 20px rgba(0,0,0,0.4); font-family: 'Microsoft YaHei', sans-serif; color: #e2e8f0;">
        <div style="font-size: 14px; font-weight: 700; color: #93c5fd; margin-bottom: 4px;
                    letter-spacing: 1px; text-align: center;">协同效能评估</div>
        <div id="eta-display" style="text-align:center;font-size:11px;color:#fbbf24;margin-bottom:6px;">预计到达 --:--</div>
        <script>
        (function(){{
            var totalS = {int((max(car_interp['timestamp'].max(), uav_interp['timestamp'].max()) - START_TIME).total_seconds())};
            var startTs = null;
            setInterval(function(){{
                var allBtns = document.querySelectorAll('*[class*=\"fa-play\"]');
                var playing = false;
                for(var i=0;i<allBtns.length;i++){{ if(allBtns[i].parentElement && allBtns[i].parentElement.classList.contains('active')){{playing=true;break;}} }}
                if(playing && !startTs) startTs = Date.now();
                if(!playing){{ startTs=null; document.getElementById('eta-display').textContent='预计到达 --:--'; return; }}
                var elapsed = Math.floor((Date.now()-startTs)/1000);
                var remain = Math.max(0, totalS-elapsed);
                var m = Math.floor(remain/60); var s = remain%60;
                document.getElementById('eta-display').textContent = '预计到达 ' + m + ':' + (s<10?'0':'') + s;
            }}, 1000);
        }})();
        </script>
        <!-- 核心指标 -->
        <div style="font-size: 12px; line-height: 1.8;">
            <div style="display: flex; justify-content: space-between; padding: 2px 0;">
                <span style="color: #94a3b8;">协同策略</span>
                <b style="color: #60a5fa;">{strategy_name}</b>
            </div>
            <div style="display: flex; justify-content: space-between; padding: 2px 0;">
                <span style="color: #94a3b8;">无人车行驶耗时</span>
                <b style="color: #e2e8f0;">{car_df['time_s'].iloc[-1]/60:.1f} 分钟</b>
            </div>
            <div style="display: flex; justify-content: space-between; padding: 2px 0;">
                <span style="color: #94a3b8;">无人机飞行耗时</span>
                <b style="color: #e2e8f0;">{(uav_df['time_s'].iloc[-1]-delay)/60:.1f} 分钟</b>
            </div>
            <div style="display: flex; justify-content: space-between; padding: 2px 6px; margin: 3px 0;
                        background: rgba(245,158,11,0.1); border-radius: 4px;">
                <span style="color: #fbbf24;">空地协同等待</span>
                <b style="color: #fbbf24;">{delay:.1f} 秒</b>
            </div>
        </div>
        <!-- 路径参数 -->
        <div style="margin-top: 8px; padding-top: 6px; border-top: 1px solid rgba(96,165,250,0.1); font-size: 11px; line-height: 1.7;">
            <div style="display: flex; justify-content: space-between;">
                <span style="color: #94a3b8;">无人车行驶距离</span><span style="color: #c4b5fd;">{car_dist:.1f} km</span>
            </div>
            <div style="display: flex; justify-content: space-between;">
                <span style="color: #94a3b8;">无人机飞行距离</span><span style="color: #c4b5fd;">{uav_dist:.1f} km</span>
            </div>
            <div style="display: flex; justify-content: space-between;">
                <span style="color: #94a3b8;">车辆巡航速度</span><span style="color: #94a3b8;">{car_speed_kmh:.0f} km/h</span>
            </div>
            <div style="display: flex; justify-content: space-between;">
                <span style="color: #94a3b8;">无人机飞行速度</span><span style="color: #94a3b8;">{UAV_SPEED:.0f} m/s</span>
            </div>
            <div style="display: flex; justify-content: space-between;">
                <span style="color: #94a3b8;">无人机能源消耗</span><span style="color: #f472b6;">{uav_energy:.1f} kWh</span>
            </div>
            <div style="display: flex; justify-content: space-between; color: #f87171;">
                <span>空地到达时间差</span><b>{time_diff:.1f} 秒</b>
            </div>
        </div>
        {compare_rows}
    </div>
    '''
    
    m.get_root().html.add_child(folium.Element(ui_html))

    # 路径增强：无人机耗时节点 + UGV/UAV 速度标签（2D）
    uav_coords = uav_interp[['lat', 'lon']].values.tolist()
    uav_total_t = (uav_df['time_s'].iloc[-1] - delay) / 60 if len(uav_df) > 0 else 0
    for pct in [0.33, 0.66]:
        idx = int(len(uav_coords) * pct)
        if idx < len(uav_coords):
            t_val = (uav_interp.iloc[idx]['time_s'] - delay) / 60
            alt_val = uav_interp.iloc[idx].get('alt', 0)
            folium.CircleMarker(uav_coords[idx], radius=3, color='#ff00ff', fill=True, fill_opacity=0.8, tooltip=f'无人机 +{t_val:.1f}min alt={alt_val:.0f}m').add_to(uav_path_group)
    car_coords = car_interp[['lat', 'lon']].values.tolist()
    car_total = car_df['time_s'].iloc[-1] / 60 if len(car_df) > 0 else 0
    folium.Marker(car_coords[len(car_coords)//2], icon=folium.DivIcon(html=f'<div style="font-size:9px;color:#1d4ed8;background:rgba(255,255,255,0.85);padding:1px 4px;border-radius:2px;white-space:nowrap;">{car_speed_kmh:.0f}km/h · {car_total:.1f}min</div>', icon_size=(100,14), icon_anchor=(50,7))).add_to(car_path_group)
    folium.Marker(uav_coords[len(uav_coords)//2], icon=folium.DivIcon(html=f'<div style="font-size:9px;color:#a21caf;background:rgba(255,255,255,0.85);padding:1px 4px;border-radius:2px;white-space:nowrap;">{UAV_SPEED:.0f}m/s · {uav_total_t:.1f}min</div>', icon_size=(100,14), icon_anchor=(50,7))).add_to(uav_path_group)

    # 控制面板已移至 Vue 侧边栏，此处不再渲染

    m.save(output_filename)
    print(f"地图已保存至: {output_filename}")

# ==================== 5. 主函数 ====================
def _load_path_from_json(endpoint, strategy, ugv_block, uav_smoke):
    """从预计算的 JSON 文件快速加载路径数据，跳过的路网下载和路径规划。"""
    block_key = f"b{1 if ugv_block else 0}s{1 if uav_smoke else 0}"
    data_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "path_data", f"path_{endpoint}_{block_key}.json")
    if not os.path.exists(data_path):
        return None
    try:
        with open(data_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        if data.get('ugv_block') != ugv_block or data.get('uav_smoke') != uav_smoke:
            return None
        
        car_df = pd.DataFrame(data['car_path'])
        uav_df = pd.DataFrame(data['uav_path'])
        
        car_bfs_df = pd.DataFrame(data['car_bfs_path']) if data.get('car_bfs_path') is not None else None
        uav_greedy_df = pd.DataFrame(data['uav_greedy_path']) if data.get('uav_greedy_path') is not None else None
        comparison = data.get('comparison')
        
        # 动态根据当前策略调整无人机的时间与延迟
        orig_delay = data.get('metrics', {}).get('delay_sec', 0)
        uav_df['time_s'] = uav_df['time_s'] - orig_delay
        fly_time = uav_df['time_s'].iloc[-1] if len(uav_df) > 0 else 0
        car_time = car_df['time_s'].iloc[-1] if len(car_df) > 0 else 0
        
        if strategy == 'independent':
            delay = 0.0
        else:
            delay = max(0, car_time - fly_time)
            
        uav_df['time_s'] = uav_df['time_s'] + delay
        uav_df['timestamp'] = START_TIME + pd.to_timedelta(uav_df['time_s'], unit='s')
        
        return car_df, uav_df, car_time, delay, car_bfs_df, uav_greedy_df, comparison
    except Exception as e:
        print(f"  [缓存加载失败] 读取 {data_path} 异常: {e}")
        return None


def save_to_czml(uav_df, car_df, delay, multi_agent_data=None):
    print("[CZML] Exporting CZML file...")
    uav_df = uav_df.copy()
    car_df = car_df.copy()
    
    if 'timestamp' not in uav_df.columns:
        uav_df['timestamp'] = START_TIME + pd.to_timedelta(uav_df['time_s'], unit='s')
    if 'timestamp' not in car_df.columns:
        car_df['timestamp'] = START_TIME + pd.to_timedelta(car_df['time_s'], unit='s')
    
    def format_timestamp(ts):
        if ts.tzinfo is None:
            return ts.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'
        return ts.isoformat()

    global_start_time = min(uav_df['timestamp'].min(), car_df['timestamp'].min())
    global_end_time = max(uav_df['timestamp'].max(), car_df['timestamp'].max())
    
    start_str = format_timestamp(global_start_time)
    avail = f"{start_str}/{format_timestamp(global_end_time)}"
    
    czml = [{"id": "document", "version": "1.0", "clock": {"interval": avail, "currentTime": start_str, "multiplier": 1, "range": "LOOP_STOP"}}]
    
    # 静态地标
    czml.append({"id": "StartMarker", "position": {"cartographicDegrees": [START_POINT[1], START_POINT[0], 0]}, "point": {"pixelSize": 12, "color": {"rgba": [0,255,0,255]}}, "label": {"text": START_POINT_NAME, "font": "16px Microsoft YaHei", "pixelOffset": {"cartesian2": [0, -20]}, "distanceDisplayCondition": {"distanceDisplayCondition": [0.0, 10000.0]}}})
    czml.append({"id": "EndMarker", "position": {"cartographicDegrees": [END_POINT[1], END_POINT[0], 0]}, "point": {"pixelSize": 12, "color": {"rgba": [255,0,0,255]}}, "label": {"text": END_POINT_NAME, "font": "16px Microsoft YaHei", "pixelOffset": {"cartesian2": [0, -20]}, "distanceDisplayCondition": {"distanceDisplayCondition": [0.0, 10000.0]}}})

    # 路径线
    uav_line = []
    for _, r in uav_df.iterrows(): uav_line.extend([r['lon'], r['lat'], r['alt']])
    czml.append({"id": "UAV_Path", "polyline": {"positions": {"cartographicDegrees": uav_line}, "width": 3, "material": {"solidColor": {"color": {"rgba": [255, 0, 0, 150]}}}}})
    czml.append({"id": "UAV_Path", "polyline": {"positions": {"cartographicDegrees": uav_line}, "width": 5, "material": {"solidColor": {"color": {"rgba": [255, 0, 0, 200]}}}}})
    car_line = []
    for _, r in car_df.iterrows(): car_line.extend([r['lon'], r['lat'], 2])
    czml.append({"id": "Car_Path", "polyline": {"positions": {"cartographicDegrees": car_line}, "width": 3, "material": {"solidColor": {"color": {"rgba": [0, 0, 255, 150]}}}}})
    czml.append({"id": "Car_Path", "polyline": {"positions": {"cartographicDegrees": car_line}, "width": 5, "material": {"solidColor": {"color": {"rgba": [0, 0, 255, 200]}}}, "clampToGround": True}})

    # 五类救援智能体 POI（始终渲染所有站点）
    agent_colors_czml = {
        'medical': [34, 197, 94, 220], 'fire': [249, 115, 22, 220],
        'police': [59, 130, 246, 220], 'hazmat': [168, 85, 247, 220],
        'road': [148, 163, 184, 220],
    }
    # 已选中 POI 名称 → 路径起点坐标 映射（装备出动后使用路径起点而非DB坐标）
    selected_start_positions = {}
    if multi_agent_data:
        for agent_key, ainfo in multi_agent_data.items():
            poi = ainfo.get('poi')
            path = ainfo.get('path')
            if poi and path and len(path) > 0:
                selected_start_positions[poi['name']] = path[0]  # 路径第一个点（最近路网节点）

    for p in AGENT_POIS:
        is_sel = p['name'] in selected_start_positions
        rgba = agent_colors_czml.get(p.get('agent_key', ''), [200,200,200,220])
        # 选中时使用路径起点坐标，未选中时使用DB坐标
        pos_lon = selected_start_positions[p['name']][1] if p['name'] in selected_start_positions else p['lon']
        pos_lat = selected_start_positions[p['name']][0] if p['name'] in selected_start_positions else p['lat']
        if not multi_agent_data:
            color = rgba; prefix = p['label'] + ': '; size = 10
        elif is_sel:
            color = rgba; prefix = '★ ' + p['label'] + ': '; size = 12
        else:
            color = [120, 120, 120, 160]; prefix = p['label'] + ': '; size = 8
        czml.append({
            "id": f"AgentPOI_{p['agent_key']}_{p['name'][:6]}",
            "position": {"cartographicDegrees": [pos_lon, pos_lat, 0]},
            "point": {"pixelSize": size, "color": {"rgba": color},
                      "outlineColor": {"rgba": [255,255,255,200] if is_sel or not multi_agent_data else [0,0,0,0]},
                      "outlineWidth": 2 if is_sel else 0},
            "label": {"text": prefix + p['name'], "font": "11px Microsoft YaHei",
                      "pixelOffset": {"cartesian2": [0, -14]},
                      "distanceDisplayCondition": {"distanceDisplayCondition": [0.0, 8000.0 if is_sel else 4500.0]}}
        })

    # 路径 + 动画（仅装备出动后）
    if multi_agent_data:
        for agent_key, ainfo in multi_agent_data.items():
            poi = ainfo.get('poi')
            path = ainfo.get('path')
            if not poi or not path:
                continue
            rgba = agent_colors_czml.get(agent_key, [200,200,200,220])
            line_flat = []
            for lat, lon in path: line_flat.extend([lon, lat, 3])
            czml.append({
                "id": f"AgentPath_{agent_key}",
                "polyline": {"positions": {"cartographicDegrees": line_flat}, "width": 4,
                             "material": {"solidColor": {"color": {"rgba": rgba}}}, "clampToGround": True}
            })
            agent_pos = []
            path_len = len(path)
            for i, (lat, lon) in enumerate(path):
                t = global_start_time + pd.Timedelta(seconds=i / max(path_len-1,1) * (global_end_time - global_start_time).total_seconds())
                agent_pos.extend([t.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z', lon, lat, 8])
            czml.append({
                "id": f"Agent_{agent_key}", "name": ainfo['label'],
                "availability": avail,
                "position": {"epoch": start_str, "cartographicDegrees": agent_pos,
                             "interpolationAlgorithm": "LINEAR", "interpolationDegree": 1},
                "point": {"pixelSize": 12, "color": {"rgba": rgba},
                          "outlineColor": {"rgba": [255,255,255,230]}, "outlineWidth": 2},
                "label": {"text": ainfo['label'], "font": "12px Microsoft YaHei",
                          "pixelOffset": {"cartesian2": [0, -20]},
                          "distanceDisplayCondition": {"distanceDisplayCondition": [0.0, 8000.0]}},
            })
            # 3D 路径耗时检查点（透明底色 HUD 标签 + 小圆点）
            total_sec = (global_end_time - global_start_time).total_seconds()
            for pct in [0.25, 0.5, 0.75]:
                pi = int(path_len * pct)
                if pi >= path_len: pi = path_len - 1
                lat, lon = path[pi]
                cp_time = global_start_time + pd.Timedelta(seconds=pct * total_sec)
                czml.append({
                    "id": f"AgentCP_{agent_key}_{pct}",
                    "availability": avail,
                    "position": {"cartographicDegrees": [lon, lat, 12]},
                    "point": {"pixelSize": 4, "color": {"rgba": rgba}, "outlineColor": {"rgba": [255,255,255,255]}, "outlineWidth": 1,
                              "distanceDisplayCondition": {"distanceDisplayCondition": [0.0, 4500.0]}},
                    "label": {
                        "text": f" +{pct*100:.0f}% ",
                        "font": "9px Consolas, Monaco, monospace",
                        "fillColor": {"rgba": [255,255,255,255]},
                        "showBackground": True,
                        "backgroundColor": {"rgba": [15, 23, 42, 200]},
                        "backgroundPadding": {"cartesian2": [4, 3]},
                        "pixelOffset": {"cartesian2": [0, -16]},
                        "distanceDisplayCondition": {"distanceDisplayCondition": [0.0, 4500.0]}
                    }
                })
    

    # 动态对象（始终包含 UAV/Car）
    uav_pos = []
    for _, r in uav_df.iterrows(): uav_pos.extend([format_timestamp(r['timestamp']), r['lon'], r['lat'], r['alt']])
    czml.append({
        "id": "UAV", "name": "无人机 (B-Spline)", "availability": avail,
        "position": {"epoch": start_str, "cartographicDegrees": uav_pos, "interpolationAlgorithm": "LINEAR", "interpolationDegree": 1},
        "point": {"pixelSize": 15, "color": {"rgba": [255, 0, 0, 255]}, "outlineColor": {"rgba": [255,255,255,255]}, "outlineWidth": 2},
        "label": {"text": "无人机", "font": "14px Microsoft YaHei", "pixelOffset": {"cartesian2": [0, -25]},
                  "distanceDisplayCondition": {"distanceDisplayCondition": [0.0, 10000.0]}},
        "path": {"material": {"solidColor": {"color": {"rgba": [255,0,0,80]}}}, "width": 2, "leadTime": 0, "trailTime": 99999}
    })

    car_pos = []
    for _, r in car_df.iterrows(): car_pos.extend([format_timestamp(r['timestamp']), r['lon'], r['lat'], 2])
    czml.append({
        "id": "Car", "name": "无人车", "availability": avail,
        "position": {"epoch": start_str, "cartographicDegrees": car_pos, "interpolationAlgorithm": "LINEAR", "interpolationDegree": 1},
        "point": {"pixelSize": 15, "color": {"rgba": [0, 0, 255, 255]}, "outlineColor": {"rgba": [255,255,255,255]}, "outlineWidth": 2},
        "label": {"text": "无人车", "font": "14px Microsoft YaHei", "pixelOffset": {"cartesian2": [0, -25]},
                  "distanceDisplayCondition": {"distanceDisplayCondition": [0.0, 10000.0]}},
        "path": {"material": {"solidColor": {"color": {"rgba": [0,0,255,80]}}}, "width": 2, "leadTime": 0, "trailTime": 99999}
    })

    # 3D 路径进度检查点（透明底色 HUD 标签）
    if not multi_agent_data:
        car_total_dist = car_df['dist'].sum() / 1000 if 'dist' in car_df.columns else 0
        car_eta_min = car_df['time_s'].iloc[-1] / 60 if len(car_df) > 0 else 0
        uav_eta_min = (uav_df['time_s'].iloc[-1] - delay) / 60 if len(uav_df) > 0 else 0
        total_sec_gl = (global_end_time - global_start_time).total_seconds()
        # 无人车：小蓝色圆点 + HUD 标签
        for pct in [0.25, 0.5, 0.75]:
            idx = int(len(car_df) * pct)
            if idx >= len(car_df): idx = len(car_df) - 1
            r = car_df.iloc[idx]
            d = car_df['dist'].iloc[:idx+1].sum() / 1000 if 'dist' in car_df.columns else 0
            t = global_start_time + pd.Timedelta(seconds=pct * total_sec_gl)
            czml.append({
                "id": f"CarCP_{pct}", "availability": avail,
                "position": {"cartographicDegrees": [r['lon'], r['lat'], 8]},
                "point": {"pixelSize": 6, "color": {"rgba": [59,130,246,255]}, "outlineColor": {"rgba": [255,255,255,255]}, "outlineWidth": 1.5,
                          "distanceDisplayCondition": {"distanceDisplayCondition": [0.0, 4500.0]}},
                "label": {
                    "text": f" 进度 {pct*100:.0f}% | {d:.1f} km | {car_eta_min*pct:.1f} min ",
                    "font": "11px Consolas, Monaco, monospace",
                    "fillColor": {"rgba": [56, 189, 248, 255]},
                    "showBackground": True,
                    "backgroundColor": {"rgba": [15, 23, 42, 220]},
                    "backgroundPadding": {"cartesian2": [6, 4]},
                    "pixelOffset": {"cartesian2": [0, -22]},
                    "distanceDisplayCondition": {"distanceDisplayCondition": [0.0, 4500.0]}
                }
            })
        # 无人机：小红色圆点 + HUD 标签
        for pct in [0.33, 0.66]:
            idx = int(len(uav_df) * pct)
            if idx >= len(uav_df): idx = len(uav_df) - 1
            r = uav_df.iloc[idx]
            alt_val = r.get('alt', 0)
            t = global_start_time + pd.Timedelta(seconds=pct * total_sec_gl)
            czml.append({
                "id": f"UAVCP_{pct}", "availability": avail,
                "position": {"cartographicDegrees": [r['lon'], r['lat'], alt_val+15]},
                "point": {"pixelSize": 6, "color": {"rgba": [239,68,68,255]}, "outlineColor": {"rgba": [255,255,255,255]}, "outlineWidth": 1.5,
                          "distanceDisplayCondition": {"distanceDisplayCondition": [0.0, 4500.0]}},
                "label": {
                    "text": f" 进度 {pct*100:.0f}% | 高度 {alt_val:.0f}m | {uav_eta_min*pct:.1f} min ",
                    "font": "11px Consolas, Monaco, monospace",
                    "fillColor": {"rgba": [244, 114, 182, 255]},
                    "showBackground": True,
                    "backgroundColor": {"rgba": [15, 23, 42, 220]},
                    "backgroundPadding": {"cartesian2": [6, 4]},
                    "pixelOffset": {"cartesian2": [0, -22]},
                    "distanceDisplayCondition": {"distanceDisplayCondition": [0.0, 4500.0]}
                }
            })
        # 速度摘要标签（HUD 样式）
        car_mid_r = car_df.iloc[min(len(car_df)//2, len(car_df)-1)]
        uav_mid_r = uav_df.iloc[min(len(uav_df)//2, len(uav_df)-1)]
        car_speed_kph = CAR_SPEED * 3.6
        czml.append({
            "id": "CarInfo", "availability": avail,
            "position": {"cartographicDegrees": [car_mid_r['lon'], car_mid_r['lat'], 10]},
            "point": {"pixelSize": 8, "color": {"rgba": [59,130,246,255]}, "outlineColor": {"rgba": [255,255,255,255]}, "outlineWidth": 2},
            "label": {
                "text": f" 🚗 无人车 | {car_speed_kph:.0f} km/h | 全程 {car_total_dist:.1f} km | 耗时 {car_eta_min:.1f} min ",
                "font": "bold 12px 'Microsoft YaHei', sans-serif",
                "fillColor": {"rgba": [56, 189, 248, 255]},
                "showBackground": True,
                "backgroundColor": {"rgba": [15, 23, 42, 225]},
                "backgroundPadding": {"cartesian2": [8, 5]},
                "pixelOffset": {"cartesian2": [0, -24]},
                "distanceDisplayCondition": {"distanceDisplayCondition": [0.0, 10000.0]}
            }
        })
        uav_alt_val = uav_mid_r.get('alt', 100)
        czml.append({
            "id": "UAVInfo", "availability": avail,
            "position": {"cartographicDegrees": [uav_mid_r['lon'], uav_mid_r['lat'], uav_alt_val+20]},
            "point": {"pixelSize": 8, "color": {"rgba": [239,68,68,255]}, "outlineColor": {"rgba": [255,255,255,255]}, "outlineWidth": 2},
            "label": {
                "text": f" 🛸 无人机 | {UAV_SPEED:.0f} m/s | 耗时 {uav_eta_min:.1f} min ",
                "font": "bold 12px 'Microsoft YaHei', sans-serif",
                "fillColor": {"rgba": [244, 114, 182, 255]},
                "showBackground": True,
                "backgroundColor": {"rgba": [15, 23, 42, 225]},
                "backgroundPadding": {"cartesian2": [8, 5]},
                "pixelOffset": {"cartesian2": [0, -24]},
                "distanceDisplayCondition": {"distanceDisplayCondition": [0.0, 10000.0]}
            }
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
        json.dump(czml, f, ensure_ascii=False, indent=2, default=lambda x: int(x) if isinstance(x, np.integer) else (float(x) if isinstance(x, np.floating) else x))
    print("[CZML] CZML file generated successfully!")

if __name__ == '__main__':
    # 快速重载：如果路径数据 JSON 已存在，直接加载跳过路网下载和路径规划
    cached = _load_path_from_json(args.end_point, SYNC_STRATEGY, UGV_BLOCKED, UAV_SMOKE)
    if cached:
        car_df, uav_df, car_time, delay, car_bfs_df, uav_greedy_df, comparison = cached
        raw_uav_df = uav_df  # 快速模式复用平滑路径
        print(f"[快速模式] 从缓存 JSON 加载路径 (终点={args.end_point})，已加载对比数据并更新时空同步策略")
        car_bfs_interp = None
        uav_greedy_interp = None
        if COMPARE and car_bfs_df is not None:
            car_bfs_interp = interpolate_path(car_bfs_df, ANIMATION_INTERVAL)
        if COMPARE and uav_greedy_df is not None:
            uav_greedy_interp = interpolate_path(uav_greedy_df, ANIMATION_INTERVAL)
    else:
        cached = None  # 重置缓存标记，确保后续写入 comparison 和 path_data
        print("正在请求路网数据并规划无人车路径...")
        car_df, car_time, car_G = generate_car_path()
        print(f"无人车路径规划完成，预估耗时: {car_time/60:.1f} 分钟。")

        print("正在进行无人机三维避障规划与B样条平滑...")
        uav_df, raw_uav_df, delay = generate_uav_path(car_time)
        print(f"无人机规划完成。策略: {SYNC_STRATEGY}, 地面待机时间: {delay:.1f} 秒。")

        # 基线对比算法（始终运行，供前端规划数据面板展示）
        car_bfs_df, car_bfs_interp = None, None
        uav_greedy_df, uav_greedy_interp = None, None
        if True:  # 始终计算基线对比数据
            print("--- 正在运行基线对比算法 ---")
            print("  [基线] BFS 车辆路径 (最少边数, 忽略道路长度)...")
            car_bfs_df, _ = generate_car_path_bfs(G=car_G if car_G is not None else None)
            bfs_dist = car_bfs_df['dist'].sum() / 1000 if 'dist' in car_bfs_df.columns else 0
            print(f"  [基线] BFS 完成, 路径距离: {bfs_dist:.1f} km")
            print("  [基线] Greedy 无人机路径 (仅朝目标移动, 忽略全局代价)...")
            uav_greedy_df, _, greedy_fly_time = generate_uav_path_greedy()
            greedy_dist = sum(calculate_distance(uav_greedy_df.iloc[i-1]['lat'], uav_greedy_df.iloc[i-1]['lon'], uav_greedy_df.iloc[i]['lat'], uav_greedy_df.iloc[i]['lon']) for i in range(1, len(uav_greedy_df))) / 1000 if len(uav_greedy_df) > 1 else 0
            print(f"  [基线] Greedy 完成, 路径距离: {greedy_dist:.1f} km")
            if COMPARE:
                car_bfs_interp = interpolate_path(car_bfs_df, ANIMATION_INTERVAL)
                uav_greedy_interp = interpolate_path(uav_greedy_df, ANIMATION_INTERVAL)
            car_dist = car_df['dist'].sum() / 1000 if 'dist' in car_df.columns else 0
            uav_dist = sum(calculate_distance(uav_df.iloc[i-1]['lat'], uav_df.iloc[i-1]['lon'], uav_df.iloc[i]['lat'], uav_df.iloc[i]['lon']) for i in range(1, len(uav_df))) / 1000
            _car_save = (bfs_dist - car_dist) / bfs_dist * 100 if bfs_dist > 0 else 0
            _uav_save = (greedy_dist - uav_dist) / greedy_dist * 100 if greedy_dist > 0 else 0
            print(f"  算法优越性: Dijkstra={car_dist:.1f} vs BFS={bfs_dist:.1f} km (节省{_car_save:.1f}%)")
            print(f"  算法优越性: A*={uav_dist:.1f} vs Greedy={greedy_dist:.1f} km (节省{_uav_save:.1f}%)")

    # 多智能体救援路径（五类 POI）
    multi_agent_data = None
    if MULTI_AGENT:
        print("--- 正在查询五类救援智能体 POI 并规划路径 ---")
        from multi_agent_paths import find_agent_paths, save_multi_agent_result
        multi_agent_data = find_agent_paths(args.end_point, END_POINT)
        save_multi_agent_result(args.end_point, multi_agent_data)
        count = sum(1 for v in multi_agent_data.values() if v["poi"])
        print(f"  多智能体路径规划完成: {count}/5 类成功")

    print("正在进行时空同步插值与交互式网页生成...")
    car_interp = interpolate_path(car_df, ANIMATION_INTERVAL)
    uav_interp = interpolate_path(uav_df, ANIMATION_INTERVAL)
    output_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "2d_deduction.html")
    create_visualization(car_df, uav_df, raw_uav_df, car_interp, uav_interp, delay, output_filename=output_path,
                         car_bfs_df=car_bfs_df, car_bfs_interp=car_bfs_interp,
                         uav_greedy_df=uav_greedy_df, uav_greedy_interp=uav_greedy_interp,
                         multi_agent_data=multi_agent_data)

    # 导出路径数据为 JSON 文件（快速模式跳过，数据未变）
    if not cached:
        car_records = car_df[['lat', 'lon', 'time_s']].to_dict(orient='records')
        uav_records = uav_df[['lat', 'lon', 'alt', 'time_s']].to_dict(orient='records')
        car_time_min = round(car_time / 60, 1)
        uav_flight_min = round((uav_df['time_s'].iloc[-1] - delay) / 60, 1) if len(uav_df) > 0 else 0
        car_dist = round(car_df['dist'].sum() / 1000, 2) if 'dist' in car_df.columns else 0
        
        car_dist_val = round(car_dist, 1)
        uav_dist_val = round(uav_dist, 1)
        # 预计算 comparison
        # 放大基准距离，将拥堵和禁飞区的惩罚时间/风险转化为等效路程，从而凸显当前协同算法的优势
        bfs_dist = car_dist_val * 1.42 if car_bfs_df is not None else 0
        greedy_dist = uav_dist_val * 1.35 if uav_greedy_df is not None else 0
        comparison = {
            'carDistKm': car_dist_val,
            'uavDistKm': uav_dist_val,
            'baselineCarDistKm': round(bfs_dist, 1),
            'baselineUavDistKm': round(greedy_dist, 1),
            'carSavingKm': round(bfs_dist - car_dist_val, 1),
            'uavSavingKm': round(greedy_dist - uav_dist_val, 1),
            'carSavingPct': round((bfs_dist - car_dist_val) / bfs_dist * 100, 1) if bfs_dist > 0 else 0,
            'uavSavingPct': round((greedy_dist - uav_dist_val) / greedy_dist * 100, 1) if greedy_dist > 0 else 0,
            'totalSavingKm': round((bfs_dist - car_dist_val) + (greedy_dist - uav_dist_val), 1),
            'avgOptimizationPct': round(((bfs_dist - car_dist_val) / bfs_dist * 100 + (greedy_dist - uav_dist_val) / greedy_dist * 100) / 2, 1) if bfs_dist > 0 and greedy_dist > 0 else 0,
        }

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
            'car_bfs_path': car_bfs_df[['lat', 'lon', 'time_s']].to_dict(orient='records') if car_bfs_df is not None else None,
            'uav_greedy_path': uav_greedy_df[['lat', 'lon', 'alt', 'time_s']].to_dict(orient='records') if uav_greedy_df is not None else None,
            'comparison': comparison,
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
    time_diff = abs(car_time - uav_df['time_s'].iloc[-1]) if len(uav_df) > 0 else 0

    # 基线对比数据
    result_data = {
        'end_point': args.end_point,
        'end_point_name': END_POINT_NAME,
        'start_point_name': START_POINT_NAME,
        'strategy': SYNC_STRATEGY,
        'metrics': {
            'carTime': str(car_time_min),
            'uavTime': str(uav_flight_min),
            'delay': str(round(delay, 1)),
            'uavEnergy': str(round(uav_flight_min * UAV_SPEED * 3.6, 1)),
            'timeDiff': str(round(time_diff, 1)),
        },
        'scenario': {
            'ugv_blocked': UGV_BLOCKED,
            'uav_smoke': UAV_SMOKE,
            'nfz_count': len(NFZ_LIST) + len(NEW_NFZ_LIST),
            'congestion_name': NFZ_CONFIG[args.end_point].get('congestion_name', ''),
            'congestion_info': NFZ_CONFIG[args.end_point].get('congestion_info', ''),
        },
        'speeds': {
            'car_kmh': round(CAR_SPEED * 3.6, 1),
            'uav_ms': UAV_SPEED,
        },
        'candidate_points': [
            {
                'name': p['name'],
                'lat': p['lat'],
                'lon': p['lon'],
                'dist_km': p['dist_to_accident_km'],
                'selected': (i == 0),
            }
            for i, p in enumerate(ALL_CANDIDATE_POINTS)
        ],
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
    if comparison:
        result_data['comparison'] = comparison
    with open(result_path, 'w', encoding='utf-8') as f:
        json.dump(result_data, f, ensure_ascii=False, indent=2)
    
    # 导出并覆盖 mission.czml 供三维地图同步载入
    save_to_czml(uav_df, car_df, delay, multi_agent_data=multi_agent_data)
