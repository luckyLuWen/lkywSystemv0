import threading
import time
import serial
import sqlite3
import json
import csv
import io
import os
import base64
import shutil
import concurrent.futures

# ================= [核心配置] 极速低延迟 UDP 模式 =================
os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;udp|fflags;nobuffer|flags;low_delay|strict;experimental|max_delay;0"

import cv2
from datetime import datetime
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

# ================= 1. 系统配置 =================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.getenv("DB_PATH", os.path.join(BASE_DIR, "sensor_data.db"))
SYSTEM_RUNNING = True 

# 📡 无人机 RTMP 推流地址
DRONE_RTMP_URL = "rtmp://192.168.0.67:1935/live/abc"

# 📂 文件保存路径
IMG_DIR = r"D:\sat\image"
VIDEO_DIR = r"D:\sat\view"

for path in [IMG_DIR, VIDEO_DIR]:
    if not os.path.exists(path):
        try:
            os.makedirs(path)
            print(f"✅ 已创建目录: {path}")
        except Exception as e:
            print(f"❌ 创建目录失败: {e}")

# 传感器节点配置
NODES = {
    "node1": {"name": "节点1", "type": "5in1", "url": "socket://192.168.0.219:10123", "ser": None, "error_count": 0},
    "node2": {"name": "节点2", "type": "5in1", "url": "socket://192.168.0.241:10123", "ser": None, "error_count": 0},
    "node3": {"name": "节点3", "type": "wind", "url": "socket://192.168.0.71:10123",  "ser": None, "error_count": 0}
}

# Modbus 指令集
CMD_SENSOR_5IN1 = bytes.fromhex("03 03 00 01 00 14 15 E7")
CMD_WIND = bytes.fromhex("01 03 00 04 00 02 85 CA")

# 🌍 全局数据缓存
latest_data = {
    "node1": {"temp": 0, "hum": 0, "smoke": 0, "tvoc": 0, "co": 0},
    "node2": {"temp": 0, "hum": 0, "smoke": 0, "tvoc": 0, "co": 0},
    "node3": {"wind": 0, "wind_dir": "--"}
}
data_lock = threading.Lock()

# ================= 2. 数据库管理 =================
def init_db():
    db_dir = os.path.dirname(DB_PATH)
    if db_dir and not os.path.exists(db_dir): os.makedirs(db_dir)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS records
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  timestamp DATETIME,
                  n1_temp REAL, n1_hum REAL, n1_smoke REAL, n1_tvoc REAL, n1_co REAL, 
                  n2_temp REAL, n2_hum REAL, n2_smoke REAL, n2_tvoc REAL, n2_co REAL,
                  wind_speed REAL, wind_dir TEXT,
                  image_path TEXT)''')
    conn.commit()
    conn.close()

def save_to_db(data, img_path=None):
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("""INSERT INTO records 
                     (timestamp, n1_temp, n1_hum, n1_smoke, n1_tvoc, n1_co,
                      n2_temp, n2_hum, n2_smoke, n2_tvoc, n2_co,
                      wind_speed, wind_dir, image_path) 
                      VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                  (datetime.now(), 
                   data['node1'].get('temp', 0), data['node1'].get('hum', 0), 
                   data['node1'].get('smoke', 0), data['node1'].get('tvoc', 0), data['node1'].get('co', 0),
                   data['node2'].get('temp', 0), data['node2'].get('hum', 0),
                   data['node2'].get('smoke', 0), data['node2'].get('tvoc', 0), data['node2'].get('co', 0),
                   data['node3'].get('wind', 0), data['node3'].get('wind_dir', '--'),
                   img_path)) 
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"写入失败: {e}")

# ================= 3. 传感器采集逻辑 =================
def clear_buffer(ser):
    try:
        if ser.in_waiting > 0: ser.read(ser.in_waiting)
    except: pass

def smart_read_modbus(ser, expected_addr, expected_func, expected_len):
    try:
        raw = ser.read(expected_len + 5) 
        if not raw: return None
        for i in range(len(raw) - 1):
            if raw[i] == expected_addr and raw[i+1] == expected_func:
                if len(raw) - i >= expected_len:
                    return raw[i : i + expected_len]
        return None
    except: return None

def ensure_conn(key):
    node = NODES[key]
    if node["error_count"] > 5:
        if node["ser"]: 
            try: node["ser"].close() 
            except: pass
        node["ser"] = None
        node["error_count"] = 0
    if node["ser"] is None:
        try:
            node["ser"] = serial.serial_for_url(node["url"], baudrate=9600, timeout=0.4)
            print(f"🔄 {node['name']} 重连成功")
        except: node["ser"] = None
    return node["ser"]

def get_wind_dir_str(val):
    dirs = ["北", "北偏东", "东北", "东偏北", "东", "东偏南", "东南", "南偏东", 
            "南", "南偏西", "西南", "西偏南", "西", "西偏北", "西北", "北偏西"]
    return dirs[val] if 0 <= val < len(dirs) else "未知"

def parse_5in1_data(d):
    try:
        if len(d) < 45: return None 
        def get_reg(n):
            idx = 3 + (n - 1) * 2
            return (d[idx] << 8) | d[idx+1]
        
        # 🟢 [修改] 严格科学换算：ppm 转 ug/m3
        # 公式: Mass = ppm * (MolecularWeight / 24.45) * 1000
        # 假设烟雾平均分子量 M = 30 (近似空气/CO混合物)
        # 系数 = (30 / 24.45) * 1000 ≈ 1227
        
        raw_smoke_ppm = get_reg(11)
        smoke_ug = int(raw_smoke_ppm * 1227) 

        return {
            "temp": round((get_reg(1) - 2000) / 100.0, 2),
            "hum": round(get_reg(2) / 100.0, 2),
            "smoke": smoke_ug, # 存入数据库的是巨大的 ug/m3 数值
            "tvoc": round(get_reg(14) / 100.0, 3),
            "co": round(get_reg(18) / 10.0, 1)
        }
    except: return None

def parse_wind_data(d):
    try:
        if len(d) < 9: return None
        wind_val = ((d[3]<<8)|d[4]) / 100.0
        dir_val = ((d[5]<<8)|d[6])
        return {
            "wind": wind_val,
            "wind_dir": get_wind_dir_str(dir_val)
        }
    except: return None

def read_single_node_task(node_key):
    node_cfg = NODES[node_key]
    ser = ensure_conn(node_key)
    result = None
    if ser:
        try:
            clear_buffer(ser)
            if node_cfg["type"] == "wind":
                ser.write(CMD_WIND)
                d = smart_read_modbus(ser, 0x01, 0x03, 9)
                if d: result = parse_wind_data(d)
            elif node_cfg["type"] == "5in1":
                ser.write(CMD_SENSOR_5IN1)
                d = smart_read_modbus(ser, 0x03, 0x03, 45)
                if d: result = parse_5in1_data(d)
            if result: NODES[node_key]["error_count"] = 0
            else: NODES[node_key]["error_count"] += 1
        except: NODES[node_key]["error_count"] += 1
    else: NODES[node_key]["error_count"] += 1
    return node_key, result

def background_task():
    global latest_data, SYSTEM_RUNNING
    print("传感器采集线程启动 (0.5s 周期)...")
    executor = concurrent.futures.ThreadPoolExecutor(max_workers=3)
    while True:
        loop_start = time.time()
        if not SYSTEM_RUNNING:
            time.sleep(1)
            continue
        future_to_node = {executor.submit(read_single_node_task, key): key for key in ["node1", "node2", "node3"]}
        round_data = {"node1": {}, "node2": {}, "node3": {}}
        for future in concurrent.futures.as_completed(future_to_node):
            key, res = future.result()
            if res: round_data[key] = res
        defaults_5in1 = {"temp": 0, "hum": 0, "smoke": 0, "tvoc": 0, "co": 0}
        defaults_wind = {"wind": 0, "wind_dir": "--"}
        for key in ["node1", "node2", "node3"]:
            if not round_data[key]:
                round_data[key] = defaults_wind if NODES[key]["type"] == "wind" else defaults_5in1
        with data_lock:
            latest_data = round_data
        save_to_db(round_data, img_path=None)
        elapsed = time.time() - loop_start
        sleep_time = max(0, 0.5 - elapsed)
        time.sleep(sleep_time)

# ================= 4. 视频流逻辑 =================

class VideoStream:
    def __init__(self, url):
        self.url = url
        self.cap = cv2.VideoCapture(self.url, cv2.CAP_FFMPEG)
        self.frame = None
        self.running = True
        self.lock = threading.Lock()
        self.thread = threading.Thread(target=self.update, args=())
        self.thread.daemon = True
        self.thread.start()

    def update(self):
        count = 0 
        while self.running:
            if self.cap.isOpened():
                self.cap.grab() 
                count += 1
                if count % 3 == 0:
                    success, frame = self.cap.retrieve()
                    if success:
                        with self.lock:
                            self.frame = frame
                    else:
                        time.sleep(0.01)
                if count > 1000: count = 0
            else:
                print("⚠️ 视频流断开，正在重连...")
                time.sleep(0.5)
                self.cap.release()
                self.cap = cv2.VideoCapture(self.url, cv2.CAP_FFMPEG)

    def read(self):
        with self.lock:
            return self.frame.copy() if self.frame is not None else None

    def stop(self):
        self.running = False
        self.thread.join()
        self.cap.release()

print(f"正在连接无人机视频流 (UDP极速版): {DRONE_RTMP_URL} ...")
drone_stream = VideoStream(DRONE_RTMP_URL)

def generate_frames():
    while True:
        frame = drone_stream.read()
        if frame is None:
            time.sleep(0.1)
            continue
        try:
            frame = cv2.resize(frame, (640, 360))
            ret, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 40])
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
            time.sleep(0.033) 
        except Exception as e:
            time.sleep(0.01)

# ================= 5. API 接口 =================
@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    t = threading.Thread(target=background_task, daemon=True)
    t.start()
    yield

app = FastAPI(lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

@app.get("/api/video_feed")
def video_feed():
    return StreamingResponse(generate_frames(), media_type="multipart/x-mixed-replace; boundary=frame")

class ImageModel(BaseModel):
    image: str 

@app.post("/api/save_drone_image")
def save_drone_image(data: ImageModel):
    try:
        with data_lock:
            current_sensor_snapshot = latest_data.copy()
        if "base64," in data.image:
            header, encoded = data.image.split(",", 1)
        else:
            encoded = data.image
        image_data = base64.b64decode(encoded)
        filename = datetime.now().strftime("%m%d_%H%M%S_%f")[:-3] + ".jpg"
        filepath = os.path.join(IMG_DIR, filename)
        with open(filepath, "wb") as f:
            f.write(image_data)
        save_to_db(current_sensor_snapshot, img_path=filepath)
        print(f"📸 截图保存成功: {filename}")
        return {"status": "success", "path": filepath}
    except Exception as e:
        print(f"❌ 截图保存失败: {e}")
        return {"status": "error", "msg": str(e)}

@app.post("/api/save_drone_video")
async def save_drone_video(file: UploadFile = File(...)):
    try:
        with data_lock:
            current_sensor_snapshot = latest_data.copy()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"Drone_Record_{timestamp}.webm"
        filepath = os.path.join(VIDEO_DIR, filename)
        with open(filepath, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        save_to_db(current_sensor_snapshot, img_path=filepath)
        print(f"🎥 视频保存成功: {filepath}")
        return {"status": "success", "path": filepath}
    except Exception as e:
        print(f"❌ 视频保存失败: {e}")
        return {"status": "error", "msg": str(e)}

@app.get("/api/history")
def get_history_api(limit: int = 100, start: str = None, end: str = None):
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        if start and end:
            c.execute("SELECT * FROM records WHERE timestamp BETWEEN ? AND ? ORDER BY id ASC", (start, end))
        else:
            c.execute("SELECT * FROM records ORDER BY id DESC LIMIT ?", (limit,))
        rows = c.fetchall()
        if not (start and end):
            rows = list(reversed(rows))
        conn.close()
        return [dict(row) for row in rows]
    except Exception as e:
        return []

@app.get("/api/export")
def export_csv(start: str = None, end: str = None):
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        if start and end:
            c.execute("SELECT * FROM records WHERE timestamp BETWEEN ? AND ? ORDER BY id DESC", (start, end))
        else:
            c.execute("SELECT * FROM records ORDER BY id DESC LIMIT 50000")
        rows = c.fetchall()
        conn.close()
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["ID", "时间", "N1温度", "N1湿度", "N1烟雾(ug/m3)", "N1TVOC", "N1CO", 
                         "N2温度", "N2湿度", "N2烟雾(ug/m3)", "N2TVOC", "N2CO", 
                         "N3风速", "N3风向", "图片路径"])
        for row in rows: writer.writerow(row)
        return Response(content="\ufeff"+output.getvalue(), media_type="text/csv", headers={"Content-Disposition": "attachment; filename=data.csv"})
    except Exception as e: return {"error": str(e)}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            await websocket.send_text(json.dumps(latest_data))
            import asyncio
            await asyncio.sleep(0.5)
    except: pass

DIST_DIR = os.path.join(BASE_DIR, "dist")
if os.path.exists(DIST_DIR):
    app.mount("/assets", StaticFiles(directory=os.path.join(DIST_DIR, "assets")), name="assets")
    @app.get("/{full_path:path}")
    async def serve_vue(full_path: str):
        if full_path.startswith("api") or full_path.startswith("ws"): return Response(status_code=404)
        return FileResponse(os.path.join(DIST_DIR, "index.html"))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)