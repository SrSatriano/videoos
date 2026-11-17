from __future__ import annotations

from collections import namedtuple

from fastapi.testclient import TestClient

from app.main import app
from app.services import storage


client = TestClient(app)
DiskUsage = namedtuple("DiskUsage", "total used free")
GIB = 1024**3


def test_storage_capacity_keeps_reserve_and_estimate_buffer(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(storage.config, "ALLOWED_OUTPUT_ROOTS", [tmp_path])
    monkeypatch.setattr(storage.shutil, "disk_usage", lambda _path: DiskUsage(10 * GIB, 5 * GIB, 5 * GIB))

    result = storage.check_storage_capacity(str(tmp_path), 3 * GIB)

    assert result["reserve_bytes"] == GIB
    assert result["safe_available_bytes"] == 4 * GIB
    assert result["required_bytes"] > 3 * GIB
    assert result["has_capacity"] is True


def test_storage_capacity_rejects_estimate_above_safe_space(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(storage.config, "ALLOWED_OUTPUT_ROOTS", [tmp_path])
    monkeypatch.setattr(storage.shutil, "disk_usage", lambda _path: DiskUsage(10 * GIB, 5 * GIB, 5 * GIB))

    result = storage.check_storage_capacity(str(tmp_path), 4 * GIB)

    assert result["required_bytes"] > result["safe_available_bytes"]
    assert result["has_capacity"] is False


def test_storage_check_endpoint_returns_backend_measurement(monkeypatch) -> None:
    expected = {
        "path": "/workspace/data/renders",
        "total_bytes": 10 * GIB,
        "free_bytes": 5 * GIB,
        "reserve_bytes": GIB,
        "safe_available_bytes": 4 * GIB,
        "estimated_output_bytes": 2 * GIB,
        "required_bytes": 2_469_606_196,
        "estimate_buffer_ratio": 0.15,
        "has_capacity": True,
    }

    monkeypatch.setattr("app.routes.system.check_storage_capacity", lambda _path, _estimate: expected)

    response = client.post(
        "/api/system/storage-check",
        json={"output_dir": "/workspace/data/renders", "estimated_output_bytes": 2 * GIB},
    )

    assert response.status_code == 200
    assert response.json() == expected
