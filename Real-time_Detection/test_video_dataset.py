"""Run the configured SFGA-YOLO26M model on top-level video test clips."""

from __future__ import annotations

import argparse
import math
import os
from datetime import datetime
from pathlib import Path

from web_app.backend.ultralytics_runtime import activate_ultralytics_runtime

os.environ.setdefault("MPLCONFIGDIR", "/tmp/matplotlib-codex")
os.environ.setdefault("YOLO_CONFIG_DIR", "/tmp/ultralytics-codex")
os.environ["TORCH_LOAD_WEIGHTS_ONLY"] = "0"

activate_ultralytics_runtime()

import cv2

from web_app.backend.sfga_compat import register_sfga_modules


ROOT = Path(__file__).resolve().parent
DEFAULT_VIDEO_DIR = ROOT / "testFile/videoTest"
DEFAULT_WEIGHTS = ROOT / "LKYWDataset_weights/yolo26m_BestPt_1/best.pt"
DEFAULT_REPORT = ROOT / "video_dataset_sfga_report.md"
CONFIDENCE = 0.60
IOU = 0.45
FRAME_INTERVAL = 15
BATCH_SIZE = 8


def detect_batch(model, frames, frame_numbers, fps):
    predictions = model.predict(
        source=frames,
        conf=CONFIDENCE,
        iou=IOU,
        verbose=False,
        device="cpu",
        batch=BATCH_SIZE,
    )
    records = []
    for frame_number, prediction in zip(frame_numbers, predictions):
        detections = []
        for box in prediction.boxes:
            class_id = int(box.cls[0])
            detections.append(
                {
                    "class": prediction.names[class_id],
                    "confidence": float(box.conf[0]),
                }
            )
        records.append(
            {
                "frame": frame_number,
                "seconds": frame_number / fps,
                "detections": detections,
            }
        )
    return records


def scan_video(model, path):
    cap = cv2.VideoCapture(str(path))
    if not cap.isOpened():
        raise RuntimeError("OpenCV cannot open this video")

    fps = float(cap.get(cv2.CAP_PROP_FPS) or 0)
    if not math.isfinite(fps) or fps <= 0:
        cap.release()
        raise RuntimeError("Video has invalid FPS metadata")

    reported_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
    frame_number = 0
    batch_frames = []
    batch_numbers = []
    sampled_results = []

    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                break
            if frame_number % FRAME_INTERVAL == 0:
                batch_frames.append(frame)
                batch_numbers.append(frame_number)
                if len(batch_frames) >= BATCH_SIZE:
                    sampled_results.extend(
                        detect_batch(model, batch_frames, batch_numbers, fps)
                    )
                    batch_frames.clear()
                    batch_numbers.clear()
            frame_number += 1
        if batch_frames:
            sampled_results.extend(detect_batch(model, batch_frames, batch_numbers, fps))
    finally:
        cap.release()

    return {
        "name": path.name,
        "fps": fps,
        "frame_count": frame_number,
        "reported_frame_count": reported_frames,
        "duration": frame_number / fps,
        "width": width,
        "height": height,
        "sampled_frames": len(sampled_results),
        "detections": [row for row in sampled_results if row["detections"]],
    }


def format_time(seconds):
    return f"{seconds:.3f}"


def write_report(path, results, video_dir, weight_path):
    valid_results = [item for item in results if "error" not in item]
    total_detected_frames = sum(len(item["detections"]) for item in valid_results)
    tested_at = datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S %Z")
    lines = [
        "# 视频检测测试结果",
        "",
        f"- 测试时间：{tested_at}",
        f"- 测试范围：`{video_dir}` 顶层目录中的 MP4；不递归进入子目录（包括 P1、P2），不处理文档文件。",
        f"- 视频数量：{len(results)}",
        f"- 算法：SFGA-YOLO26M（沿用后端现有映射，权重文件 `{weight_path}`）",
        f"- 置信度阈值：{CONFIDENCE:.2f}",
        f"- IoU 阈值：{IOU:.2f}",
        f"- 抽帧间隔：每 {FRAME_INTERVAL} 帧检测一次，从第 0 帧开始（0-based 帧号）",
        f"- 推理设备：CPU（本机 `lkywSystem` 环境未检测到可用 CUDA 设备）",
        f"- 检测到目标的视频帧总数：{total_detected_frames}",
        "- 说明：下表仅列出检测到目标的抽样帧；未列出的抽样帧均未检出目标。时间按 `帧号 / 视频 FPS` 计算。",
        "",
        "## 汇总",
        "",
        "| 视频名称 | 时长(s) | FPS | 总帧数 | 抽样帧数 | 检出目标帧数 | 检出帧号（0-based） |",
        "|---|---:|---:|---:|---:|---:|---|",
    ]

    for item in results:
        if "error" in item:
            lines.append(f"| `{item['name']}` | - | - | - | - | - | 测试失败：{item['error']} |")
            continue
        frame_list = ", ".join(str(row["frame"]) for row in item["detections"]) or "无"
        lines.append(
            f"| `{item['name']}` | {item['duration']:.3f} | {item['fps']:.3f} | "
            f"{item['frame_count']} | {item['sampled_frames']} | "
            f"{len(item['detections'])} | {frame_list} |"
        )

    lines.extend(["", "## 检出帧明细", ""])
    for item in results:
        lines.extend([f"### `{item['name']}`", ""])
        if "error" in item:
            lines.extend([f"测试失败：{item['error']}", ""])
            continue
        if not item["detections"]:
            lines.extend(["未检出目标。", ""])
            continue
        lines.extend(
            [
                "| 秒数(s) | 帧号（0-based） | 检测结果（类别：置信度） |",
                "|---:|---:|---|",
            ]
        )
        for row in item["detections"]:
            detection_text = "；".join(
                f"{det['class']}：{det['confidence']:.4f}"
                for det in row["detections"]
            )
            lines.append(
                f"| {format_time(row['seconds'])} | {row['frame']} | {detection_text} |"
            )
        lines.append("")

    path.write_text("\n".join(lines), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--videos-dir", type=Path, default=DEFAULT_VIDEO_DIR)
    parser.add_argument("--weights", type=Path, default=DEFAULT_WEIGHTS)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    args = parser.parse_args()

    # Keep numbered files in human order (video2 before video10).
    videos = sorted(
        (item for item in args.videos_dir.iterdir() if item.is_file() and item.suffix.lower() == ".mp4"),
        key=lambda item: (
            int(item.stem[5:]) if item.stem.casefold().startswith("video") and item.stem[5:].isdigit() else math.inf,
            item.name.casefold(),
        ),
    )
    if not videos:
        raise SystemExit(f"No top-level MP4 files found in {args.videos_dir}")
    if not args.weights.is_file():
        raise SystemExit(f"Model weights not found: {args.weights}")

    register_sfga_modules()
    from ultralytics import YOLO

    print(f"Loading SFGA-YOLO26M weights: {args.weights}", flush=True)
    model = YOLO(str(args.weights))
    results = []
    for index, video in enumerate(videos, 1):
        print(f"[{index}/{len(videos)}] {video.name}", flush=True)
        try:
            result = scan_video(model, video)
            results.append(result)
            print(
                f"  {result['sampled_frames']} sampled frames; "
                f"{len(result['detections'])} with detections",
                flush=True,
            )
        except Exception as exc:
            results.append({"name": video.name, "error": str(exc)})
            print(f"  ERROR: {exc}", flush=True)

    write_report(args.report, results, args.videos_dir, args.weights)
    errors = [item for item in results if "error" in item]
    print(f"Report written to {args.report}", flush=True)
    if errors:
        raise SystemExit(f"{len(errors)} video(s) failed; see report")


if __name__ == "__main__":
    main()
