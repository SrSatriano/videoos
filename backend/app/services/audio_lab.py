import os
import shutil
import subprocess
from pathlib import Path
from typing import Any

from ..config import DATA_DIR
from .media import ensure_ffmpeg


AUDIO_MOODS: dict[str, dict[str, Any]] = {
    "energetic": {
        "label": "Energético",
        "bpm_range": (120, 138),
        "color": "#ff5722",
        "description": "Synthwave, Upbeat EDM, Trap Drums, Bassline pulsante para retenção e dinamismo.",
        "keywords": ["energia", "fogo", "dinamico", "hype", "treino", "ritmo", "upbeat", "rapido", "viral"],
    },
    "inspiring": {
        "label": "Inspirador",
        "bpm_range": (85, 105),
        "color": "#9c27b0",
        "description": "Piano acústico, cordas crescentes, ambient cinematic para storytelling e superação.",
        "keywords": ["historia", "emocao", "superacao", "sucesso", "reflexao", "aula", "futuro", "jornada"],
    },
    "mysterious": {
        "label": "Misterioso",
        "bpm_range": (90, 110),
        "color": "#3f51b5",
        "description": "Drones graves, synth analógico, tensão e batida minimalista para curiosidades e segredos.",
        "keywords": ["segredo", "misterio", "curiosidade", "conspiracao", "crime", "tensao", "fato"],
    },
    "lofi": {
        "label": "Lo-Fi",
        "bpm_range": (75, 90),
        "color": "#00b0ff",
        "description": "Chillhop, vinyl crackle, rhodes vintage e batida relaxada para tutoriais e tecnologia.",
        "keywords": ["tech", "tutorial", "programacao", "estudo", "relax", "rotina", "dica", "codigo"],
    },
    "corporate": {
        "label": "Corporativo",
        "bpm_range": (110, 125),
        "color": "#00e676",
        "description": "Acoustic guitar leve, estalos, marimba e clareza comercial para negócios e SaaS.",
        "keywords": ["negocios", "vendas", "empresa", "dinheiro", "marketing", "financas", "b2b", "lucro"],
    },
}


def classify_mood_from_prompt(prompt: str) -> str:
    lowered = prompt.lower()
    for mood_key, mood_data in AUDIO_MOODS.items():
        for kw in mood_data["keywords"]:
            if kw in lowered:
                return mood_key
    return "energetic" if any(w in lowered for w in ["rapido", "corte", "short"]) else "lofi"


def music_brief_from_prompt(prompt: str) -> dict:
    lowered = prompt.lower()
    if "tech" in lowered or "futur" in lowered:
        mood = "tech"
    elif "creator" in lowered:
        mood = "creator"
    else:
        mood = classify_mood_from_prompt(prompt)

    mood_info = AUDIO_MOODS.get(mood, AUDIO_MOODS["lofi"] if mood == "tech" else AUDIO_MOODS["corporate"])
    bpm = 120 if mood == "tech" else (96 if mood == "creator" else (mood_info["bpm_range"][0] + mood_info["bpm_range"][1]) // 2)
    return {
        "mood": mood,
        "mood_label": mood_info.get("label", mood),
        "description": prompt.strip(),
        "bpm": bpm,
        "usage": "background",
        "color": mood_info.get("color", "#ff5722"),
        "rights_note": "Use apenas trilhas proprias, licenciadas ou geradas com direito comercial.",
    }



def build_vocal_clarity_filter(config: dict | None = None) -> str:
    """Retorna cadeia de filtros DSP para máxima clareza e presença da voz."""
    cfg = config or {}
    highpass_hz = int(cfg.get("highpass_hz", 80))
    presence_db = float(cfg.get("presence_boost_db", 3.2))
    return (
        f"highpass=f={highpass_hz}:poles=2,"
        "equalizer=f=320:t=q:w=1.0:g=-2.2,"
        f"equalizer=f=3200:t=q:w=1.3:g={presence_db},"
        "highshelf=f=8500:g=2.0,"
        "acompressor=threshold=-18dB:ratio=3.5:attack=15:release=120:makeup=2.5:knee=3"
    )


def build_music_duck_filter(
    video_has_voice: bool,
    *,
    strength: float = 0.65,
    threshold: float | None = None,
    ratio: float | None = None,
) -> str:
    """Gera filtro de sidechain ducking calibrado para manter a voz audível."""
    if not video_has_voice or strength <= 0.05:
        vol = max(0.05, min(0.4, 0.25 * (1.0 - strength * 0.5)))
        return f"[1:a]volume={vol:.2f}[musicduck]"

    th = threshold if threshold is not None else (0.09 - strength * 0.05)
    rt = ratio if ratio is not None else (3.0 + strength * 6.0)
    att = 30
    rel = 450
    return (
        f"[1:a][0:a]sidechaincompress=threshold={th:.3f}:ratio={rt:.1f}:attack={att}:release={rel}:knee=3[musicduck]"
    )


build_dynamic_ducking_filter = build_music_duck_filter



def demucs_status() -> dict[str, Any]:
    demucs_bin = shutil.which("demucs")
    return {
        "demucs_available": bool(demucs_bin),
        "demucs_path": demucs_bin,
        "features": ["vocals", "drums", "bass", "other"] if demucs_bin else ["vocals_dsp", "instrumental_dsp"],
        "dsp_available": True,
    }


def separate_audio_stems(audio_path: Path | str, output_dir: Path | str | None = None) -> dict[str, Any]:
    """Separates audio into vocals and instrumental tracks using Demucs or FFmpeg DSP fallback."""
    ensure_ffmpeg()
    src = Path(audio_path)
    if not src.exists():
        raise FileNotFoundError(f"Arquivo de audio nao encontrado: {src}")

    target_dir = Path(output_dir) if output_dir else DATA_DIR / "audio_stems" / src.stem
    target_dir.mkdir(parents=True, exist_ok=True)

    vocals_file = target_dir / "vocals.wav"
    instrumental_file = target_dir / "instrumental.wav"

    demucs_bin = shutil.which("demucs")
    if demucs_bin:
        cmd = ["demucs", "--two-stems=vocals", "-o", str(target_dir), str(src)]
        try:
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
            if res.returncode == 0:
                # Demucs puts files in target_dir / "htdemucs" / src.stem / (vocals.wav, no_vocals.wav)
                ht_vocals = list(target_dir.rglob("vocals.wav"))
                ht_no_vocals = list(target_dir.rglob("no_vocals.wav"))
                if ht_vocals and ht_vocals[0] != vocals_file:
                    shutil.move(str(ht_vocals[0]), str(vocals_file))
                if ht_no_vocals and ht_no_vocals[0] != instrumental_file:
                    shutil.move(str(ht_no_vocals[0]), str(instrumental_file))

                if vocals_file.exists() and instrumental_file.exists():
                    return {
                        "status": "success",
                        "engine": "demucs",
                        "output_dir": str(target_dir),
                        "vocals_path": str(vocals_file),
                        "instrumental_path": str(instrumental_file),
                    }
        except Exception:
            pass

    # DSP Fallback using FFmpeg
    # Vocals: Voice rumble filter + presence boost (intelligibility without telephone lowpass)
    cmd_vocals = [
        "ffmpeg",
        "-y",
        "-i",
        str(src),
        "-af",
        "highpass=f=120,equalizer=f=300:t=q:w=1.2:g=-4,equalizer=f=3200:t=q:w=1.0:g=3,volume=1.1",
        str(vocals_file),
    ]
    # Instrumental: Ensure stereo layout before stereotools center channel attenuation
    cmd_inst = [
        "ffmpeg",
        "-y",
        "-i",
        str(src),
        "-af",
        "aformat=channel_layouts=stereo,stereotools=mlev=0.15",
        str(instrumental_file),
    ]

    subprocess.run(cmd_vocals, capture_output=True, check=False)
    subprocess.run(cmd_inst, capture_output=True, check=False)

    return {
        "status": "success",
        "engine": "ffmpeg_dsp",
        "output_dir": str(target_dir),
        "vocals_path": str(vocals_file) if vocals_file.exists() else None,
        "instrumental_path": str(instrumental_file) if instrumental_file.exists() else None,
    }

