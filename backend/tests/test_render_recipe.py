from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace

import pytest

from app.services import render
from app.services.seed import DEFAULT_RECIPE
from conftest import DATA_ROOT


def test_validate_recipe_requires_vertical_9_16() -> None:
    recipe = {**DEFAULT_RECIPE, "format": {"width": 1920, "height": 1080, "fit": "crop"}}

    with pytest.raises(ValueError, match="9:16"):
        render.validate_recipe(recipe)


@pytest.mark.parametrize(("width", "height"), [(1080, 1920), (1440, 2560), (2160, 3840)])
def test_validate_recipe_accepts_export_resolution_presets(width: int, height: int) -> None:
    recipe = deepcopy(DEFAULT_RECIPE)
    recipe["format"] = {"width": width, "height": height, "fit": "crop", "fps": 30}

    render.validate_recipe(recipe)


def test_build_filters_adds_text_and_watermark() -> None:
    filters = render.build_video_filters(DEFAULT_RECIPE, variation_index=3)

    assert "scale=1080:1920" in filters
    assert "crop=1080:1920" in filters
    assert "setsar=1" in filters
    assert "drawtext" in filters
    assert "drawtext=fontfile=" in filters or "drawtext=text=" in filters
    assert "drawtext:fontfile=" not in filters
    assert "Hoje vamos automatizar" in filters
    assert "@sistema.dark" in filters
    assert "#3" in filters


def test_build_filters_supports_burned_captions() -> None:
    recipe = deepcopy(DEFAULT_RECIPE)
    srt_path = DATA_ROOT / "transcripts" / "demo.srt"
    srt_path.parent.mkdir(parents=True, exist_ok=True)
    srt_path.write_text("1\n00:00:00,000 --> 00:00:01,000\nTeste\n", encoding="utf-8")
    recipe["captions"] = {"enabled": True, "burned_srt_path": str(srt_path)}

    filters = render.build_video_filters(recipe, variation_index=1)

    assert f"subtitles='{render.escape_filter_path(str(srt_path.resolve()))}'" in filters


def test_validate_recipe_rejects_burned_caption_outside_allowed_roots() -> None:
    recipe = deepcopy(DEFAULT_RECIPE)
    recipe["captions"] = {"enabled": True, "burned_srt_path": str(DATA_ROOT.parent / "outside.srt")}

    with pytest.raises(ValueError, match="captions.burned_srt_path fora das pastas permitidas"):
        render.validate_recipe(recipe)


def test_validate_recipe_rejects_broll_outside_allowed_roots() -> None:
    recipe = deepcopy(DEFAULT_RECIPE)
    recipe["broll"] = [{"path": str(DATA_ROOT.parent / "outside.mp4"), "start": 0, "end": 1}]

    with pytest.raises(ValueError, match="broll\\[0\\].path fora das pastas permitidas"):
        render.validate_recipe(recipe)


def test_validate_recipe_rejects_music_outside_allowed_roots() -> None:
    recipe = deepcopy(DEFAULT_RECIPE)
    recipe["audio"] = {**recipe["audio"], "music_path": str(DATA_ROOT.parent / "outside.mp3")}

    with pytest.raises(ValueError, match="audio.music_path fora das pastas permitidas"):
        render.validate_recipe(recipe)


def test_build_framed_filter_complex_adds_header_logo_and_video_area(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(render, "ensure_ffmpeg", lambda: None)
    logo_path = DATA_ROOT / "assets" / "logo.png"
    logo_path.parent.mkdir(parents=True, exist_ok=True)
    logo_path.write_bytes(b"fake image")
    recipe = deepcopy(DEFAULT_RECIPE)
    recipe["frame"] = {
        **recipe["frame"],
        "enabled": True,
        "logo_path": str(logo_path),
        "channel_name": "Canal Teste",
        "header_height": 340,
        "divider_height": 8,
        "logo_size": 164,
    }

    complex_filter = render.build_framed_filter_complex(recipe, logo_input_index=1)

    assert "color=c=white:s=1080x1920:r=30" in complex_filter
    assert "drawbox=x=0:y=340:w=1080:h=8" in complex_filter
    assert "overlay=0:348:shortest=1" in complex_filter
    assert "[1:v]scale=164:164" in complex_filter
    assert "Canal Teste" in complex_filter
    assert "null[vout]" in complex_filter


def test_framed_2k_logo_size_is_normalized_for_ffmpeg_padding() -> None:
    recipe = deepcopy(DEFAULT_RECIPE)
    recipe["format"] = {"width": 1440, "height": 2560, "fit": "crop", "fps": 30}
    recipe["frame"] = {**recipe["frame"], "enabled": True, "logo_size": 219}

    layout = render.frame_layout(recipe)

    assert layout["logo_size"] == 218


def test_framed_captions_reserve_safe_zone_for_bottom_text() -> None:
    captions_path = DATA_ROOT / "transcripts" / "safe-zone.srt"
    captions_path.parent.mkdir(parents=True, exist_ok=True)
    captions_path.write_text("1\n00:00:00,000 --> 00:00:01,000\nTeste\n", encoding="utf-8")
    recipe = deepcopy(DEFAULT_RECIPE)
    recipe["frame"] = {**recipe["frame"], "enabled": True}
    recipe["captions"] = {"enabled": True, "burned_srt_path": str(captions_path)}
    recipe["text"] = {**recipe["text"], "bottom": "CTA sem sobreposicao"}

    complex_filter = render.build_framed_filter_complex(recipe)

    assert "y=h-text_h-538" in complex_filter


def test_framed_4k_scales_watermark_geometry() -> None:
    recipe = deepcopy(DEFAULT_RECIPE)
    recipe["format"] = {"width": 2160, "height": 3840, "fit": "crop", "fps": 30}
    recipe["frame"] = {**recipe["frame"], "enabled": True}

    complex_filter = render.build_framed_filter_complex(recipe)

    assert "x=w-text_w-104" in complex_filter
    assert "y=h-text_h-112" in complex_filter
    assert "fontsize=68" in complex_filter


def test_build_ffmpeg_command_supports_broll_overlay(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(render, "ensure_ffmpeg", lambda: None)
    recipe = deepcopy(DEFAULT_RECIPE)
    broll_path = DATA_ROOT / "assets" / "broll.mp4"
    broll_path.parent.mkdir(parents=True, exist_ok=True)
    broll_path.write_bytes(b"fake video")
    recipe["broll"] = [{"path": str(broll_path), "start": 3, "end": 8, "opacity": 0.82, "layout": "cover"}]

    command = render.build_ffmpeg_command(
        input_path=Path("entrada.mp4"),
        output_path=Path("saida.mp4"),
        recipe=recipe,
        variation_index=1,
    )

    assert "-filter_complex" in command
    complex_filter = command[command.index("-filter_complex") + 1]
    assert "overlay=0:0" in complex_filter
    assert "between(t\\,3\\,8)" in complex_filter
    assert "colorchannelmixer=aa=0.82" in complex_filter
    assert "-stream_loop" in command
    assert str(broll_path.resolve()) in command
    assert "[vout]" in command


def test_build_ffmpeg_command_supports_framed_layout_and_music(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(render, "ensure_ffmpeg", lambda: None)
    monkeypatch.setattr("app.services.media.available_video_encoders", lambda: ["libx264"])
    logo_path = DATA_ROOT / "assets" / "logo.png"
    music_path = DATA_ROOT / "assets" / "track.mp3"
    logo_path.parent.mkdir(parents=True, exist_ok=True)
    logo_path.write_bytes(b"fake image")
    music_path.write_bytes(b"fake audio")
    recipe = deepcopy(DEFAULT_RECIPE)
    recipe["frame"] = {
        **recipe["frame"],
        "enabled": True,
        "logo_path": str(logo_path),
        "channel_name": "Canal Teste",
    }
    recipe["audio"] = {
        **recipe["audio"],
        "music_path": str(music_path),
        "music_volume": 0.25,
        "original_volume": 0.9,
    }

    command = render.build_ffmpeg_command(
        input_path=Path("entrada.mp4"),
        output_path=Path("saida.mp4"),
        recipe=recipe,
        variation_index=1,
        input_has_audio=True,
    )

    assert "-loop" in command
    assert str(logo_path.resolve()) in command
    assert str(music_path.resolve()) in command
    assert "-filter_complex" in command
    complex_filter = command[command.index("-filter_complex") + 1]
    assert "Canal Teste" in complex_filter
    assert "amix=inputs=2" in complex_filter
    assert "[aout]" in complex_filter
    assert ["-map", "[vout]"] == command[command.index("-map") : command.index("-map") + 2]
    assert "[aout]" in command
    assert "-shortest" in command


def test_build_ffmpeg_command_contains_export_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(render, "ensure_ffmpeg", lambda: None)

    command = render.build_ffmpeg_command(
        input_path=Path("entrada.mp4"),
        output_path=Path("saida.mp4"),
        recipe=DEFAULT_RECIPE,
        variation_index=1,
    )

    assert command[0] == "ffmpeg"
    assert "-hide_banner" in command
    assert "-nostdin" in command
    assert "-vf" in command
    assert ["-map", "0:v:0"] == command[command.index("-map") : command.index("-map") + 2]
    assert "0:a?" in command
    assert "-sn" in command
    assert "-dn" in command
    assert "libx264" in command
    assert "loudnorm=I=-14:TP=-1.5:LRA=11" in command
    assert "48000" in command
    assert "+faststart" in command
    assert command[-1] == "saida.mp4"


def test_trim_uses_duration_when_start_and_end_are_set(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(render, "ensure_ffmpeg", lambda: None)
    recipe = deepcopy(DEFAULT_RECIPE)
    recipe["trim"] = {"start": 5, "end": 8}
    recipe["format"] = {**recipe["format"], "fps": 30}

    command = render.build_ffmpeg_command(
        input_path=Path("entrada.mp4"),
        output_path=Path("saida.mp4"),
        recipe=recipe,
        variation_index=1,
    )
    filters = command[command.index("-vf") + 1]

    assert "-t" in command
    assert command[command.index("-t") + 1] == "3.0"
    assert "-to" not in command
    assert "fps=30" in filters


def test_render_video_removes_partial_temp_file_on_failure(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(render, "ensure_ffmpeg", lambda: None)

    def fake_run(command: list[str], **_kwargs):
        Path(command[-1]).write_bytes(b"partial")
        return SimpleNamespace(returncode=1, stderr="falhou")

    monkeypatch.setattr(render, "run_ffmpeg_command", fake_run)
    output_path = tmp_path / "job.mp4"

    with pytest.raises(RuntimeError, match="falhou"):
        render.render_video(
            input_path=tmp_path / "entrada.mp4",
            output_path=output_path,
            thumbnail_path=tmp_path / "thumb.jpg",
            recipe=DEFAULT_RECIPE,
        )

    assert not output_path.exists()
    assert not (tmp_path / "job.tmp.mp4").exists()


def test_build_ffmpeg_command_fallback_codec(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(render, "ensure_ffmpeg", lambda: None)
    monkeypatch.setattr("app.services.media.available_video_encoders", lambda: ["libx264"])
    
    recipe = deepcopy(DEFAULT_RECIPE)
    recipe["export"] = {"codec": "h264_nvenc", "preset": "veryfast", "crf": 23}
    
    command = render.build_ffmpeg_command(
        input_path=Path("entrada.mp4"),
        output_path=Path("saida.mp4"),
        recipe=recipe,
        variation_index=1,
    )
    
    assert "libx264" in command
    assert "h264_nvenc" not in command
    assert "-crf" in command


def test_build_ffmpeg_command_nvenc_syntax(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(render, "ensure_ffmpeg", lambda: None)
    monkeypatch.setattr("app.services.media.available_video_encoders", lambda: ["libx264", "h264_nvenc"])
    
    recipe = deepcopy(DEFAULT_RECIPE)
    recipe["export"] = {"codec": "h264_nvenc", "preset": "veryfast", "crf": 18}
    
    command = render.build_ffmpeg_command(
        input_path=Path("entrada.mp4"),
        output_path=Path("saida.mp4"),
        recipe=recipe,
        variation_index=1,
    )
    
    assert "h264_nvenc" in command
    assert "-rc:v" in command
    assert "constqp" in command
    assert "-cq:v" in command
    assert "18" in command
    assert "fast" in command
    assert "veryfast" not in command


def test_build_music_audio_filter_complex_with_fade_in(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(render, "ensure_ffmpeg", lambda: None)
    music_path = DATA_ROOT / "assets" / "trilha_fade.mp3"
    music_path.parent.mkdir(parents=True, exist_ok=True)
    music_path.write_bytes(b"fake music")

    recipe = deepcopy(DEFAULT_RECIPE)
    recipe["audio"] = {
        "preserve": True,
        "music_path": str(music_path),
        "music_volume": 0.25,
        "fade_in": 1.5,
    }

    command = render.build_ffmpeg_command(
        input_path=Path("entrada.mp4"),
        output_path=Path("saida.mp4"),
        recipe=recipe,
        variation_index=1,
        input_has_audio=True,
    )

    complex_filter = command[command.index("-filter_complex") + 1]
    assert "afade=t=in:ss=0:d=1.5" in complex_filter
    assert "volume=0.25" in complex_filter
    assert "amix=inputs=2" in complex_filter

