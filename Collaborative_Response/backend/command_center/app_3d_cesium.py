import pandas as pd
import numpy as np
import folium
import osmnx as ox
import networkx as nx
from folium.plugins import TimestampedGeoJson
import math
import warnings
from datetime import datetime
from geopy.distance import geodesic
import os 
import json 
from graph_utils import load_drive_graph_from_local_or_osm
# 🔥 1. 引入 B-Spline 必要的库
from scipy.interpolate import splprep, splev 

# 忽略警告
warnings.filterwarnings("ignore")

# ==================== 1. 全局配置 (已修复缺失变量)111222 ====================
CAR_SPEED = 8.33   # 30 km/h
UAV_SPEED = 20.0   # 20 m/s

# 坐标 (武汉光谷)
START_POINT = (30.5185, 114.4140) 
END_POINT = (30.4751, 114.4046)   

# --- 障碍物配置 ---
NFZ_LIST = [{'center': (30.495, 114.41), 'radius': 600}]
NEW_NFZ_LIST = [{'center': (30.505, 114.415), 'radius': 500}] 
CONGESTION_ZONE_POLYGON = [[30.512, 114.408], [30.512, 114.412], [30.508, 114.412], [30.508, 114.408]]

# 网格精度 (米)
GRID_RES = 30.0 
START_TIME = pd.Timestamp('2025-01-01 09:00:00')
ANIMATION_INTERVAL = 1.0

# 🔥🔥🔥【修复点】补全缺失的变量 🔥🔥🔥
MIN_GROUND_CLEARANCE = 5.0  # 最小离地高度 (米)

# ==================== 2. 辅助函数 ====================
def calculate_distance(lat1, lon1, lat2, lon2):
    return geodesic((lat1, lon1), (lat2, lon2)).meters

def interpolate_path(df, interval=1.0):
    """简单的时间插值，用于生成动画帧"""
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

# 🔥 2. B-Spline 平滑算法
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
    except Exception as e:
        print(f"B-Spline 平滑失败: {e}")
        return waypoints

# ==================== 3. 车辆规划 ====================
def generate_car_path():
    print("🚗 正在规划车辆路径...")
    graph_file = "wuhan_drive.graphml"
    if os.path.exists(graph_file):
        try: os.remove(graph_file)
        except: pass

    try:
        G = load_drive_graph_from_local_or_osm(
            START_POINT,
            dist=6000,
            network_type='drive',
            simplify=False,
        )
        lats = [p[0] for p in CONGESTION_ZONE_POLYGON]
        lons = [p[1] for p in CONGESTION_ZONE_POLYGON]
        min_lat, max_lat = min(lats), max(lats)
        min_lon, max_lon = min(lons), max(lons)

        for u, v, k, data in G.edges(keys=True, data=True):
            length = data.get('length', 1.0)
            u_node = G.nodes[u]
            v_node = G.nodes[v]
            u_in = (min_lat <= u_node['y'] <= max_lat) and (min_lon <= u_node['x'] <= max_lon)
            v_in = (min_lat <= v_node['y'] <= max_lat) and (min_lon <= v_node['x'] <= max_lon)
            if u_in or v_in: data['weight'] = length * 99999 
            else: data['weight'] = length

        orig = ox.nearest_nodes(G, START_POINT[1], START_POINT[0])
        dest = ox.nearest_nodes(G, END_POINT[1], END_POINT[0])
        route = nx.shortest_path(G, orig, dest, weight='weight')
        path_coords = [(G.nodes[n]['y'], G.nodes[n]['x']) for n in route]
        if (path_coords[0][0] != START_POINT[0]): path_coords.insert(0, START_POINT)

        df = pd.DataFrame(path_coords, columns=['lat', 'lon'])
        df['dist'] = 0.0
        for i in range(1, len(df)):
            df.loc[i, 'dist'] = calculate_distance(df.loc[i-1,'lat'], df.loc[i-1,'lon'], df.loc[i,'lat'], df.loc[i,'lon'])
        
        total_time = df['dist'].sum() / CAR_SPEED
        df['time_s'] = np.linspace(0, total_time, len(df))
        df['timestamp'] = START_TIME + pd.to_timedelta(df['time_s'], unit='s')
        
        print(f"✅ 车辆路径生成完毕: {len(df)} 个点")
        return df, total_time

    except Exception as e:
        print(f"❌ 车辆规划出错: {e}")
        return pd.DataFrame([START_POINT, END_POINT], columns=['lat', 'lon']), 100

# ==================== 4. 无人机规划 ====================
def generate_uav_path(car_time):
    print("🚁 正在规划无人机路径 (A* + B-Spline)...")
    pad = 0.02
    min_lat = min(START_POINT[0], END_POINT[0]) - pad
    max_lat = max(START_POINT[0], END_POINT[0]) + pad
    min_lon = min(START_POINT[1], END_POINT[1]) - pad
    max_lon = max(START_POINT[1], END_POINT[1]) + pad
    
    rows = int(calculate_distance(min_lat, min_lon, max_lat, min_lon) / GRID_RES)
    cols = int(calculate_distance(min_lat, min_lon, min_lat, max_lon) / GRID_RES)
    grid = np.zeros((rows, cols), dtype=int)
    all_nfz = NFZ_LIST + NEW_NFZ_LIST
    
    for nfz in all_nfz:
        c_lat, c_lon = nfz['center']
        r = int((c_lat - min_lat) / (max_lat - min_lat) * rows)
        c = int((c_lon - min_lon) / (max_lon - min_lon) * cols)
        rad_grid = int(nfz['radius'] * 1.1 / GRID_RES)
        y, x = np.ogrid[-r:rows-r, -c:cols-c]
        mask = x*x + y*y <= rad_grid*rad_grid
        grid[mask] = 1 
        
    start_node = (min(rows-1, int((START_POINT[0] - min_lat) / (max_lat - min_lat) * rows)), min(cols-1, int((START_POINT[1] - min_lon) / (max_lon - min_lon) * cols)))
    end_node = (min(rows-1, int((END_POINT[0] - min_lat) / (max_lat - min_lat) * rows)), min(cols-1, int((END_POINT[1] - min_lon) / (max_lon - min_lon) * cols)))
    
    G = nx.grid_2d_graph(rows, cols)
    G.add_edges_from([((x, y), (x+1, y+1)) for x in range(rows-1) for y in range(cols-1)] + [((x+1, y), (x, y+1)) for x in range(rows-1) for y in range(cols-1)], weight=1.414)
    nodes_to_remove = [n for n in G.nodes if grid[n[0]][n[1]] == 1]
    G.remove_nodes_from(nodes_to_remove)
    
    try:
        path = nx.astar_path(G, start_node, end_node, heuristic=lambda a, b: ((a[0]-b[0])**2 + (a[1]-b[1])**2)**0.5)
    except nx.NetworkXNoPath:
        path = [start_node, end_node]

    raw_waypoints = []
    for r, c in path:
        lat = min_lat + (r / rows) * (max_lat - min_lat)
        lon = min_lon + (c / cols) * (max_lon - min_lon)
        raw_waypoints.append([lat, lon, 100])
    
    raw_df = pd.DataFrame(raw_waypoints, columns=['lat', 'lon', 'alt'])
    smooth_waypoints = b_spline_smooth(raw_waypoints, num_points=len(raw_waypoints)*5, k=3)
    if smooth_waypoints:
        smooth_waypoints[0][0] = START_POINT[0]
        smooth_waypoints[0][1] = START_POINT[1]
        smooth_waypoints[-1][0] = END_POINT[0]
        smooth_waypoints[-1][1] = END_POINT[1]
    df = pd.DataFrame(smooth_waypoints, columns=['lat', 'lon', 'alt'])
    
    total_dist = 0
    for i in range(1, len(df)):
        total_dist += calculate_distance(df.iloc[i-1]['lat'], df.iloc[i-1]['lon'], df.iloc[i]['lat'], df.iloc[i]['lon'])
    
    fly_time = total_dist / UAV_SPEED
    delay = max(0, car_time - fly_time)
    
    df['time_s'] = np.linspace(0, fly_time, len(df)) + delay
    df['timestamp'] = START_TIME + pd.to_timedelta(df['time_s'], unit='s')
    
    print(f"✅ 无人机路径生成完毕。")
    return df, raw_df

# ==================== 5. 生成 CZML (中文优化) ====================
def save_to_czml(uav_df, car_df):
    print("💾 正在导出 CZML 文件...")
    
    global_start_time = min(uav_df['timestamp'].min(), car_df['timestamp'].min())
    global_end_time = max(uav_df['timestamp'].max(), car_df['timestamp'].max())
    
    start_str = global_start_time.isoformat() + "Z"
    avail = f"{start_str}/{global_end_time.isoformat()}Z"
    
    czml = [{"id": "document", "version": "1.0", "clock": {"interval": avail, "currentTime": start_str, "multiplier": 10, "range": "LOOP_STOP"}}]
    
    # 静态地标
    czml.append({"id": "StartMarker", "position": {"cartographicDegrees": [START_POINT[1], START_POINT[0], 0]}, "point": {"pixelSize": 12, "color": {"rgba": [0,255,0,255]}}, "label": {"text": "救援基地", "font": "16px Microsoft YaHei", "pixelOffset": {"cartesian2": [0, -20]}}})
    czml.append({"id": "EndMarker", "position": {"cartographicDegrees": [END_POINT[1], END_POINT[0], 0]}, "point": {"pixelSize": 12, "color": {"rgba": [255,0,0,255]}}, "label": {"text": "事故现场", "font": "16px Microsoft YaHei", "pixelOffset": {"cartesian2": [0, -20]}}})

    # 路径线
    uav_line = []
    for _, r in uav_df.iterrows(): uav_line.extend([r['lon'], r['lat'], r['alt']])
    czml.append({"id": "UAV_Path", "polyline": {"positions": {"cartographicDegrees": uav_line}, "width": 3, "material": {"solidColor": {"color": {"rgba": [255, 0, 0, 150]}}}}})
    
    car_line = []
    for _, r in car_df.iterrows(): car_line.extend([r['lon'], r['lat'], 2])
    czml.append({"id": "Car_Path", "polyline": {"positions": {"cartographicDegrees": car_line}, "width": 3, "material": {"solidColor": {"color": {"rgba": [0, 0, 255, 150]}}}}})

    # 动态对象
    uav_pos = []
    for _, r in uav_df.iterrows(): uav_pos.extend([r['timestamp'].isoformat()+"Z", r['lon'], r['lat'], r['alt']])
    czml.append({
        "id": "UAV", "name": "无人机 (B-Spline)", "availability": avail,
        "position": {"epoch": start_str, "cartographicDegrees": uav_pos, "interpolationAlgorithm": "LINEAR", "interpolationDegree": 1},
        "point": {"pixelSize": 15, "color": {"rgba": [255, 0, 0, 255]}, "outlineColor": {"rgba": [255,255,255,255]}, "outlineWidth": 2},
        "label": {"text": "无人机", "font": "14px Microsoft YaHei", "pixelOffset": {"cartesian2": [0, -25]}}
    })

    car_pos = []
    for _, r in car_df.iterrows(): car_pos.extend([r['timestamp'].isoformat()+"Z", r['lon'], r['lat'], 2])
    czml.append({
        "id": "Car", "name": "无人车", "availability": avail,
        "position": {"epoch": start_str, "cartographicDegrees": car_pos, "interpolationAlgorithm": "LINEAR", "interpolationDegree": 1},
        "point": {"pixelSize": 15, "color": {"rgba": [0, 0, 255, 255]}, "outlineColor": {"rgba": [255,255,255,255]}, "outlineWidth": 2},
        "label": {"text": "无人车", "font": "14px Microsoft YaHei", "pixelOffset": {"cartesian2": [0, -25]}}
    })

    # 障碍物
    for i, nfz in enumerate(NFZ_LIST + NEW_NFZ_LIST):
        color = [255, 0, 0, 100] if i==0 else [255, 165, 0, 100]
        czml.append({
            "id": f"NFZ_{i}", "position": {"cartographicDegrees": [nfz['center'][1], nfz['center'][0], 200]},
            "cylinder": {"length": 400, "topRadius": nfz['radius'], "bottomRadius": nfz['radius'], "material": {"solidColor": {"color": {"rgba": color}}}}
        })
    poly = []
    for p in CONGESTION_ZONE_POLYGON: poly.extend([p[1], p[0], 0])
    czml.append({"id": "Congestion", "polygon": {"positions": {"cartographicDegrees": poly}, "material": {"solidColor": {"color": {"rgba": [0, 0, 255, 80]}}}}})

    with open("mission.czml", "w", encoding='utf-8') as f: json.dump(czml, f, ensure_ascii=False)
    print("✅ CZML 文件已生成!")

# ==================== 6. Folium 可视化 (中文优化) ====================
def create_visualization(car_df, uav_df, raw_uav_df, congestion_polygon, car_interp, uav_interp, output_filename='wuhan_rescue_optimized.html'):
    if car_df.empty or uav_df.empty: return None

    map_center = [(START_POINT[0] + END_POINT[0]) / 2, (START_POINT[1] + END_POINT[1]) / 2]
    m = folium.Map(location=map_center, zoom_start=14, tiles="OpenStreetMap")

    # 中文图层名称
    car_layer = folium.FeatureGroup(name='🚗 车辆路径 (Ground Path)', show=True).add_to(m)
    uav_smooth_layer = folium.FeatureGroup(name='🚁 平滑路径 (Smooth Trajectory)', show=True).add_to(m)
    uav_raw_layer = folium.FeatureGroup(name='❌ 原始路径 (Raw A*)', show=True).add_to(m)
    zone_layer = folium.FeatureGroup(name='🚫 禁飞/拥堵区 (Restricted Zones)', show=True).add_to(m)

    # 绘制区域
    if congestion_polygon:
        folium.Polygon(locations=congestion_polygon, color='blue', fill=True, fill_opacity=0.2, popup='<b>拥堵区域</b><br>车辆需绕行').add_to(zone_layer)
    for i, nfz in enumerate(NFZ_LIST + NEW_NFZ_LIST):
        color = 'red' if i == 0 else 'orange'
        label = '核心禁飞区' if i == 0 else '临时禁飞区'
        folium.Circle(location=nfz['center'], radius=nfz['radius'], color=color, fill=True, fill_opacity=0.3, popup=f'<b>{label}</b><br>半径: {nfz["radius"]}m').add_to(zone_layer)

    # 绘制起终点
    folium.Marker(START_POINT, icon=folium.Icon(color='green', icon='home', prefix='fa'), tooltip='救援基地', popup='<b>起点: 救援基地</b>').add_to(m)
    folium.Marker(END_POINT, icon=folium.Icon(color='red', icon='fire', prefix='fa'), tooltip='事故现场', popup='<b>终点: 事故现场</b>').add_to(m)

    # 绘制路径
    folium.PolyLine(car_interp[['lat', 'lon']].values.tolist(), color='blue', weight=5, opacity=0.6, popup='车辆路径').add_to(car_layer)
    
    # 平滑路径 (实线)
    folium.PolyLine(
        uav_interp[['lat', 'lon']].values.tolist(),
        color='#ff00ff', weight=4, opacity=0.8,
        popup='<b>无人机平滑路径</b><br>算法: B-Spline<br>特征: C2连续，无尖锐拐点'
    ).add_to(uav_smooth_layer)

    # 原始路径 (虚线)
    folium.PolyLine(
        raw_uav_df[['lat', 'lon']].values.tolist(),
        color='black', weight=2, opacity=1.0, dash_array='5, 8',
        popup='<b>A* 原始折线</b><br>未平滑'
    ).add_to(uav_raw_layer)

    # 动画
    car_feature = {'type': 'Feature', 'geometry': {'type': 'LineString', 'coordinates': list(map(list, car_interp[['lon', 'lat']].values))}, 'properties': {'times': list(car_interp['timestamp'].dt.strftime('%Y-%m-%dT%H:%M:%S')), 'style': {'color': 'blue', 'weight': 5}, 'icon': 'circle', 'iconstyle': {'fillColor': 'blue', 'fillOpacity': 0.8, 'stroke': 'true', 'radius': 5}, 'popup': '车辆实时位置'}}
    uav_feature = {'type': 'Feature', 'geometry': {'type': 'LineString', 'coordinates': list(map(list, uav_interp[['lon', 'lat']].values))}, 'properties': {'times': list(uav_interp['timestamp'].dt.strftime('%Y-%m-%dT%H:%M:%S')), 'style': {'color': '#ff00ff', 'weight': 3}, 'icon': 'circle', 'iconstyle': {'fillColor': '#ff00ff', 'fillOpacity': 0.8, 'stroke': 'true', 'radius': 5}, 'popup': '无人机实时位置'}}
    
    latest = max(car_interp['timestamp'].max(), uav_interp['timestamp'].max())
    duration = int((latest - START_TIME).total_seconds())
    
    folium.plugins.TimestampedGeoJson(
        {'type': 'FeatureCollection', 'features': [car_feature, uav_feature]},
        period='PT1S', add_last_point=True, duration=f"PT{duration}S",
        transition_time=1000, loop=True, auto_play=True
    ).add_to(m)

    # UI 面板 (中文)
    params_html = f"""
    <div style="font-size:12px; line-height:1.5;">
        <b>🚗 车辆速度:</b> {CAR_SPEED * 3.6:.1f} km/h<br>
        <b>🚁 无人机速度:</b> {UAV_SPEED * 3.6:.1f} km/h<br>
        <b>📏 最小离地:</b> {MIN_GROUND_CLEARANCE} m<br>
        <b>⚙️ 协同策略:</b> 自动延迟同步 (Auto-Sync)
    </div>
    """
    
    ui_html = f'''
    <div style="position: fixed; top: 10px; left: 50px; z-index: 1000; width: 250px; background: white; padding: 10px; border-radius: 5px; box-shadow: 0 0 10px rgba(0,0,0,0.3);">
        <h4 style="margin: 0 0 5px; text-align: center;">🚁 空地协同救援仿真</h4>
        <hr style="margin: 5px 0;">
        {params_html}
        <div style="margin-top:5px; color:gray; font-size:10px;">
            * 黑色虚线: 原始 A* 路径<br>
            * 洋红实线: B-Spline 优化路径
        </div>
    </div>
    '''
    m.get_root().html.add_child(folium.Element(ui_html))

    folium.LayerControl().add_to(m)
    m.save(output_filename)
    print(f"✓ 可视化地图已保存: {output_filename}")

# ==================== 主程序 ====================
if __name__ == '__main__':
    print("🚀 开始仿真任务...")
    
    car_df, car_time = generate_car_path()
    uav_df, raw_uav_df = generate_uav_path(car_time)
    
    print("🔄 生成动画数据...")
    car_interp = interpolate_path(car_df, ANIMATION_INTERVAL)
    uav_interp = interpolate_path(uav_df, ANIMATION_INTERVAL)
    
    create_visualization(car_df, uav_df, raw_uav_df, CONGESTION_ZONE_POLYGON, car_interp, uav_interp)
    save_to_czml(uav_df, car_df)
    
    print("\n✅ 所有任务完成！")
    print("   1. 打开 wuhan_rescue_optimized.html 查看 Folium 交互地图。")
    print("   2. 将 mission.czml 拖入 Cesium Viewer 查看三维仿真。")
