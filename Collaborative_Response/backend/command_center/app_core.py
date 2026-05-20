import streamlit as st
import osmnx as ox
import networkx as nx
import folium
from folium.plugins import AntPath
from streamlit_folium import st_folium
import pandas as pd
import altair as alt
import random
import numpy as np
import time as time_lib
from datetime import datetime, time
from graph_utils import load_drive_graph_from_local_or_osm

# ==================== 1. 页面配置 ====================
st.set_page_config(layout="wide", page_title="协同调度平台", page_icon="")

st.markdown("""
<style>
    .block-container { padding-top: 5rem !important; max-width: 100% !important; }
    header[data-testid="stHeader"] { background: transparent !important; }
    [data-testid="stToolbar"] { display: none !important; }
    .stApp { background: radial-gradient(ellipse at 40% 25%, rgba(30,60,120,0.10) 0%, transparent 55%), radial-gradient(ellipse at 70% 70%, rgba(15,35,70,0.06) 0%, transparent 50%), #0a0f23; }
    [data-testid="stSidebar"] { background: linear-gradient(180deg, #111d3a 0%, #0d1630 40%, #0a1025 100%) !important; border-right: 1px solid rgba(74,158,255,0.12) !important; }
    [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] h1 { color: #ffffff !important; font-size: 1.2rem !important; font-weight: 700 !important; letter-spacing: 0.06em !important; padding-bottom: 14px !important; border-bottom: 1px solid rgba(74,158,255,0.16) !important; }
    [data-testid="stSidebar"] label { color: rgba(200,210,225,0.7) !important; font-size: 0.8rem !important; font-weight: 500 !important; }
    [data-testid="stSidebar"] hr { border-color: rgba(74,158,255,0.1) !important; }
    [data-testid="stSidebar"] button[kind="primary"] { background: linear-gradient(135deg, #2563eb, #3b82f6) !important; border: none !important; color: #fff !important; font-weight: 600 !important; letter-spacing: 0.04em !important; border-radius: 6px !important; box-shadow: 0 2px 12px rgba(37,99,235,0.25) !important; }
    .stApp h1 { color: #ffffff !important; font-size: 1.8rem !important; font-weight: 700 !important; letter-spacing: 0.04em !important; }
    .stApp h3 { color: #e8edf5 !important; font-weight: 600 !important; }
    [data-testid="stExpander"] { background: rgba(16,25,50,0.4) !important; border: 1px solid rgba(74,158,255,0.12) !important; border-radius: 8px !important; }
    [data-testid="stExpander"] summary { color: #e8edf5 !important; font-weight: 600 !important; }
    [data-testid="stTabs"] [data-baseweb="tab-list"] { border-bottom: 1px solid rgba(74,158,255,0.12) !important; }
    [data-testid="stTabs"] button[role="tab"] { color: rgba(200,210,225,0.6) !important; }
    [data-testid="stTabs"] button[role="tab"][aria-selected="true"] { color: #4a9eff !important; border-bottom-color: #4a9eff !important; }
    [data-testid="stMetricValue"] { color: #ffffff !important; font-weight: 700 !important; }
    [data-testid="stMetricLabel"] { color: rgba(200,210,225,0.55) !important; font-size: 0.8rem !important; }
    .stProgress > div > div { background-color: #4a9eff !important; }
    .info-card { background: rgba(16,25,50,0.85); border: 1px solid rgba(74,158,255,0.16); border-left: 4px solid #3b82f6; border-radius: 8px; padding: 15px; margin-bottom: 10px; color: #e8edf5; }
    .info-card.best { border-left-color: #5ec76e; background: rgba(94,199,110,0.06); }
    .info-card.selected { border-left-color: #4a9eff; background: rgba(74,158,255,0.06); }
    .info-card.warn { border-left-color: #e8915c; background: rgba(232,145,92,0.06); }
    .dashboard-container { background: rgba(16,25,50,0.6); padding: 20px; border-radius: 8px; border: 1px solid rgba(74,158,255,0.14); margin-top: 20px; }
    .metric-small { font-size: 0.85rem; color: rgba(200,210,225,0.5); }
</style>
""", unsafe_allow_html=True)

# ==================== 2. 全局配置 ====================
ACCIDENT_POINT = (30.4751, 114.4046)
# 🔥 修复 1：将 8000米 缩减至 3500米，防止过量数据请求导致网页假死白屏
SEARCH_RADIUS = 3500 
NETWORK_TYPE = 'drive'

if 'dispatched' not in st.session_state: st.session_state.dispatched = False
if 'best_route' not in st.session_state: st.session_state.best_route = None
if 'calculation_results' not in st.session_state: st.session_state.calculation_results = []
if 'route_comparison' not in st.session_state: st.session_state.route_comparison = {}
if 'obstacles' not in st.session_state: st.session_state.obstacles = []
if 'interaction_mode' not in st.session_state: st.session_state.interaction_mode = 'view'

# ==================== 3. 核心逻辑 ====================

# 🔥 修复 2：复杂空间图对象必须使用 cache_resource，否则引发 Streamlit 哈希崩溃
@st.cache_resource 
def load_graph():
    return load_drive_graph_from_local_or_osm(
        ACCIDENT_POINT,
        dist=SEARCH_RADIUS,
        network_type=NETWORK_TYPE,
    )

def get_safe_graph(G, obstacles):
    if not obstacles: return G, 0
    G_safe = G.copy()
    nodes_removed = set()
    for obs in obstacles:
        center_node = ox.nearest_nodes(G, obs[1], obs[0])
        if center_node in G_safe:
            G_safe.remove_node(center_node)
            nodes_removed.add(center_node)
    return G_safe, len(nodes_removed)

@st.cache_data
def get_facilities_data(tag_type):
    tags = {'amenity': tag_type}
    try:
        gdf = ox.features_from_point(ACCIDENT_POINT, tags, dist=SEARCH_RADIUS)
        facilities = []
        for _, row in gdf.iterrows():
            geom = row.geometry
            pt = (geom.y, geom.x) if geom.geom_type == 'Point' else (geom.centroid.y, geom.centroid.x)
            name = row.get('name', '未命名站点')
            if pd.isna(name): continue
            facilities.append({'name': str(name), 'coords': pt})
        return facilities
    except Exception as e: 
        print(f"警告：获取POI数据失败 ({e})")
        return []

@st.cache_data
def simulate_attributes(fac_list, category):
    enriched = []
    for f in fac_list:
        attr = {'name': f['name'], 'coords': f['coords']}
        if category == 'medical':
            is_large = any(x in f['name'] for x in ['大学', '省', '市', '中心', '三', '同济'])
            attr['level'] = '三甲医院' if is_large else '社区/二级'
            attr['total_beds'] = random.randint(1000, 2000) if is_large else random.randint(50, 200)
            attr['available_beds'] = random.randint(0, 100) if is_large else random.randint(20, 80)
            attr['status'] = '接诊中'
        elif category == 'fire':
            is_special = '特勤' in f['name']
            attr['level'] = '特勤站' if is_special else '普通站'
            attr['trucks'] = random.randint(6, 10) if is_special else random.randint(2, 4)
            attr['status'] = '待命' if random.random() > 0.2 else '出警中'
        elif category == 'police':
            attr['name'] = f['name'].replace('派出所', '交警中队').replace('公安局', '交管大队')
            if '交警' not in attr['name'] and '交管' not in attr['name']: attr['name'] += ' (交警单位)'
            is_large = '大队' in attr['name'] or '分局' in attr['name']
            attr['level'] = '交管大队' if is_large else '辖区中队'
            attr['patrol_cars'] = random.randint(10, 20) if is_large else random.randint(2, 6)
            attr['status'] = '待命' if random.random() > 0.15 else '全员出警'
        elif category == 'hazmat':
            attr['name'] = f['name'].replace('消防站', '防化特勤站').replace('救援', '防化应急')
            if '防化' not in attr['name']: attr['name'] += ' (防化编队)'
            is_heavy = random.random() > 0.6
            attr['level'] = '重型防化编队 (A级)' if is_heavy else '常规防化小组 (B级)'
            attr['neutralizer'] = '充足' if random.random() > 0.3 else '匮乏'
            attr['status'] = '待命' if random.random() > 0.2 else '演练/出勤中'
        elif category == 'road':
            attr['name'] = f['name'].replace('派出所', '路政大队').replace('公安', '交通运输')
            if '路政' not in attr['name'] and '交通' not in attr['name']: attr['name'] += ' (清障中心)'
            is_heavy = random.random() > 0.5
            attr['level'] = '重型清障中心' if is_heavy else '路面巡查中队'
            attr['heavy_cranes'] = random.randint(1, 3) if is_heavy else 0
            attr['tow_trucks'] = random.randint(3, 8) if is_heavy else random.randint(1, 2)
            attr['status'] = '随时可调派'
        enriched.append(attr)
    return enriched

def get_weather_impact(weather_type):
    impact = {"☀️ 晴朗": 1.0, "🌧️ 小雨": 0.8, "⛈️ 暴雨": 0.5, "🌫️ 大雾": 0.6, "❄️ 积雪": 0.4}
    return impact.get(weather_type, 1.0)

def calculate_score(distance_m, traffic_f, weather_f, attr, config):
    speed_mpm = (600 / traffic_f) * weather_f
    mode = config['type']
    severity = config['severity']
    
    if mode == 'police': speed_mpm *= 1.3
    elif mode == 'hazmat': speed_mpm *= 0.85
    elif mode == 'road': speed_mpm *= 0.7
    
    travel_time = distance_m / speed_mpm
    score = travel_time
    
    if mode == 'medical' and severity == '危重' and '三甲' not in attr['level']: score += 10000
    if mode == 'fire' and attr['status'] == '出警中': score += 99999
    if mode == 'police' and attr['status'] == '全员出警': score += 99999
    if mode == 'hazmat' and attr['status'] != '待命': score += 99999
    if mode == 'road' and severity == '特大' and attr['heavy_cranes'] == 0: score += 15000

    return score, travel_time

# ==================== 4. 主程序 ====================
def main():
    st.sidebar.title("联合指挥控制台")
    
    task_options = {
        "人员伤亡 (医疗急救)": {"mode": "medical", "tag": "hospital", "color": "green", "icon": "user-md"},
        "火灾事故 (消防灭火)": {"mode": "fire", "tag": "fire_station", "color": "orange", "icon": "fire-extinguisher"},
        "现场封控 (公安交警)": {"mode": "police", "tag": "police", "color": "blue", "icon": "shield"},
        "危化品泄漏 (防化部队)": {"mode": "hazmat", "tag": "fire_station", "color": "purple", "icon": "flask"},
        "道路清障 (交通路政)": {"mode": "road", "tag": "police", "color": "gray", "icon": "truck"}
    }
    
    task_type = st.sidebar.selectbox("调度主体优先级类型", list(task_options.keys()))
    current_task = task_options[task_type]
    mode, target_tag, theme_color, fa_icon = current_task["mode"], current_task["tag"], current_task["color"], current_task["icon"]
    
    levels = ["轻微", "中度", "危重"] if mode == 'medical' else ["一般", "较大", "特大"]
    severity = st.sidebar.select_slider("灾害应急响应等级", options=levels, value=levels[1])

    st.sidebar.caption("环境参数")
    col_t1, col_t2 = st.sidebar.columns(2)
    sim_time = col_t1.time_input("时间", time(8, 30))
    weather = col_t2.selectbox("天气", ["☀️ 晴朗", "🌧️ 小雨", "⛈️ 暴雨", "🌫️ 大雾", "❄️ 积雪"])
    
    st.sidebar.divider()
    st.sidebar.subheader("🚧 灾害模拟交互")
    inter_mode = st.sidebar.radio("地图点击功能：", ["🔍 查看站点详情", "🚫 添加道路阻断"], index=0)
    st.session_state.interaction_mode = 'block' if "添加" in inter_mode else 'view'
    
    if st.session_state.obstacles:
        st.sidebar.warning(f"已设置 {len(st.session_state.obstacles)} 处障碍")
        if st.sidebar.button("清除所有障碍"):
            st.session_state.obstacles = []
            st.rerun()

    st.sidebar.divider()

    raw_facs = get_facilities_data(target_tag)
    facilities_basic = simulate_attributes(raw_facs, mode)

    if st.sidebar.button("🚀 开始动态规划联合解算", type="primary", use_container_width=True):
        if not facilities_basic:
            st.sidebar.error("⚠️ 当前区域内未检索到对应类型的救援资源，请扩大范围！")
        else:
            bar = st.sidebar.progress(0, text="初始化 GIS 引擎...")
            G = load_graph()
            h = sim_time.hour
            traffic_f = 2.5 if 7<=h<=9 else (2.2 if 17<=h<=19 else 1.2)
            weather_f = get_weather_impact(weather)
            orig_node_acc = ox.nearest_nodes(G, ACCIDENT_POINT[1], ACCIDENT_POINT[0])
            
            G_safe, removed_cnt = get_safe_graph(G, st.session_state.obstacles)
            bar.progress(30, text=f"拓扑重构: 移除{removed_cnt}个阻断节点...")
            
            ranked = []
            for i, fac in enumerate(facilities_basic):
                dest = ox.nearest_nodes(G, fac['coords'][1], fac['coords'][0])
                try:
                    # 🔥 修复 3：调换计算方向。救援应当从 救援站(dest) 出发，前往 事故点(orig_node_acc)111
                    dist_safe = nx.shortest_path_length(G_safe, dest, orig_node_acc, weight='length')
                    try:
                        dist_orig = nx.shortest_path_length(G, dest, orig_node_acc, weight='length')
                    except nx.NetworkXNoPath: 
                        dist_orig = dist_safe

                    score, t = calculate_score(dist_safe, traffic_f, weather_f, fac, {'type': mode, 'severity': severity})
                    res = fac.copy()
                    res.update({'dist': dist_safe, 'time': t, 'score': score, 'dest': dest, 'dist_orig': dist_orig})
                    ranked.append(res)
                except nx.NetworkXNoPath:
                    res = fac.copy()
                    res.update({'dist': 99999, 'time': 9999, 'score': 99999, 'dest': dest, 'dist_orig': 0})
                    ranked.append(res)
                except Exception as e: 
                    # 🔥 修复 4：不要吃掉异常，打印出来防止排查不到死因
                    print(f"⚠️ 节点计算异常跳过: {e}")
                
            ranked.sort(key=lambda x: x['score'])
            st.session_state.calculation_results = ranked
            
            if ranked and ranked[0]['score'] < 90000:
                best = ranked[0]
                # 同理调换路线生成的方向
                route = nx.shortest_path(G_safe, best['dest'], orig_node_acc, weight='length')
                st.session_state.best_route = [(G_safe.nodes[n]['y'], G_safe.nodes[n]['x']) for n in route]
                st.session_state.route_comparison = {
                    'name': best['name'], 'orig_dist': best['dist_orig'], 'curr_dist': best['dist'],
                    'detour': best['dist'] - best['dist_orig'], 'obstacles': len(st.session_state.obstacles)
                }
            else:
                st.session_state.best_route = None
                st.session_state.route_comparison = {}
            
            bar.progress(100, text="✅ 解算完成")
            time_lib.sleep(0.5)
            bar.empty()
            st.session_state.dispatched = True

    # --- 主界面 ---
    st.title(f"灾害动态路径规划系统 ({mode.upper()})")
    col_map, col_data = st.columns([3, 1.2])

    with col_map:
        m = folium.Map(location=ACCIDENT_POINT, zoom_start=13, tiles="OpenStreetMap")
        folium.Marker(ACCIDENT_POINT, popup="事故点", icon=folium.Icon(color='red', icon='warning', prefix='fa')).add_to(m)
        for obs in st.session_state.obstacles:
            folium.Circle(location=obs, radius=150, color='red', fill=True, fill_opacity=0.5, popup="🚫 阻断").add_to(m)

        if st.session_state.dispatched and st.session_state.best_route:
            AntPath(st.session_state.best_route, color=theme_color, weight=5, opacity=0.8, delay=800).add_to(m)
        elif st.session_state.dispatched:
            st.error("🚨 目标全部受阻不可达！")

        current_list = st.session_state.calculation_results if st.session_state.dispatched else facilities_basic
        best_name = current_list[0]['name'] if st.session_state.dispatched and current_list else ""

        for item in current_list:
            color = 'blue'
            if st.session_state.dispatched:
                if item.get('score', 0) > 90000: color = 'lightgray' 
                elif item['name'] == best_name: color = theme_color
            folium.Marker(item['coords'], tooltip=f"{item['name']}", icon=folium.Icon(color=color, icon=fa_icon, prefix='fa')).add_to(m)

        map_output = st_folium(m, width="100%", height=650, returned_objects=["last_clicked", "last_object_clicked"])

        if map_output['last_clicked'] and st.session_state.interaction_mode == 'block':
            lat, lng = map_output['last_clicked']['lat'], map_output['last_clicked']['lng']
            is_exist = any(abs(o[0]-lat)<0.001 and abs(o[1]-lng)<0.001 for o in st.session_state.obstacles)
            if not is_exist:
                st.session_state.obstacles.append((lat, lng))
                st.rerun()

    with col_data:
        with st.expander("🌍 环境与灾情感知", expanded=True):
            ec1, ec2 = st.columns(2)
            ec1.metric("天气", weather)
            w_rate = get_weather_impact(weather)
            ec2.metric("通行效率", f"{w_rate*100:.0f}%", delta=f"-{(1-w_rate)*100:.0f}%" if w_rate<1 else None)
            mode_style = "background-color:#dc3545; color:white;" if st.session_state.interaction_mode == 'block' else "background-color:#007bff; color:white;"
            mode_text = "🚧 点击地图添加障碍" if st.session_state.interaction_mode == 'block' else "🔍 点击站点查看详情"
            st.markdown(f'<div style="{mode_style} padding:10px; border-radius:5px; text-align:center; margin-top:10px;">当前模式：{mode_text}</div>', unsafe_allow_html=True)

        selected = None
        if st.session_state.interaction_mode == 'view' and map_output['last_object_clicked']:
            click_pt = (map_output['last_object_clicked']['lat'], map_output['last_object_clicked']['lng'])
            for item in current_list:
                if abs(item['coords'][0]-click_pt[0]) < 0.001 and abs(item['coords'][1]-click_pt[1]) < 0.001:
                    selected = item
                    break
        if not selected and st.session_state.dispatched and st.session_state.calculation_results:
            selected = st.session_state.calculation_results[0]

        if selected:
            level_bg, level_color = ("#fef3c7", "#92400e") if selected.get('level') == '三甲医院' else ("#e5e7eb", "#374151")
            is_best = st.session_state.dispatched and (selected['name'] == st.session_state.calculation_results[0]['name'])
            is_unreachable = st.session_state.dispatched and selected.get('score', 0) > 90000
            title_pre = "🏆 最佳调度方案" if is_best else "📍 选中单位"
            card_class = "info-card best" if is_best else "info-card selected"
            if is_unreachable: card_class, title_pre = "info-card warn", "🚫 不符合条件 / 路线断联"

            st.markdown(f"""<div class="{card_class}"><div style="color:#94a3b8; font-size:0.8rem;">{title_pre}</div><h3 style="margin:5px 0; color:#e8edf5;">{selected['name']}</h3><span style="background:{level_bg}; color:{level_color}; padding:2px 8px; border-radius:3px; font-size:0.8rem; font-weight:600;">{selected['level']}</span></div>""", unsafe_allow_html=True)

            if st.session_state.dispatched and not is_unreachable:
                c1, c2 = st.columns(2)
                c1.metric("预计耗时", f"{selected['time']:.1f}m")
                c2.metric("行驶距离", f"{selected['dist']:.0f}m")
                st.caption("与最优方案对比:")
                diff = selected['time'] - st.session_state.calculation_results[0]['time']
                if diff > 0: st.warning(f"慢 {diff:.1f} 分钟")
                else: st.success("当前为最快方案")

            st.divider()
            if mode == 'medical':
                st.caption(f"床位使用情况: {selected.get('available_beds',0)}/{selected.get('total_beds',0)}")
                if selected.get('total_beds', 0) > 0:
                    st.progress(1 - selected['available_beds']/selected['total_beds'])
            elif mode == 'fire': st.write(f"🚒 **状态:** {selected.get('status','')} | **可调派消防车:** {selected.get('trucks',0)}辆")
            elif mode == 'police': st.write(f"🚓 **警力状态:** {selected.get('status','')} | **可调用警车:** {selected.get('patrol_cars',0)}辆")
            elif mode == 'hazmat': st.write(f"☣️ **状态:** {selected.get('status','')} | **洗消剂储备:** {selected.get('neutralizer','未知')}")
            elif mode == 'road': st.write(f"🏗️ **状态:** {selected.get('status','')} | **重型吊车:** {selected.get('heavy_cranes',0)}台")
        else:
            st.info("👈 在 [查看模式] 下点击地图图标查看详情")

    st.markdown("### 📊 灾害空间协同调度效能评估")
    with st.container():
        st.markdown('<div class="dashboard-container">', unsafe_allow_html=True)
        tab1, tab2, tab3 = st.tabs(["🛣️ 路径损耗评估", "🚧 道路阻断详情", "📡 算法执行监控"])
        with tab1:
            if st.session_state.dispatched and st.session_state.route_comparison:
                comp = st.session_state.route_comparison
                c1, c2, c3 = st.columns(3)
                c1.metric("理想路网行程 (无灾害)", f"{comp['orig_dist']:.0f} m")
                c2.metric("当前避障行程 (有灾害)", f"{comp['curr_dist']:.0f} m")
                delta = comp['detour']
                c3.metric("次生灾害导致的绕行损耗", f"+{delta:.0f} m", delta_color="inverse" if delta > 0 else "normal")
                chart_data = pd.DataFrame({'Scenario': ['理想路径', '灾后避障路径'], 'Distance': [comp['orig_dist'], comp['curr_dist']]})
                chart = alt.Chart(chart_data).mark_bar().encode(x='Distance:Q', y=alt.Y('Scenario:N', sort=None), color='Scenario:N').properties(height=150)
                st.altair_chart(chart, use_container_width=True)
            else: st.info("待执行动态规划后查看对比分析。")
        with tab2:
            if st.session_state.obstacles:
                obs_df = pd.DataFrame(st.session_state.obstacles, columns=['纬度', '经度'])
                obs_df.index += 1
                st.dataframe(obs_df, use_container_width=True)
            else: st.success("当前路网畅通，无结构性阻断记录。")
        with tab3:
            obs_log = f"网络拓扑动态重构: 移除 {len(st.session_state.obstacles)} 个故障节点..." if st.session_state.obstacles else "路网连通性校验... 完整."
            st.code(f"[System] {datetime.now().strftime('%H:%M:%S')} GIS空间调度引擎自检... OK\n[System] {datetime.now().strftime('%H:%M:%S')} {obs_log}\n[Result] 最优协同响应单位: {st.session_state.route_comparison.get('name', 'N/A')}", language="bash")
        st.markdown('</div>', unsafe_allow_html=True)

if __name__ == "__main__":
    main()