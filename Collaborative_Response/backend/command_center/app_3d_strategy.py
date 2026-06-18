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
    'leak':  (30.713897297892842, 114.7804552777263),   # 武汉市消防救援支队新洲区大队
    'crash': (30.321919430948842, 113.41817301217728),   # 仙桃市毛嘴镇消防站
}
START_POINT_NAMES = {
    'leak':  '武汉市消防救援支队新洲区大队',
    'crash': '仙桃市毛嘴镇消防站',
}

END_POINTS = {
    'leak':  (30.607380528841425, 114.87332066872784),   # 油罐车泄漏现场
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

# 禁飞区 & 拥堵区 — 按终点分别配置，确保每条路径都有绕行效果
NFZ_CONFIG = {
    'leak': {
        'nfz':      [{'center': (30.67, 114.82), 'radius': 2000}],   # 新洲→黄冈段 路径中段拦截
        'buffer':   [{'center': (30.63, 114.85), 'radius': 1500}],   # 路径南侧缓冲区
        'congestion': [
            [30.660, 114.815], [30.660, 114.835],
            [30.645, 114.835], [30.645, 114.815],
        ],
    },
    'crash': {
        'nfz':      [{'center': (30.365, 113.28), 'radius': 2000}],  # 三伏潭镇北侧拦截
        'buffer':   [{'center': (30.34, 113.22),  'radius': 1500}],  # 胡场镇南侧拦截
        'congestion': [
            [30.360, 113.255], [30.360, 113.275],
            [30.345, 113.275], [30.345, 113.255],
        ],
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
        df = pd.DataFrame(path_coords, columns=['lat', 'lon'])
        df['dist'] = 0.0
        for i in range(1, len(df)): df.loc[i, 'dist'] = calculate_distance(df.loc[i-1,'lat'], df.loc[i-1,'lon'], df.loc[i,'lat'], df.loc[i,'lon'])
        total_time = df['dist'].sum() / CAR_SPEED
        df['time_s'] = np.linspace(0, total_time, len(df))
        df['timestamp'] = START_TIME + pd.to_timedelta(df['time_s'], unit='s')
        return df, total_time, G
    except Exception as e: return pd.DataFrame([START_POINT, END_POINT], columns=['lat', 'lon']), 100, None

def generate_uav_path(car_time):
    pad = 0.05
    min_lat, max_lat = min(START_POINT[0], END_POINT[0]) - pad, max(START_POINT[0], END_POINT[0]) + pad
    min_lon, max_lon = min(START_POINT[1], END_POINT[1]) - pad, max(START_POINT[1], END_POINT[1]) + pad
    rows, cols = int(calculate_distance(min_lat, min_lon, max_lat, min_lon) / GRID_RES), int(calculate_distance(min_lat, min_lon, min_lat, max_lon) / GRID_RES)
    grid = np.zeros((rows, cols), dtype=int)
    
    if UAV_SMOKE:
        for nfz in NFZ_LIST + NEW_NFZ_LIST:
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
    city_file = 'xiantao.json' if args.end_point == 'crash' else 'huanggang.json'
    geojson_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', 'vue-project_all', 'public', 'Dashboard', city_file)
    if os.path.exists(geojson_path):
        import json
        with open(geojson_path, 'r', encoding='utf-8') as f:
            city_data = json.load(f)
            
        features = city_data.get('features', [])
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

            folium.GeoJson(
                city_data,
                style_function=lambda x: {'color': '#00e5ff', 'weight': 3, 'fillOpacity': 0, 'dashArray': '5, 5'}
            ).add_to(m)

            # 计算城市边界并自动缩放以在视图中完整显示城市
            city_lats = [pt[0] for ring in mask_locations[1:] for pt in ring]
            city_lons = [pt[1] for ring in mask_locations[1:] for pt in ring]
            if city_lats and city_lons:
                m.fit_bounds([[min(city_lats), min(city_lons)], [max(city_lats), max(city_lons)]])
    # -----------------------

    car_path_group = folium.FeatureGroup(name='车辆路径 (UGV Path)', show=True).add_to(m)
    uav_path_group = folium.FeatureGroup(name='无人机路径 (UAV Path)', show=True).add_to(m)

    if COMPARE and car_bfs_interp is not None:
        car_base_group = folium.FeatureGroup(name='车辆-基线BFS (UGV Baseline)', show=True).add_to(m)
    if COMPARE and uav_greedy_interp is not None:
        uav_base_group = folium.FeatureGroup(name='无人机-基线Greedy (UAV Baseline)', show=True).add_to(m)

    if UGV_BLOCKED:
        folium.Polygon(locations=CONGESTION_ZONE_POLYGON, color='#3b82f6', weight=2, fill=True, fill_opacity=0.2, tooltip='地面拥堵/救援禁区').add_to(m)

    if UAV_SMOKE:
        nfz = NFZ_LIST[0]
        folium.Circle(location=nfz['center'], radius=nfz['radius'], color='#ef4444', weight=2, fill=True, fill_opacity=0.3, tooltip='核心禁飞区 (Core NFZ)').add_to(m)
        new_nfz = NEW_NFZ_LIST[0]
        folium.Circle(location=new_nfz['center'], radius=new_nfz['radius'], color='#f97316', weight=2, fill=True, fill_opacity=0.25, tooltip='风险缓冲区 (Buffer Zone)').add_to(m)

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
            <hr style="margin: 10px 0; border: 0; border-top: 2px solid #dbeafe;">
            <div style="background: linear-gradient(135deg, #eff6ff 0%, #dbeafe 100%); border-radius: 6px; padding: 10px 12px; margin-bottom: 6px;">
                <div style="font-size: 12px; font-weight: 700; color: #1e40af; text-align: center; margin-bottom: 10px;">
                    ★ 算法优越性分析 ★
                </div>

                <!-- UGV 对比 -->
                <div style="margin-bottom: 8px;">
                    <div style="font-size: 11px; font-weight: 600; color: #475569; margin-bottom: 5px;">
                        <span style="display:inline-block;width:12px;height:12px;background:#f97316;border-radius:3px;margin-right:6px;vertical-align:middle;"></span>
                        <span style="color:#9a3412;">基准算法</span>
                        <span style="float:right;color:#9a3412;">BFS: {bfs_dist:.1f} km</span>
                    </div>
                    <div style="font-size: 11px; font-weight: 600; color: #475569;">
                        <span style="display:inline-block;width:12px;height:12px;background:#2563eb;border-radius:3px;margin-right:6px;vertical-align:middle;"></span>
                        <span style="color:#1e40af;">本文算法</span>
                        <span style="float:right;color:#1e40af;">Dijkstra: {car_dist:.1f} km</span>
                    </div>
                    <div style="background: #dcfce7; border-radius: 4px; padding: 3px 8px; margin-top: 4px; text-align: center;">
                        <span style="font-size: 11px; font-weight: 700; color: #15803d;">
                            ▼ 车辆路径优化 <b>{car_saving_km:.1f} km</b>（缩短 <b>{car_saving_pct:.1f}%</b>）
                        </span>
                    </div>
                </div>

                <!-- UAV 对比 -->
                <div>
                    <div style="font-size: 11px; font-weight: 600; color: #475569; margin-bottom: 5px;">
                        <span style="display:inline-block;width:12px;height:12px;background:#f97316;border-radius:3px;margin-right:6px;vertical-align:middle;"></span>
                        <span style="color:#9a3412;">基准算法</span>
                        <span style="float:right;color:#9a3412;">Greedy: {greedy_dist:.1f} km</span>
                    </div>
                    <div style="font-size: 11px; font-weight: 600; color: #475569;">
                        <span style="display:inline-block;width:12px;height:12px;background:#2563eb;border-radius:3px;margin-right:6px;vertical-align:middle;"></span>
                        <span style="color:#1e40af;">本文算法</span>
                        <span style="float:right;color:#1e40af;">A*: {uav_dist:.1f} km</span>
                    </div>
                    <div style="background: #dcfce7; border-radius: 4px; padding: 3px 8px; margin-top: 4px; text-align: center;">
                        <span style="font-size: 11px; font-weight: 700; color: #15803d;">
                            ▼ 无人机路径优化 <b>{uav_saving_km:.1f} km</b>（缩短 <b>{uav_saving_pct:.1f}%</b>）
                        </span>
                    </div>
                </div>

                <!-- 总结 -->
                <div style="background: #166534; border-radius: 4px; padding: 5px 10px; margin-top: 8px; text-align: center;">
                    <span style="font-size: 11px; font-weight: 700; color: #f0fdf4;">
                        综合路径总节省 <b>{(car_saving_km + uav_saving_km):.1f} km</b>（平均优化 <b>{((car_saving_pct + uav_saving_pct) / 2):.1f}%</b>）
                    </span>
                </div>
            </div>
        '''

    ui_html = f'''
    <div style="position: fixed; top: 110px; left: 40px; z-index: 1000; width: 300px; background: rgba(255,255,255,0.9); padding: 15px; border-radius: 10px; box-shadow: 0 4px 15px rgba(0,0,0,0.2); font-family: 'Arial', sans-serif;">
        <h4 style="margin: 0 0 12px; color: #1e40af; text-align: center; border-bottom: 2px solid #ddd; padding-bottom: 8px;">ISD/CAS/RCD 效能对比</h4>
        <div style="font-size: 13px; line-height: 1.6;">
            <div style="display: flex; justify-content: space-between;"><span>协同机制:</span> <b>{strategy_name}</b></div>
            <div style="display: flex; justify-content: space-between;"><span>车辆(UGV)耗时:</span> <b>{car_df['time_s'].iloc[-1]/60:.1f} min</b></div>
            <div style="display: flex; justify-content: space-between;"><span>无人机(UAV)飞行:</span> <b>{(uav_df['time_s'].iloc[-1]-delay)/60:.1f} min</b></div>
            <div style="display: flex; justify-content: space-between; background: #fffbeb; padding: 0 3px;"><span>无人机地面待机:</span> <b style="color:#b45309;">{delay:.1f} s</b></div>
            <hr style="margin: 10px 0; border: 0; border-top: 1px solid #eee;">
            <div style="display: flex; justify-content: space-between; color: #c2410c;"><span>协同终端时间差:</span> <b>{time_diff:.1f} s</b></div>
            {compare_rows}
        </div>
    </div>
    '''
    
    # 精简图例 (右上角)
    legend_html = f'''
    <div style="position: fixed; top: 20px; right: 20px; z-index: 1000; width: 220px; background: white; padding: 12px 15px; border: 1.5px solid black; font-family: 'Times New Roman', Times, serif, 'SimSun'; color: black; box-shadow: none; border-radius: 0;">
        <h4 style="margin: 0 0 10px; text-align: center; color: black; font-size: 15px; font-weight: bold; border-bottom: 1px solid black; padding-bottom: 6px;">图 例 / Legend</h4>
        <div style="font-size: 13px; line-height: 1.8;">
            <div style="display: flex; align-items: center; margin-bottom: 4px;">
                <span style="width: 30px; height: 3px; background: #0000ff; display: inline-block; margin-right: 12px;"></span>
                车辆(UGV)路径 / UGV Path
            </div>
            <div style="display: flex; align-items: center; margin-bottom: 4px;">
                <span style="width: 30px; height: 0px; border-top: 3px dashed #ff00ff; display: inline-block; margin-right: 12px;"></span>
                无人机(UAV)路径 / UAV Path
            </div>{"""            <div style="display: flex; align-items: center; margin-bottom: 4px;">
                <span style="width: 30px; height: 0px; border-top: 3px dashed #22c55e; display: inline-block; margin-right: 12px;"></span>
                基线BFS(车) / BFS Baseline
            </div>
            <div style="display: flex; align-items: center; margin-bottom: 4px;">
                <span style="width: 30px; height: 0px; border-top: 3px dashed #f97316; display: inline-block; margin-right: 12px;"></span>
                基线Greedy(机) / Greedy BL
            </div>""" if COMPARE else ''}
            <div style="display: flex; align-items: center; margin-top: 6px;">
                <i class="fa fa-map-marker fa-lg" style="color:green; margin-right: 16px; margin-left: 8px;"></i> 起点：{START_POINT_NAME}
            </div>
            <div style="display: flex; align-items: center; margin-top: 4px;">
                <i class="fa fa-map-marker fa-lg" style="color:red; margin-right: 16px; margin-left: 8px;"></i> 终点：{END_POINT_NAME}
            </div>
        </div>
    </div>
    '''

    m.get_root().html.add_child(folium.Element(ui_html))
    # 注入学术图例
    m.get_root().html.add_child(folium.Element(legend_html))

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
        'obstacles': [
            {'type': 'polygon', 'color': '#3b82f6', 'positions': [p for point in CONGESTION_ZONE_POLYGON for p in [point[1], point[0]]]},
            {'type': 'cylinder', 'center': [NFZ_LIST[0]['center'][1], NFZ_LIST[0]['center'][0]], 'radius': NFZ_LIST[0]['radius'], 'color': '#ef4444', 'height': 200},
        ] if UGV_BLOCKED or UAV_SMOKE else [],
        'updated_at': datetime.now(timezone.utc).isoformat() if 'timezone' in dir() else datetime.now().isoformat(),
    }
    with open(result_path, 'w', encoding='utf-8') as f:
        json.dump(result_data, f, ensure_ascii=False, indent=2)
