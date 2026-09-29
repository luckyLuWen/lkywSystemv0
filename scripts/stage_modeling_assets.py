"""Copy the prepared UAV/UGV datasets and PLY meshes into the main app's public assets.

The generated catalog is read by the browser at /ModelingData/catalog.json. Large source
datasets and meshes are intentionally kept out of Git; see the matching .gitignore entries.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
from pathlib import Path
from urllib.parse import quote


REPO_ROOT = Path(__file__).resolve().parents[1]
PUBLIC_ROOT = REPO_ROOT / "vue-project_all" / "public" / "ModelingData"
DEFAULT_DEMO_ROOT = Path(r"Q:\final_lkywsystemv0")
PHOTO_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}
DEMO_SPECS = (
    {
        "id": "coach-synthetic",
        "title": "客运车仿真场景",
        "folder": "客运车_仿真视角演示",
        "slug": "coach-synthetic",
    },
    {
        "id": "coach-jetset-synthetic",
        "title": "长途客运巴士仿真场景",
        "folder": "长途客运巴士仿真视角演示",
        "slug": "coach-jetset-synthetic",
    },
)


def copy_dataset(source: Path, destination: Path) -> None:
    if not source.is_dir():
        raise FileNotFoundError(f"Dataset directory not found: {source}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        shutil.rmtree(destination)
    shutil.copytree(source, destination, dirs_exist_ok=True, copy_function=shutil.copy2)


def read_ply_header(path: Path) -> str:
    header = bytearray()
    with path.open("rb") as source:
        while len(header) < 64 * 1024:
            line = source.readline()
            if not line:
                break
            header.extend(line)
            if line.strip() == b"end_header":
                break

    return header.decode("ascii", errors="replace")


def read_ply_counts(path: Path) -> tuple[int, int]:
    text = read_ply_header(path)
    vertex_match = re.search(r"^element\s+vertex\s+(\d+)\s*$", text, re.MULTILINE)
    face_match = re.search(r"^element\s+face\s+(\d+)\s*$", text, re.MULTILINE)
    if not vertex_match or not face_match or "end_header" not in text:
        raise ValueError(f"Could not read vertex/face counts from PLY header: {path}")
    return int(vertex_match.group(1)), int(face_match.group(1))


def public_url(relative_path: Path) -> str:
    return "/ModelingData/" + quote(relative_path.as_posix(), safe="/")


def collect_dataset(dataset_id: str, title: str, source: Path, destination: Path, model: dict) -> dict:
    copy_dataset(source, destination)

    images = []
    samples = []
    counts = {"uav": 0, "ugv": 0}
    for group_name, count_key in (("UAV", "uav"), ("UGV", "ugv")):
        group_folder = source / group_name
        if not group_folder.is_dir():
            continue

        paths = sorted(
            (path for path in group_folder.rglob("*") if path.is_file() and path.suffix.lower() in PHOTO_EXTENSIONS),
            key=lambda path: path.as_posix().lower(),
        )
        counts[count_key] = len(paths)
        group_records = []
        for path in paths:
            staged_path = destination / path.relative_to(source)
            relative = staged_path.relative_to(PUBLIC_ROOT)
            record = {
                "name": path.name,
                "kind": count_key,
                "bytes": path.stat().st_size,
                "url": public_url(relative),
            }
            images.append(record)
            group_records.append(record)

        sample_indexes = [0] if group_records else []
        for index in sample_indexes:
            samples.append(group_records[index])

    model["datasetCounts"] = {"total": counts["uav"] + counts["ugv"], **counts}

    return {
        "id": dataset_id,
        "title": title,
        "vehicleType": model.get("vehicleType", "coach"),
        "captureType": model.get("captureType", "captured"),
        "datasetName": source.name,
        "dataDirectory": public_url(destination.relative_to(PUBLIC_ROOT)),
        "counts": {"total": counts["uav"] + counts["ugv"], **counts},
        "images": images,
        "samples": samples,
        "model": model,
    }


def build_catalog(demo_root: Path, public_root: Path) -> dict:
    datasets_root = public_root / "datasets"
    datasets = []
    for spec in DEMO_SPECS:
        source = demo_root / spec["folder"]
        model_source = source / "models"
        ply_files = sorted(model_source.glob("*.ply"), key=lambda path: path.name.lower())
        if not ply_files:
            raise FileNotFoundError(f"No PLY model found in prepared demo: {model_source}")
        ply = max(ply_files, key=lambda path: ("meshed-poisson" in path.name.lower(), read_ply_counts(path)[1]))
        vertices, faces = read_ply_counts(ply)
        header = read_ply_header(ply)
        has_uv = bool(re.search(r"^property\s+float\s+(?:u|v|s|t)\s*$", header, re.MULTILINE))
        has_vertex_colors = all(
            re.search(rf"^property\s+\w+\s+{channel}\s*$", header, re.MULTILINE)
            for channel in ("red", "green", "blue")
        )

        texture_candidates = sorted(
            (
                path
                for path in model_source.iterdir()
                if path.is_file()
                and path.suffix.lower() in PHOTO_EXTENSIONS
                and re.search(r"texture|atlas|albedo|material", path.name, re.IGNORECASE)
            ),
            key=lambda path: path.name.lower(),
        )
        texture = texture_candidates[0] if texture_candidates and has_uv else None
        destination = datasets_root / spec["slug"]
        relative_model = Path("datasets") / spec["slug"] / "models" / ply.name
        preview_candidates = sorted((source / "UAV").glob("*"), key=lambda path: path.name.lower())
        preview_url = public_url(Path("datasets") / spec["slug"] / "UAV" / preview_candidates[0].name) if preview_candidates else ""

        metadata_path = source / "metadata.xml"
        metadata_text = metadata_path.read_text(encoding="utf-8") if metadata_path.is_file() else ""
        axis_match = re.search(r"<UpAxis>\s*([yz])\s*</UpAxis>", metadata_text, re.IGNORECASE)
        capture_match = re.search(r"<CaptureType>\s*([^<]+)\s*</CaptureType>", metadata_text, re.IGNORECASE)
        scale_match = re.search(r"<ScaleCalibrated>\s*(true|false)\s*</ScaleCalibrated>", metadata_text, re.IGNORECASE)
        capture_type = capture_match.group(1).strip().lower() if capture_match else "synthetic"
        scale_calibrated = scale_match.group(1).lower() == "true" if scale_match else False

        model = {
            "sceneDescription": spec["title"],
            "fileName": ply.name,
            "format": "PLY",
            "url": public_url(relative_model),
            "previewUrl": preview_url,
            "textureUrl": public_url(relative_model.parent / texture.name) if texture else "",
            "vertices": vertices,
            "faces": faces,
            "upAxis": axis_match.group(1).lower() if axis_match else "z",
            "coordinateSystem": "仿真场景局部坐标",
            "unitLabel": "模型单位",
            "scaleCalibrated": scale_calibrated,
            "scaleFactor": 1.0,
            "coordinateLabel": "未标定 · 模型单位",
            "scaleSource": "演示模型未提供已知实长或独立控制点",
            "surfaceAppearance": "UV纹理图集" if texture else "顶点颜色" if has_vertex_colors else "单色网格",
            "captureType": capture_type,
            "vehicleType": "coach",
        }
        dataset = collect_dataset(spec["id"], spec["title"], source, destination, model)
        datasets.append(dataset)

    return {"version": 2, "datasets": datasets}


def main() -> None:
    parser = argparse.ArgumentParser(description="Stage the two prepared synthetic passenger-coach demonstrations.")
    parser.add_argument("--demo-root", type=Path, default=DEFAULT_DEMO_ROOT)
    parser.add_argument("--public-root", type=Path, default=PUBLIC_ROOT)
    args = parser.parse_args()

    public_root = args.public_root.resolve()
    public_root.mkdir(parents=True, exist_ok=True)
    catalog = build_catalog(args.demo_root.resolve(), public_root)
    catalog_path = public_root / "catalog.json"
    catalog_path.write_text(json.dumps(catalog, ensure_ascii=False, indent=2), encoding="utf-8")

    for dataset in catalog["datasets"]:
        counts = dataset["counts"]
        model = dataset["model"]
        print(
            f"{dataset['id']}: UAV={counts['uav']}, UGV={counts['ugv']}, "
            f"vertices={model['vertices']:,}, faces={model['faces']:,}, model={model['url']}"
        )
    print(f"Catalog written to: {catalog_path}")


if __name__ == "__main__":
    main()
