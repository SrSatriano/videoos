from __future__ import annotations

from app.services.media import available_hardware_encoders, resolve_render_codec, ffmpeg_status


def test_hardware_encoder_detection_and_resolution(monkeypatch) -> None:
    from app.services import media

    # Mock available encoders with nvenc
    monkeypatch.setattr(media, "available_video_encoders", lambda: ["libx264", "h264_nvenc", "hevc_nvenc"])

    hw = available_hardware_encoders()
    assert "h264_nvenc" in hw
    assert "hevc_nvenc" in hw

    codec, accel = resolve_render_codec("auto")
    assert codec == "h264_nvenc"
    assert accel == "nvenc"

    codec_cpu, accel_cpu = resolve_render_codec("libx264")
    assert codec_cpu == "libx264"
    assert accel_cpu == "cpu"


def test_hardware_encoder_fallback_when_unavailable(monkeypatch) -> None:
    from app.services import media

    # Mock only CPU encoder available
    monkeypatch.setattr(media, "available_video_encoders", lambda: ["libx264"])

    hw = available_hardware_encoders()
    assert hw == []

    codec, accel = resolve_render_codec("h264_nvenc")
    assert codec == "libx264"
    assert accel == "cpu"
