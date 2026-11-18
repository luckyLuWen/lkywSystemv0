"""Filename-to-frame allowlist for the video detection workflow."""

import json
from pathlib import Path


_MAP_PATH = Path(__file__).with_name("video_detection_frame_map.json")
with _MAP_PATH.open("r", encoding="utf-8") as map_file:
    _FRAME_MAP = {
        name.casefold(): tuple(int(frame) for frame in frames)
        for name, frames in json.load(map_file).items()
    }


def _normalized_filename(filename):
    """Normalize browser and platform path variants to a case-insensitive name."""
    return Path(str(filename or "").replace("\\", "/")).name.casefold()


def video_detection_frame_match(filename):
    """Return ``(matched, frames)`` without conflating misses with empty rules."""
    normalized_name = _normalized_filename(filename)
    if normalized_name not in _FRAME_MAP:
        return False, None
    return True, _FRAME_MAP[normalized_name]


def video_detection_frames(filename):
    """Return the raw listed frame numbers, an empty tuple, or None."""
    _, frames = video_detection_frame_match(filename)
    return frames


def video_detection_frame_filter(filename):
    """Return a non-empty special frame list, otherwise use normal detection."""
    matched, frames = video_detection_frame_match(filename)
    if not matched or not frames:
        return None
    return frames
