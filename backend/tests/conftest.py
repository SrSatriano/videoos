from __future__ import annotations

import os
import tempfile
from pathlib import Path


TEST_ROOT = Path(tempfile.mkdtemp(prefix="video-os-tests-"))
IMPORT_ROOT = TEST_ROOT / "imports com acento"
DATA_ROOT = TEST_ROOT / "data"
IMPORT_ROOT.mkdir(parents=True, exist_ok=True)
DATA_ROOT.mkdir(parents=True, exist_ok=True)

os.environ["VIDEO_OS_DATA_DIR"] = str(DATA_ROOT)
os.environ["VIDEO_OS_IMPORT_ROOTS"] = str(IMPORT_ROOT)
os.environ["VIDEO_OS_CORS_ORIGINS"] = "http://localhost:5173"


def pytest_configure() -> None:
    IMPORT_ROOT.mkdir(parents=True, exist_ok=True)


def pytest_unconfigure() -> None:
    # Keep artifacts on disk for failed-test inspection; temp cleanup is owned by the OS.
    return None
