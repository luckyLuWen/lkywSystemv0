import pandas as pd
import numpy as np
import folium
import osmnx as ox
import networkx as nx
from folium.plugins import TimestampedGeoJson
import warnings
from datetime import datetime
from geopy.distance import geodesic
import os 
from scipy.interpolate import splprep, splev 
import json
import argparse
from graph_utils import load_drive_graph_from_local_or_osm

warnings.filterwarnings("ignore")

# ==================== 1. 接收前端指令与全局配置 ====================
parser = argparse.ArgumentParser()
parser.add_argument('--ugv_block', type=int, default=1)
parser.add_argument('--uav_smoke', type=int, default=1)
# 默认策略设为 RCD 逆向推演以展示最佳效果
parser.add_argument('--strategy', type=str, default='rcd') 
args = parser.parse_args()

UGV_BLOCKED = (args.ugv_block == 1)
UAV_SMOKE = (args.uav_smoke == 1)
SYNC_STRATEGY = str(args.strategy).strip().lower()

CAR_SPEED = 22.22  # 80 km/h (长途救援真实车速)
UAV_SPEED = 20.0   # 20 m/s (大型救援无人机)
START_POINT = (30.321919430948842, 113.41817301217728)  # 起点：仙桃市毛嘴镇消防站
END_POINT = (30.238683, 113.070272)                     # 终点：油罐车泄漏现场

# 核心禁飞区：放在三伏潭镇附近（路径中段偏北），迫使无人机绕行
NFZ_LIST = [{'center': (30.33, 113.30), 'radius': 2000}]
# 风险缓冲区：放在胡场镇附近（路径中段偏南），扩大避障范围
NEW_NFZ_LIST = [{'center': (30.27, 113.18), 'radius': 1500}]
# 地面拥堵区：拦截G318沪聂线主干道（毛嘴→仙桃方向）
CONGESTION_ZONE_POLYGON = [
    [30.310, 113.245],
    [30.310, 113.260],
    [30.295, 113.260],
    [30.295, 113.245]
]
GRID_RES = 100.0   # 适配约35km大范围网格 
START_TIME = pd.Timestamp('2025-01-01 09:00:00')
ANIMATION_INTERVAL = 1.0

# ==================== 2. 辅助与算法 ====================
def calculate_distance(lat1, lon1, lat2, lon2): 
    return geodesic((lat1, lon1), (lat2, lon2)).meters

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
        fetch_radius = int(straight_dist * 1.5)
        print(f"正在拉取底层真实路网... (预计半径: {fetch_radius/1000:.1f} km)")
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
        return df, total_time
    except Exception as e: return pd.DataFrame([START_POINT, END_POINT], columns=['lat', 'lon']), 100

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

# ==================== 4. 生成 Folium ====================
def create_visualization(car_df, uav_df, raw_uav_df, car_interp, uav_interp, delay, output_filename='2d_deduction.html'):
    map_center = [(START_POINT[0] + END_POINT[0]) / 2, (START_POINT[1] + END_POINT[1]) / 2]
    
    # 🌟 修改点 1：开启 detect_retina=True (高清视网膜图层，极大提高清晰度) 和 control_scale=True (添加学术论文必备的比例尺)
    m = folium.Map(location=map_center, zoom_start=11, tiles="OpenStreetMap", detect_retina=True, control_scale=True)

    car_path_group = folium.FeatureGroup(name='车辆路径 (UGV Path)', show=True).add_to(m)
    uav_path_group = folium.FeatureGroup(name='无人机路径 (UAV Path)', show=True).add_to(m)

    if UGV_BLOCKED: 
        folium.Polygon(locations=CONGESTION_ZONE_POLYGON, color='#3b82f6', weight=2, fill=True, fill_opacity=0.2, tooltip='地面拥堵/救援禁区').add_to(m)
    
    if UAV_SMOKE:
        # 核心禁飞区 (红色)
        nfz = NFZ_LIST[0]
        folium.Circle(location=nfz['center'], radius=nfz['radius'], color='#ef4444', weight=2, fill=True, fill_opacity=0.3, tooltip='核心禁飞区 (Core NFZ)').add_to(m)
        # 风险缓冲区 (橙色)
        new_nfz = NEW_NFZ_LIST[0]
        folium.Circle(location=new_nfz['center'], radius=new_nfz['radius'], color='#f97316', weight=2, fill=True, fill_opacity=0.25, tooltip='风险缓冲区 (Buffer Zone)').add_to(m)
    
    folium.Marker(START_POINT, icon=folium.Icon(color='green', icon='home'), tooltip='起点：仙桃市毛嘴镇消防站').add_to(m)
    folium.Marker(END_POINT, icon=folium.Icon(color='red', icon='fire'), tooltip='终点：市区道路-油罐车泄漏现场').add_to(m)

    # 车：蓝色实线
    folium.PolyLine(car_interp[['lat', 'lon']].values.tolist(), color='#0000ff', weight=5, opacity=0.7).add_to(car_path_group)
    # 飞机：紫色虚线
    folium.PolyLine(uav_interp[['lat', 'lon']].values.tolist(), color='#ff00ff', weight=3, opacity=0.7, dash_array='5, 5').add_to(uav_path_group)

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

    # 效能评估报告面板 (左上角) - 如果截图时不需要可以注释掉这段
    time_diff = abs(car_df['time_s'].iloc[-1] - uav_df['time_s'].iloc[-1])
    if SYNC_STRATEGY == 'independent': strategy_name = "极速独立模式 (ISD)"
    elif SYNC_STRATEGY == 'wait': strategy_name = "基地待命模式 (CAS)"
    else: strategy_name = "RCD 逆向推演 (本文)"

    ui_html = f'''
    <div style="position: fixed; top: 20px; left: 60px; z-index: 1000; width: 280px; background: rgba(255,255,255,0.9); padding: 15px; border-radius: 10px; box-shadow: 0 4px 15px rgba(0,0,0,0.2); font-family: 'Arial', sans-serif;">
        <h4 style="margin: 0 0 12px; color: #1e40af; text-align: center; border-bottom: 2px solid #ddd; padding-bottom: 8px;">ISD/CAS/RCD 效能对比</h4>
        <div style="font-size: 13px; line-height: 1.6;">
            <div style="display: flex; justify-content: space-between;"><span>协同机制:</span> <b>{strategy_name}</b></div>
            <div style="display: flex; justify-content: space-between;"><span>车辆(UGV)耗时:</span> <b>{car_df['time_s'].iloc[-1]/60:.1f} min</b></div>
            <div style="display: flex; justify-content: space-between;"><span>无人机(UAV)飞行:</span> <b>{(uav_df['time_s'].iloc[-1]-delay)/60:.1f} min</b></div>
            <div style="display: flex; justify-content: space-between; background: #fffbeb; padding: 0 3px;"><span>无人机地面待机:</span> <b style="color:#b45309;">{delay:.1f} s</b></div>
            <hr style="margin: 10px 0; border: 0; border-top: 1px solid #eee;">
            <div style="display: flex; justify-content: space-between; color: #c2410c;"><span>协同终端时间差:</span> <b>{time_diff:.1f} s</b></div>
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
            </div>
            <div style="display: flex; align-items: center; margin-top: 6px;">
                <i class="fa fa-map-marker fa-lg" style="color:green; margin-right: 16px; margin-left: 8px;"></i> 起点：仙桃市毛嘴镇消防站
            </div>
            <div style="display: flex; align-items: center; margin-top: 4px;">
                <i class="fa fa-map-marker fa-lg" style="color:red; margin-right: 16px; margin-left: 8px;"></i> 终点：市区道路-油罐车泄漏现场
            </div>
        </div>
    </div>
    '''

    m.get_root().html.add_child(folium.Element(ui_html))
    # 注入学术图例
    m.get_root().html.add_child(folium.Element(legend_html))
    
    # 🌟 修改点 3：把图层面板移到左下角，防止和右上角的图例重叠
    folium.LayerControl(position='bottomleft', collapsed=False).add_to(m)
    m.save(output_filename)
    print(f"地图已保存至: {output_filename}")

# ==================== 5. 主函数 ====================
if __name__ == '__main__':
    print("正在请求路网数据并规划无人车路径...")
    car_df, car_time = generate_car_path()
    print(f"无人车路径规划完成，预估耗时: {car_time/60:.1f} 分钟。")
    
    print("正在进行无人机三维避障规划与B样条平滑...")
    uav_df, raw_uav_df, delay = generate_uav_path(car_time)
    print(f"无人机规划完成。策略: {SYNC_STRATEGY}, 地面待机时间: {delay:.1f} 秒。")
    
    print("正在进行时空同步插值与交互式网页生成...")
    car_interp = interpolate_path(car_df, ANIMATION_INTERVAL)
    uav_interp = interpolate_path(uav_df, ANIMATION_INTERVAL)
    output_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "2d_deduction.html")
    create_visualization(car_df, uav_df, raw_uav_df, car_interp, uav_interp, delay, output_filename=output_path)
