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
st.set_page_config(layout="wide", page_title="交通事故动态路径规划系统 (五大多主体)", page_icon="🚧")

st.markdown("""
<style>
    /* 将 padding-top 增加到 5rem，确保标题完全显示 */
    .block-container {
        padding-top: 5rem !important;
        max-width: 100% !important;
    }
    
    /* 使得左右列高度自动拉伸对齐，并且让地图 iframe 高度 100% 填满左侧，杜绝任何白边或断层 */
    div[data-testid="stHorizontalBlock"] {
        align-items: stretch !important;
    }
    div[data-testid="column"] {
        display: flex !important;
        flex-direction: column !important;
    }
    div[data-testid="column"] > div {
        flex-grow: 1 !important;
        display: flex !important;
        flex-direction: column !important;
    }
    div[data-testid="column"] iframe {
        flex-grow: 1 !important;
        height: 100% !important;
        min-height: 520px !important;
    }
    
    /* 强制全局暗色背景与CSS变量设置 */
    html, body, .stApp, [data-testid="stAppViewContainer"], [data-testid="stMain"], [data-testid="stHeader"], [data-testid="stBlockContainer"] {
        --primary-color: #00f2fe !important;
        --background-color: #020813 !important;
        --secondary-background-color: rgba(10, 19, 35, 0.82) !important;
        --text-color: #cbd5e1 !important;
        background-color: #020813 !important;
        color: #cbd5e1 !important;
    }
    
    /* 侧边栏样式，完美复刻左侧系统侧边栏样式 */
    section[data-testid="stSidebar"] {
        width: 260px !important;
        min-width: 260px !important;
        background-color: rgba(10, 19, 35, 0.82) !important;
        backdrop-filter: blur(20px) saturate(140%) !important;
        -webkit-backdrop-filter: blur(20px) saturate(140%) !important;
        border-right: 1px solid rgba(0, 242, 254, 0.22) !important;
        box-shadow: 0 0 30px rgba(0, 0, 0, 0.7), inset 0 0 20px rgba(0, 242, 254, 0.05) !important;
    }
    section[data-testid="stSidebar"] .stMarkdown, 
    section[data-testid="stSidebar"] .stRadio, 
    section[data-testid="stSidebar"] label,
    section[data-testid="stSidebar"] p,
    section[data-testid="stSidebar"] span {
        color: #cbd5e1 !important;
    }

    /* 卡片采用纯深色固体背景，保障字样高度清晰 */
    .info-card {
        background-color: #0a1220 !important;
        border: 1px solid rgba(0, 242, 254, 0.18) !important;
        border-left: 6px solid #6c757d !important;
        border-radius: 8px;
        padding: 15px;
        margin-bottom: 10px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.4);
        color: #cbd5e1 !important;
    }
    .info-card h3 {
        color: #ffffff !important;
        margin: 5px 0 !important;
    }
    .info-card.best { 
        border-left-color: #00f2fe !important; 
        background-color: #0b1c31 !important; 
        box-shadow: 0 0 15px rgba(0, 242, 254, 0.15) !important;
    }
    .info-card.selected { 
        border-left-color: #2563eb !important; 
        background-color: #0e1d3e !important; 
    }
    .info-card.warn { 
        border-left-color: #ef4444 !important; 
        background-color: #21121c !important; 
    }

    /* 直接对 Tabs 进行样式定义，杜绝假 div 产生多余留白 */
    .stTabs {
        background-color: rgba(2, 12, 26, 0.6) !important;
        padding: 20px;
        border-radius: 8px;
        border: 1px solid rgba(0, 242, 254, 0.15) !important;
        box-shadow: inset 0 0 10px rgba(0, 242, 254, 0.05) !important;
        margin-top: 15px;
        color: #cbd5e1 !important;
    }
    
    .metric-small { 
        font-size: 0.9rem; 
        color: #94a3b8; 
    }

    /* 折叠面板 (Expander) 新版及老版样式覆盖 */
    [data-testid="stExpander"] {
        background-color: rgba(10, 25, 47, 0.3) !important;
        border: 1px solid rgba(0, 242, 254, 0.15) !important;
        border-radius: 8px !important;
        box-shadow: 0 4px 12px rgba(0,0,0,0.3) !important;
    }
    /* 彻底清除按钮在 hover/focus 下变白的问题，引入科技蓝悬停光晕 */
    [data-testid="stExpander"] button,
    [data-testid="stExpander"] [data-testid="stExpanderToggleHeader"] button {
        background: transparent !important;
        background-color: transparent !important;
        color: #ffffff !important;
        border: none !important;
        box-shadow: none !important;
        outline: none !important;
    }
    [data-testid="stExpander"] button:hover,
    [data-testid="stExpander"] button:focus,
    [data-testid="stExpander"] button:active,
    [data-testid="stExpander"] [data-testid="stExpanderToggleHeader"] button:hover,
    [data-testid="stExpander"] [data-testid="stExpanderToggleHeader"] button:focus {
        background: rgba(0, 242, 254, 0.08) !important;
        background-color: rgba(0, 242, 254, 0.08) !important;
        color: #00f2fe !important;
        box-shadow: none !important;
    }
    [data-testid="stExpander"] div,
    [data-testid="stExpander"] p,
    [data-testid="stExpander"] span {
        background-color: transparent !important;
    }
    .streamlit-expanderHeader, [data-testid="stExpanderToggleHeader"] {
        background-color: rgba(10, 25, 47, 0.5) !important;
        border-bottom: 1px solid rgba(0, 242, 254, 0.15) !important;
        color: #ffffff !important;
    }
    .streamlit-expanderHeader p, 
    .streamlit-expanderHeader span, 
    [data-testid="stExpanderToggleHeader"] p, 
    [data-testid="stExpanderToggleHeader"] span {
        color: #ffffff !important;
        font-weight: 700 !important;
    }
    .streamlit-expanderContent, [data-testid="stExpanderDetails"], [data-testid="stExpanderDetails"] > div {
        background-color: rgba(2, 12, 26, 0.5) !important;
        border: none !important;
        color: #cbd5e1 !important;
    }

    /* 指标 (Metrics) 样式增强 */
    [data-testid="stMetricLabel"], 
    [data-testid="stMetricLabel"] > div,
    .stMetric label {
        color: #94a3b8 !important;
        font-size: 0.9rem !important;
        font-weight: 600 !important;
    }
    [data-testid="stMetricValue"], 
    [data-testid="stMetricValue"] > div,
    .stMetric [data-testid="stMetricValue"] {
        color: #ffffff !important;
        font-weight: 700 !important;
        font-size: 1.6rem !important;
    }

    /* 辅助说明字样 (Caption) */
    .stCaption, 
    [data-testid="stCaptionContainer"], 
    .stCaption p {
        color: #94a3b8 !important;
        font-size: 0.85rem !important;
    }

    /* 选项卡 (Tabs) */
    .stTabs [data-baseweb="tab-list"] {
        background-color: transparent !important;
        border-bottom: 1px solid rgba(0, 242, 254, 0.15) !important;
    }
    .stTabs [data-baseweb="tab"] {
        color: #94a3b8 !important;
        font-weight: 600 !important;
    }
    .stTabs [aria-selected="true"] {
        color: #00f2fe !important;
        border-bottom-color: #00f2fe !important;
    }

    /* 按钮定制 */
    .stButton>button {
        background: linear-gradient(135deg, rgba(0, 229, 255, 0.15) 0%, rgba(37, 99, 235, 0.15) 100%) !important;
        border: 1px solid rgba(0, 242, 254, 0.4) !important;
        color: #00f2fe !important;
        border-radius: 8px !important;
        font-weight: bold !important;
        transition: all 0.3s !important;
        min-height: 38px !important;
    }
    .stButton>button:hover {
        background: linear-gradient(135deg, rgba(0, 242, 254, 0.28) 0%, rgba(37, 99, 235, 0.28) 100%) !important;
        border-color: #00f2fe !important;
        color: #ffffff !important;
        box-shadow: 0 0 15px rgba(0, 242, 254, 0.4) !important;
    }
    .stButton>button[kind="primary"] {
        background: linear-gradient(135deg, rgba(0, 229, 255, 0.3) 0%, rgba(37, 99, 235, 0.3) 100%) !important;
        border: 1px solid #00f2fe !important;
        color: #ffffff !important;
        box-shadow: 0 0 10px rgba(0, 242, 254, 0.2) !important;
    }
    .stButton>button[kind="primary"]:hover {
        background: linear-gradient(135deg, rgba(0, 242, 254, 0.45) 0%, rgba(37, 99, 235, 0.45) 100%) !important;
        box-shadow: 0 0 18px rgba(0, 242, 254, 0.5) !important;
    }

    /* 下拉选择框和输入框 */
    div[data-baseweb="select"] {
        background-color: rgba(18, 30, 49, 0.8) !important;
        border: 1px solid rgba(0, 242, 254, 0.3) !important;
        border-radius: 6px !important;
    }
    div[data-baseweb="select"] div {
        color: #ffffff !important;
    }
    input {
        background-color: rgba(18, 30, 49, 0.8) !important;
        color: #ffffff !important;
        border: 1px solid rgba(0, 242, 254, 0.3) !important;
    }
    div[data-baseweb="input"] {
        background-color: rgba(18, 30, 49, 0.8) !important;
        border: 1px solid rgba(0, 242, 254, 0.3) !important;
        border-radius: 6px !important;
    }
</style>
""", unsafe_allow_html=True)

# ==================== 2. 全局配置 ====================
ACCIDENT_POINT = (30.4751, 114.4046)
SEARCH_RADIUS = 8000
NETWORK_TYPE = 'drive'

# 初始化 Session State
if 'dispatched' not in st.session_state: st.session_state.dispatched = False
if 'best_route' not in st.session_state: st.session_state.best_route = None
if 'calculation_results' not in st.session_state: st.session_state.calculation_results = []
if 'route_comparison' not in st.session_state: st.session_state.route_comparison = {}
if 'obstacles' not in st.session_state: st.session_state.obstacles = []
if 'interaction_mode' not in st.session_state: st.session_state.interaction_mode = 'view'

# ==================== 3. 核心逻辑 ====================

@st.cache_data
def load_graph():
    return load_drive_graph_from_local_or_osm(
        ACCIDENT_POINT,
        dist=SEARCH_RADIUS,
        network_type=NETWORK_TYPE,
    )

def get_safe_graph(G, obstacles):
    if not obstacles:
        return G, 0
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
            pt = (row.geometry.y, row.geometry.x) if row.geometry.geom_type == 'Point' else (row.geometry.centroid.y, row.geometry.centroid.x)
            name = row.get('name', '未命名站点')
            if pd.isna(name): continue
            facilities.append({'name': name, 'coords': pt})
        return facilities
    except: return []

@st.cache_data
def simulate_attributes(fac_list, category):
    enriched = []
    for f in fac_list:
        attr = {'name': f['name'], 'coords': f['coords']}
        
        # 1. 医疗急救
        if category == 'medical':
            is_large = any(x in f['name'] for x in ['大学', '省', '市', '中心', '三', '同济'])
            attr['level'] = '三甲医院' if is_large else '社区/二级'
            attr['level_score'] = 10 if is_large else 5
            attr['total_beds'] = random.randint(1000, 2000) if is_large else random.randint(50, 200)
            attr['available_beds'] = random.randint(0, 100) if is_large else random.randint(20, 80)
            attr['status'] = '接诊中'
            
        # 2. 消防灭火
        elif category == 'fire':
            is_special = '特勤' in f['name']
            attr['level'] = '特勤站' if is_special else '普通站'
            attr['level_score'] = 10 if is_special else 6
            attr['personnel'] = random.randint(40, 60) if is_special else random.randint(12, 20)
            attr['trucks'] = random.randint(6, 10) if is_special else random.randint(2, 4)
            attr['chem_capable'] = True if is_special else False
            attr['status'] = '待命' if random.random() > 0.2 else '出警中'
            
        # 3. 公安交警 (基于警察局数据模拟)
        elif category == 'police':
            attr['name'] = f['name'].replace('派出所', '交警中队').replace('公安局', '交管大队')
            if '交警' not in attr['name'] and '交管' not in attr['name']: attr['name'] += ' (交警单位)'
            is_large = '大队' in attr['name'] or '分局' in attr['name']
            attr['level'] = '交管大队' if is_large else '辖区中队'
            attr['patrol_cars'] = random.randint(10, 20) if is_large else random.randint(2, 6)
            attr['status'] = '待命' if random.random() > 0.15 else '全员出警'
            
        # 4. 防化部队 (基于消防数据模拟特勤防化)
        elif category == 'hazmat':
            attr['name'] = f['name'].replace('消防站', '防化特勤站').replace('救援', '防化应急')
            if '防化' not in attr['name']: attr['name'] += ' (防化编队)'
            is_heavy = random.random() > 0.6
            attr['level'] = '重型防化编队 (A级)' if is_heavy else '常规防化小组 (B级)'
            attr['neutralizer'] = '充足' if random.random() > 0.3 else '匮乏'
            attr['status'] = '待命' if random.random() > 0.2 else '演练/出勤中'
            
        # 5. 交通路政 (基于警察局/政府驻地模拟)
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
    
    # 模拟不同车型的运动学差异 (警车快，重型机械慢)
    if mode == 'police': speed_mpm *= 1.3
    elif mode == 'hazmat': speed_mpm *= 0.85
    elif mode == 'road': speed_mpm *= 0.7
    
    travel_time = distance_m / speed_mpm
    score = travel_time
    
    # 业务逻辑硬约束惩罚
    if mode == 'medical':
        if severity == '危重' and '三甲' not in attr['level']: score += 10000
        if attr['available_beds'] < 3: score += 1000
    elif mode == 'fire':
        if attr['status'] == '出警中': score += 99999
    elif mode == 'police':
        if attr['status'] == '全员出警': score += 99999
        if severity == '特大' and attr['patrol_cars'] < 5: score += 5000
    elif mode == 'hazmat':
        if attr['status'] != '待命': score += 99999
        if severity == '特大' and '常规' in attr['level']: score += 8000
        if attr['neutralizer'] == '匮乏': score += 20000
    elif mode == 'road':
        if severity == '特大' and attr['heavy_cranes'] == 0: score += 15000

    return score, travel_time

# ==================== 4. 主程序 ====================

def main():
    qp = st.query_params
    _is_embed = qp.get("embed", "") == "true" or qp.get("sidebar", "") == "minimal"
    ext_mode = qp.get("mode", "")
    ext_severity = qp.get("severity", "")
    ext_weather = qp.get("weather", "")
    ext_time = qp.get("time", "")
    ext_interact = qp.get("interact_mode", "view")
    ext_action = qp.get("action", "")

    if _is_embed:
        st.markdown("""
        <style>
        [data-testid="stSidebar"] { display: none !important; }
        [data-testid="collapsedControl"] { display: none !important; }
        header[data-testid="stHeader"] { display: none !important; }
        footer { display: none !important; }
        .block-container { padding-top: 0.5rem !important; padding-bottom: 0.5rem !important; padding-left: 1rem !important; padding-right: 1rem !important; }
        </style>
        """, unsafe_allow_html=True)
    else:
        st.sidebar.title("🛠️ 联合指挥应急控制台")

    # 1. 任务设置 (扩展为5个模块)
    task_options = {
        "人员伤亡 (医疗急救)": {"mode": "medical", "tag": "hospital", "color": "green", "icon": "user-md"},
        "火灾事故 (消防灭火)": {"mode": "fire", "tag": "fire_station", "color": "orange", "icon": "fire-extinguisher"},
        "现场封控 (公安交警)": {"mode": "police", "tag": "police", "color": "blue", "icon": "shield"},
        "危化品泄漏 (防化部队)": {"mode": "hazmat", "tag": "fire_station", "color": "purple", "icon": "flask"},
        "道路清障 (交通路政)": {"mode": "road", "tag": "police", "color": "gray", "icon": "truck"}
    }
    _mode_to_label = {v["mode"]: k for k, v in task_options.items()}
    _default_task = _mode_to_label.get(ext_mode, list(task_options.keys())[0])
    if not _is_embed:
        task_type = st.sidebar.selectbox("调度主体优先级类型", list(task_options.keys()),
                                          index=list(task_options.keys()).index(_default_task))
    else:
        task_type = _default_task
    current_task = task_options[task_type]
    mode = current_task["mode"]
    target_tag = current_task["tag"]
    theme_color = current_task["color"]
    fa_icon = current_task["icon"]

    levels = ["轻微", "中度", "危重"] if mode == 'medical' else ["一般", "较大", "特大"]
    _default_sev = ext_severity if ext_severity in levels else levels[1]
    if not _is_embed:
        severity = st.sidebar.select_slider("交通事故应急响应等级", options=levels, value=_default_sev)
    else:
        severity = _default_sev

    # 2. 环境仿真
    _dh, _dm = 8, 30
    if ext_time and ":" in ext_time:
        try: _dh, _dm = int(ext_time.split(":")[0]), int(ext_time.split(":")[1])
        except: pass
    weather_options = ["☀️ 晴朗", "🌧️ 小雨", "⛈️ 暴雨", "🌫️ 大雾", "❄️ 积雪"]
    _default_w = ext_weather if ext_weather in weather_options else weather_options[0]
    if not _is_embed:
        st.sidebar.caption("环境参数")
        col_t1, col_t2 = st.sidebar.columns(2)
        sim_time = col_t1.time_input("时间", time(_dh, _dm))
        weather = col_t2.selectbox("天气", weather_options, index=weather_options.index(_default_w))
    else:
        sim_time = time(_dh, _dm)
        weather = _default_w
    
    # 3. 互动模式
    if not _is_embed:
        st.sidebar.markdown("""
        <div style="background:rgba(0, 242, 254, 0.06);border:1px solid rgba(0, 242, 254, 0.3);border-left:4px solid #00f2fe;border-radius:6px;padding:10px 14px;margin-bottom:4px;box-shadow:0 0 12px rgba(0, 242, 254, 0.1);">
            <span style="font-size:16px;font-weight:700;color:#00f2fe;text-shadow:0 0 8px rgba(0, 242, 254, 0.3);">&#x1F3AE; 交互控制台</span>
        </div>
        """, unsafe_allow_html=True)
        inter_mode = st.sidebar.radio("地图点击功能", ["&#x1F50D; 查看站点详情", "&#x1F6AB; 添加道路阻断"], index=0, key="interact_radio")
        st.session_state.interaction_mode = 'block' if "添加" in inter_mode else 'view'
    else:
        st.session_state.interaction_mode = 'block' if ("block" in ext_interact or "阻断" in ext_interact) else 'view'

    # 预加载
    raw_facs = get_facilities_data(target_tag)
    facilities_basic = simulate_attributes(raw_facs, mode)

    # 状态摘要
    w_rate = get_weather_impact(weather)
    h = sim_time.hour
    traffic_f = 2.5 if 7<=h<=9 else (2.2 if 17<=h<=19 else 1.2)
    tf_color = "#ef4444" if traffic_f >= 2.0 else "#f59e0b" if traffic_f >= 1.5 else "#10b981"
    if not _is_embed:
        st.sidebar.markdown(f"""
        <div style="background:rgba(2,12,26,0.6);border:1px solid rgba(0,242,254,0.15);border-radius:8px;padding:12px 14px;margin:10px 0;box-shadow:inset 0 0 10px rgba(0,242,254,0.05);">
            <div style="font-size:13px;font-weight:700;color:#00f2fe;margin-bottom:8px;display:flex;align-items:center;gap:6px;">
                <span style="display:inline-block;width:4px;height:16px;background:#00f2fe;border-radius:2px;"></span>&#x1F4CB; 调度参数
            </div>
            <table style="width:100%;font-size:13px;line-height:2.2;color:#cbd5e1;border-collapse:collapse;">
            <tr><td style="color:#94a3b8;width:68px;padding:2px 0;">调度主体</td><td style="font-weight:600;color:#ffffff;">{current_task['mode']}</td></tr>
            <tr><td style="color:#94a3b8;padding:2px 0;">响应等级</td><td style="font-weight:600;color:#ffffff;">{severity}</td></tr>
            <tr><td style="color:#94a3b8;padding:2px 0;">天气状况</td><td>{weather}&ensp;<span style="color:#00f2fe;font-weight:500;">通行 {w_rate*100:.0f}%</span></td></tr>
            <tr><td style="color:#94a3b8;padding:2px 0;">模拟时间</td><td>{sim_time.strftime('%H:%M')}&ensp;<span style="color:{tf_color};font-weight:500;">系数 {traffic_f:.1f}</span></td></tr>
            <tr><td style="color:#94a3b8;padding:2px 0;">可用站点</td><td style="font-weight:600;color:#ffffff;">{len(facilities_basic)} 个</td></tr>
            </table>
        </div>
        """, unsafe_allow_html=True)

    # 4. 规划按钮/自动解算触发
    should_run = False
    if not _is_embed:
        if st.sidebar.button("🚀 开始动态规划联合解算", type="primary", use_container_width=True):
            should_run = True
    else:
        if ext_action == "run" or qp.get("auto_run", "") == "1":
            should_run = True

    if should_run:
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
                dist_safe = nx.shortest_path_length(G_safe, orig_node_acc, dest, weight='length')
                try:
                    dist_orig = nx.shortest_path_length(G, orig_node_acc, dest, weight='length')
                except: dist_orig = dist_safe

                score, t = calculate_score(dist_safe, traffic_f, weather_f, fac, {'type': mode, 'severity': severity})
                
                res = fac.copy()
                res.update({
                    'dist': dist_safe,
                    'time': t,
                    'score': score,
                    'dest': dest,
                    'dist_orig': dist_orig
                })
                ranked.append(res)
            except nx.NetworkXNoPath:
                res = fac.copy()
                res.update({'dist': 99999, 'time': 9999, 'score': 99999, 'dest': None, 'dist_orig': 0})
                ranked.append(res)
            except: pass
            
        ranked.sort(key=lambda x: x['score'])
        st.session_state.calculation_results = ranked
        
        if ranked and ranked[0]['dest']:
            best = ranked[0]
            route = nx.shortest_path(G_safe, orig_node_acc, best['dest'], weight='length')
            st.session_state.best_route = [(G_safe.nodes[n]['y'], G_safe.nodes[n]['x']) for n in route]
            
            st.session_state.route_comparison = {
                'name': best['name'],
                'orig_dist': best['dist_orig'],
                'curr_dist': best['dist'],
                'detour': best['dist'] - best['dist_orig'],
                'obstacles': len(st.session_state.obstacles)
            }
        else:
            st.session_state.best_route = None
            st.session_state.route_comparison = {}
        
        bar.progress(100, text="✅ 解算完成")
        time_lib.sleep(0.5)
        bar.empty()
        st.session_state.dispatched = True

    # --- 主界面 ---
    st.title(f"🚑 交通事故动态路径规划系统 ({mode.upper()})")
    col_map, col_data = st.columns([3, 1.2])

    with col_map:
        m = folium.Map(location=ACCIDENT_POINT, zoom_start=13, tiles="OpenStreetMap")
        
        folium.Marker(ACCIDENT_POINT, popup="事故点", icon=folium.Icon(color='red', icon='warning', prefix='fa')).add_to(m)

        for obs in st.session_state.obstacles:
            folium.Circle(location=obs, radius=150, color='red', fill=True, fill_opacity=0.5, popup="🚫 阻断").add_to(m)

        if st.session_state.dispatched and st.session_state.best_route:
            AntPath(st.session_state.best_route, color=theme_color, weight=5, opacity=0.8, delay=800).add_to(m)
        elif st.session_state.dispatched:
            st.error("🚨 目标不可达！")

        current_list = st.session_state.calculation_results if st.session_state.dispatched else facilities_basic
        best_name = current_list[0]['name'] if st.session_state.dispatched and current_list else ""

        for item in current_list:
            color = 'blue'
            if st.session_state.dispatched:
                if item.get('score', 0) > 9000: color = 'lightgray' # 惩罚分数过高，颜色变灰
                elif item['name'] == best_name: color = theme_color
            folium.Marker(item['coords'], tooltip=f"{item['name']}", icon=folium.Icon(color=color, icon=fa_icon, prefix='fa')).add_to(m)

        map_output = st_folium(m, width="100%", height=450, returned_objects=["last_clicked", "last_object_clicked"])

        if map_output['last_clicked'] and st.session_state.interaction_mode == 'block':
            lat, lng = map_output['last_clicked']['lat'], map_output['last_clicked']['lng']
            is_exist = any(abs(o[0]-lat)<0.001 and abs(o[1]-lng)<0.001 for o in st.session_state.obstacles)
            if not is_exist:
                st.session_state.obstacles.append((lat, lng))
                st.rerun()

    # === 🔥 底部重构：交通事故救援路径效能评估系统 ===
        st.markdown("### 📊 交通事故空间协同调度效能评估")
        with st.container():
            tab1, tab2, tab3 = st.tabs(["🛣️ 路径损耗评估", "🚧 道路阻断详情", "📡 算法执行监控"])

            # Tab 1: 路径损耗 (核心：对比灾害前后的距离)
            with tab1:
                if st.session_state.dispatched and st.session_state.route_comparison:
                    comp = st.session_state.route_comparison
                    c1, c2, c3 = st.columns(3)
                    c1.metric("理想路网行程 (无灾害)", f"{comp['orig_dist']:.0f} m")
                    c2.metric("当前避障行程 (有灾害)", f"{comp['curr_dist']:.0f} m")

                    delta = comp['detour']
                    delta_color = "inverse" if delta > 0 else "normal"
                    c3.metric("次生事故导致的绕行损耗", f"+{delta:.0f} m", delta_color=delta_color)

                    # 损耗图表
                    chart_data = pd.DataFrame({
                        'Scenario': ['理想路径', '灾后避障路径'],
                        'Distance': [comp['orig_dist'], comp['curr_dist']]
                    })
                    chart = alt.Chart(chart_data).mark_bar().encode(
                        x='Distance:Q', y=alt.Y('Scenario:N', sort=None), color='Scenario:N'
                    ).properties(height=150)
                    st.altair_chart(chart, use_container_width=True)

                    if delta > 0: st.warning(f"⚠️ 受 {comp['obstacles']} 处障碍物影响，目标单位 {comp['name']} 被迫绕行，时效性受到影响。")
                    else: st.success("✅ 当前目标单位规划路径未受阻断影响，保持最佳通行效率。")
                else:
                    st.info("💡 系统已就绪，请在左侧【交互控制台】选择调度主体与等级，点击按钮开始动态路径联合解算。")
                    st.markdown("<div style='margin-top: 15px;'></div>", unsafe_allow_html=True)
                    c1, c2, c3 = st.columns(3)
                    c1.metric("监测覆盖率", "100%", help="全路网拓扑传感器状态")
                    c2.metric("平均调度响应时效", "< 15s", help="历史解算平均耗时")
                    c3.metric("应急车道可用状态", "正常", help="全段应急通道通行率")

            # Tab 2: 障碍物列表
            with tab2:
                if st.session_state.obstacles:
                    obs_df = pd.DataFrame(st.session_state.obstacles, columns=['纬度', '经度'])
                    obs_df.index += 1
                    st.dataframe(obs_df, use_container_width=True)
                    st.caption(f"共监测到 {len(obs_df)} 处道路中断点，已在底层网络拓扑中动态剔除。")
                else:
                    st.success("当前路网畅通，无结构性阻断记录。")

            # Tab 3: 算法日志
            with tab3:
                obs_log = f"网络拓扑动态重构: 移除 {len(st.session_state.obstacles)} 个故障节点..." if st.session_state.obstacles else "路网连通性校验... 完整."
                best_info = st.session_state.route_comparison.get('name', 'N/A')
                st.code(f"""
    [System] {datetime.now().strftime('%H:%M:%S')} GIS空间调度引擎自检... OK
    [System] {datetime.now().strftime('%H:%M:%S')} {obs_log}
    [Algorithm] 多目标智能打分系统 (考虑因素: 距离约束, 业务资质约束, {NETWORK_TYPE}载具运动学)
    [Context] 当前调度模块: {mode.upper()} | 气象折损权重: {get_weather_impact(weather)}
    [Result] 最优协同响应单位: {best_info}
                """, language="bash")

    with col_data:
        if st.session_state.obstacles:
            c1, c2 = st.columns([3, 1])
            c1.warning(f"已设置 {len(st.session_state.obstacles)} 处道路阻断")
            if c2.button("清除", key="clear_obstacles"):
                st.session_state.obstacles = []
                st.rerun()

        with st.expander("🌍 环境与事故感知", expanded=True):
            ec1, ec2 = st.columns(2)
            ec1.metric("天气", weather)
            w_rate = get_weather_impact(weather)
            ec2.metric("通行效率", f"{w_rate*100:.0f}%", delta=f"-{(1-w_rate)*100:.0f}%" if w_rate<1 else None)
            mode_style = "background-color:rgba(239, 68, 68, 0.15); border:1px solid rgba(239, 68, 68, 0.4); color:#ef4444;" if st.session_state.interaction_mode == 'block' else "background-color:rgba(0, 242, 254, 0.1); border:1px solid rgba(0, 242, 254, 0.3); color:#00f2fe;"
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
            is_best = st.session_state.dispatched and (selected['name'] == st.session_state.calculation_results[0]['name'])
            is_unreachable = st.session_state.dispatched and selected.get('score', 0) > 9000
            title_pre = "🏆 最佳调度方案" if is_best else "📍 选中单位"
            card_class = "info-card best" if is_best else "info-card selected"
            if is_unreachable: card_class, title_pre = "info-card warn", "🚫 不符合条件 / 不可达"

            st.markdown(f"""<div class="{card_class}"><div style="color:#94a3b8; font-size:0.8rem;">{title_pre}</div><h3 style="margin:5px 0;">{selected['name']}</h3><span style="background:rgba(255,255,255,0.08);color:#ffffff;border:1px solid rgba(255,255,255,0.1);border-radius:4px; padding:2px 6px; font-size:0.8rem;">{selected['level']}</span></div>""", unsafe_allow_html=True)

            if st.session_state.dispatched and not is_unreachable:
                c1, c2 = st.columns(2)
                c1.metric("预计耗时", f"{selected['time']:.1f}m")
                c2.metric("行驶距离", f"{selected['dist']:.0f}m")
                
                st.caption("与最优方案对比:")
                diff = selected['time'] - st.session_state.calculation_results[0]['time']
                if diff > 0: st.warning(f"慢 {diff:.1f} 分钟")
                else: st.success("当前为最快方案")

            # 针对不同模块显示动态业务属性
            st.markdown('<hr style="margin: 8px 0; border: none; border-top: 1px solid rgba(255,255,255,0.12);"/>', unsafe_allow_html=True)
            if mode == 'medical':
                st.caption(f"床位使用情况: {selected['available_beds']}/{selected['total_beds']}")
                st.progress(1 - selected['available_beds']/selected['total_beds'])
            elif mode == 'fire':
                st.write(f"🚒 **状态:** {selected['status']} | **可调派消防车:** {selected.get('trucks',0)}辆")
            elif mode == 'police':
                st.write(f"🚓 **警力状态:** {selected['status']} | **可调用警车:** {selected.get('patrol_cars',0)}辆")
            elif mode == 'hazmat':
                st.write(f"☣️ **状态:** {selected['status']} | **洗消剂储备:** {selected.get('neutralizer','未知')}")
            elif mode == 'road':
                st.write(f"🏗️ **状态:** {selected['status']} | **重型吊车:** {selected.get('heavy_cranes',0)}台 | **清障拖车:** {selected.get('tow_trucks',0)}台")
            
            # 解决右侧留白：如果已解算，在下方展示备选优选排序
            if st.session_state.dispatched and len(st.session_state.calculation_results) > 1:
                st.markdown("<div style='margin-top: 15px; border-top: 1px solid rgba(0,242,254,0.15); padding-top: 10px;'></div>", unsafe_allow_html=True)
                st.markdown("<div style='font-size: 13px; font-weight: 700; color: #00f2fe; margin-bottom: 10px;'>📊 协同响应效能优选排序</div>", unsafe_allow_html=True)
                for rank, res in enumerate(st.session_state.calculation_results[1:4], start=2):
                    st.markdown(f"""
                    <div style="background: rgba(255, 255, 255, 0.02); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 8px; padding: 10px 12px; margin-bottom: 8px;">
                        <div style="display: flex; justify-content: space-between; font-weight: 600; font-size: 12px; color: #cbd5e1;">
                            <span>No.{rank} {res['name']}</span>
                            <span style="color: #94a3b8; font-size: 11px;">{res['level']}</span>
                        </div>
                        <div style="display: flex; justify-content: space-between; color: #94a3b8; font-size: 11px; margin-top: 6px;">
                            <span>耗时: {res['time']:.1f}m</span>
                            <span>距离: {res['dist']/1000:.1f} km</span>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
        else:
            st.info("👈 在 [查看模式] 下点击地图图标查看详情")
            st.markdown("<div style='margin-top: 15px;'></div>", unsafe_allow_html=True)
            st.markdown("<div style='font-size: 13px; font-weight: 700; color: #00f2fe; margin-bottom: 10px;'>📋 备选保障力量状态一览</div>", unsafe_allow_html=True)
            for fac in facilities_basic[:4]:
                st.markdown(f"""
                <div style="background: rgba(255, 255, 255, 0.03); border: 1px solid rgba(0, 242, 254, 0.15); border-radius: 8px; padding: 10px 12px; margin-bottom: 8px; box-shadow: inset 0 0 10px rgba(0,242,254,0.02);">
                    <div style="display: flex; justify-content: space-between; font-weight: 600; font-size: 12px; color: #ffffff;">
                        <span>{fac['name']}</span>
                        <span style="color: #00f2fe; background: rgba(0,242,254,0.1); border: 1px solid rgba(0,242,254,0.25); border-radius: 4px; padding: 1px 6px; font-size: 10px;">{fac['level']}</span>
                    </div>
                    <div style="display: flex; justify-content: space-between; color: #cbd5e1; font-size: 11px; margin-top: 6px;">
                        <span>预计距离: 内侧寻优中</span>
                        <span style="color: #10b981;">● 待命可用</span>
                    </div>
                </div>
                """, unsafe_allow_html=True)



if __name__ == "__main__":
    main()
