"""Select the YOLO26-compatible Ultralytics runtime before model imports."""

from __future__ import annotations

import inspect
import os
import sys
from pathlib import Path


DEFAULT_ULTRALYTICS_SOURCE = Path("/home/zhangboyu/SFGAYOLO26")
REQUIRED_VERSION = "8.4.56"


def activate_ultralytics_runtime() -> Path:
    """Load the local YOLO26 runtime and reject incompatible fallbacks."""
    source_root = Path(
        os.environ.get("LKYW_ULTRALYTICS_SOURCE", str(DEFAULT_ULTRALYTICS_SOURCE))
    ).expanduser().resolve()
    package_init = source_root / "ultralytics" / "__init__.py"
    if not package_init.is_file():
        raise RuntimeError(
            "YOLO26-compatible Ultralytics source was not found at "
            f"{source_root}. Set LKYW_ULTRALYTICS_SOURCE to the 8.4.56 source directory."
        )

    source_text = str(source_root)
    if source_text in sys.path:
        sys.path.remove(source_text)
    sys.path.insert(0, source_text)

    import ultralytics
    from ultralytics.nn.modules.head import Detect

    loaded_package = Path(ultralytics.__file__).resolve()
    try:
        loaded_package.relative_to(source_root)
    except ValueError as exc:
        raise RuntimeError(
            "An incompatible Ultralytics package was imported before the YOLO26 runtime: "
            f"{loaded_package}"
        ) from exc

    detect_parameters = inspect.signature(Detect.__init__).parameters
    missing_parameters = {"reg_max", "end2end"} - set(detect_parameters)
    if ultralytics.__version__ != REQUIRED_VERSION or missing_parameters:
        raise RuntimeError(
            "Incompatible Ultralytics runtime. "
            f"Expected {REQUIRED_VERSION} with YOLO26 Detect(reg_max, end2end), "
            f"loaded {ultralytics.__version__} from {loaded_package}."
        )

    return source_root
