from __future__ import annotations

import re
from pathlib import Path
from typing import Any

FILLER_WORDS_PT = {"tipo", "assim", "ne", "cara", "entao", "basicamente"}

# Mapeamento semântico de vocabulário para emojis (PT-BR e termos frequentes)
EMOJI_KEYWORDS: dict[str, str] = {
    # Finanças & Lucro
    "dinheiro": "💰", "grana": "💰", "faturamento": "💰", "lucro": "💰",
    "milhoes": "💰", "milhao": "💰", "rico": "🤑", "riqueza": "💰",
    "vendas": "📈", "venda": "📈", "investir": "💵", "investimento": "💵",
    "pix": "💸", "dolar": "💵", "cash": "💰", "preco": "🏷️",
    # Fogo & Viral & Hype
    "fogo": "🔥", "viral": "🔥", "viralizou": "🔥", "estourou": "💥",
    "chama": "🔥", "explodiu": "💥", "quente": "🔥", "insano": "🤯", "brabo": "⚡",
    # Alerta & Cuidado
    "atencao": "⚠️", "cuidado": "⚠️", "alerta": "🚨", "perigo": "🚫",
    "aviso": "⚠️", "erro": "❌", "jamais": "⛔", "nunca": "⛔", "pare": "🛑",
    # Crescimento & Escala
    "foguete": "🚀", "escala": "🚀", "escalar": "🚀", "crescimento": "📈",
    "crescer": "📈", "lancamento": "🚀", "voar": "🚀", "decolou": "🚀",
    # Mente, Ideia & Estratégia
    "ideia": "💡", "insight": "💡", "segredo": "🤫", "dica": "💡",
    "mente": "🧠", "mindset": "🧠", "estrategia": "♟️",
    # Metas, Foco & Conversão
    "meta": "🎯", "objetivo": "🎯", "foco": "🎯", "resultado": "🏆",
    # Tempo & Urgência
    "tempo": "⏱️", "rapido": "⚡", "agora": "⏳", "hoje": "📅",
    "hora": "⏰", "minutos": "⏱️", "segundos": "⏱️", "pressa": "⚡",
    # Vitória & Sucesso
    "vitoria": "🏆", "campeao": "🏆", "trofeu": "🏆", "sucesso": "🌟", "ganhou": "🥇",
    # Espanto & Choque
    "choque": "😱", "chocante": "😱", "absurdo": "🤯", "loucura": "🤯", "surreal": "🛸",
    # Afeto & Conexão
    "amor": "❤️", "coracao": "❤️", "incrivel": "✨", "gratidao": "🙏", "obrigado": "🤝",
}

SAFE_ZONE_PRESETS: dict[str, dict[str, Any]] = {
    "tiktok": {"margin_l": 80, "margin_r": 160, "margin_v": 490, "alignment": 2},
    "reels": {"margin_l": 70, "margin_r": 150, "margin_v": 470, "alignment": 2},
    "shorts": {"margin_l": 80, "margin_r": 160, "margin_v": 510, "alignment": 2},
    "universal": {"margin_l": 80, "margin_r": 160, "margin_v": 490, "alignment": 2},
    "center": {"margin_l": 60, "margin_r": 60, "margin_v": 0, "alignment": 5},
    "top": {"margin_l": 60, "margin_r": 60, "margin_v": 280, "alignment": 8},
}

VIRAL_PRESETS: dict[str, dict[str, Any]] = {
    "hormozi": {
        "font_name": "Montserrat",
        "font_size": 76,
        "primary_color": "&H00FFFFFF",     # Branco inativo
        "highlight_color": "&H0000FFFF",   # Amarelo fluorescente ativo
        "outline_color": "&H00000000",
        "outline_width": 10,
        "shadow_width": 5,
        "uppercase": True,
        "animation": "bounce",             # \fscx120\fscy120 -> 100
        "words_per_chunk": 3,
    },
    "mrbeast": {
        "font_name": "Komika Axis",
        "font_size": 74,
        "primary_color": "&H00FFFFFF",
        "highlight_color": "&H0012D6FF",   # Amarelo/Dourado MrBeast
        "outline_color": "&H00000000",
        "outline_width": 8,
        "shadow_width": 4,
        "uppercase": True,
        "animation": "tilt_bounce",        # \frz-2.5 + bounce
        "words_per_chunk": 3,
    },
    "minimalist_clean": {
        "font_name": "Inter",
        "font_size": 56,
        "primary_color": "&H30E0E0E0",     # Off-white suave com leve alpha
        "highlight_color": "&H00FFFFFF",   # Branco puro vívido
        "outline_color": "&H80101010",
        "outline_width": 2,
        "shadow_width": 1,
        "uppercase": False,
        "animation": "fade",
        "words_per_chunk": 4,
    },
    "cyberpunk_neon": {
        "font_name": "Orbitron",
        "font_size": 68,
        "primary_color": "&H00FFFFFF",
        "highlight_color": "&H00FFFF00",   # Ciano Elétrico
        "outline_color": "&H00FF00FF",     # Magenta Neon (Glow)
        "outline_width": 6,
        "shadow_width": 0,
        "uppercase": True,
        "animation": "glow_pulse",
        "words_per_chunk": 2,
    },
}

KARAOKE_THEMES: dict[str, dict] = {
    "hormozi": {
        "font_name": "Montserrat",
        "font_size": 72,
        "primary_color": "&H00FFFFFF",
        "highlight_color": "&H0000E6FF",
        "outline_color": "&H00000000",
        "outline_width": 5,
        "shadow_width": 3,
        "margin_v": 460,
    },
    "neon_cyan": {
        "font_name": "Arial",
        "font_size": 68,
        "primary_color": "&H00FFFFFF",
        "highlight_color": "&H00FFFF00",
        "outline_color": "&H00802000",
        "outline_width": 4,
        "shadow_width": 4,
        "margin_v": 460,
    },
    "minimal_white": {
        "font_name": "Helvetica",
        "font_size": 60,
        "primary_color": "&H00FFFFFF",
        "highlight_color": "&H00D0D0D0",
        "outline_color": "&H00202020",
        "outline_width": 2,
        "shadow_width": 1,
        "margin_v": 460,
    },
    "bold_red": {
        "font_name": "Impact",
        "font_size": 72,
        "primary_color": "&H00FFFFFF",
        "highlight_color": "&H000000FF",
        "outline_color": "&H00000000",
        "outline_width": 5,
        "shadow_width": 2,
        "margin_v": 460,
    },
}


def format_srt_time(seconds: float) -> str:
    millis = int(round(seconds * 1000))
    hours, remainder = divmod(millis, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    secs, millis = divmod(remainder, 1000)
    return f"{hours:02}:{minutes:02}:{secs:02},{millis:03}"


def format_vtt_time(seconds: float) -> str:
    return format_srt_time(seconds).replace(",", ".")


def format_ass_time(seconds: float) -> str:
    cs = max(0, int(round(seconds * 100)))
    hours, remainder = divmod(cs, 360000)
    minutes, remainder = divmod(remainder, 6000)
    secs, centis = divmod(remainder, 100)
    return f"{hours:d}:{minutes:02d}:{secs:02d}.{centis:02d}"


def build_srt(segments: list[dict]) -> str:
    blocks = []
    for index, segment in enumerate(segments, start=1):
        blocks.append(
            f"{index}\n{format_srt_time(float(segment['start']))} --> {format_srt_time(float(segment['end']))}\n{segment['text']}"
        )
    return "\n\n".join(blocks) + "\n"


def build_vtt(segments: list[dict]) -> str:
    blocks = ["WEBVTT", ""]
    for segment in segments:
        blocks.append(
            f"{format_vtt_time(float(segment['start']))} --> {format_vtt_time(float(segment['end']))}\n{segment['text']}"
        )
    return "\n\n".join(blocks) + "\n"


def detect_filler_words(text: str) -> list[str]:
    words = [word.strip(".,!?;:").lower() for word in text.split()]
    return sorted({word for word in words if word in FILLER_WORDS_PT})


def clean_transcript_segments(segments: list[dict]) -> list[dict]:
    cleaned = []
    for seg in segments:
        text = seg.get("text", "")
        words = text.split()
        filtered_words = [w for w in words if w.lower().strip(".,!?") not in FILLER_WORDS_PT]
        clean_text = " ".join(filtered_words).strip()
        if clean_text:
            cleaned.append({**seg, "text": clean_text})
    return cleaned or segments


def normalize_token(text: str) -> str:
    cleaned = re.sub(r"[^\w\s]", "", text).lower().strip()
    replacements = {
        "ã": "a", "á": "a", "à": "a", "â": "a",
        "é": "e", "ê": "e", "í": "i",
        "ó": "o", "ô": "o", "õ": "o", "ú": "u", "ç": "c"
    }
    for orig, rep in replacements.items():
        cleaned = cleaned.replace(orig, rep)
    return cleaned


def chunk_words(
    words: list[dict[str, Any]],
    max_words: int = 3,
    max_chars: int = 24,
    silence_gap: float = 0.45,
) -> list[list[dict[str, Any]]]:
    if not words:
        return []

    chunks: list[list[dict[str, Any]]] = []
    current_chunk: list[dict[str, Any]] = []
    current_char_count = 0

    for w in words:
        word_text = str(w.get("word", "")).strip()
        if not word_text:
            continue

        is_new_chunk = False
        if current_chunk:
            prev_end = float(current_chunk[-1].get("end", 0))
            curr_start = float(w.get("start", prev_end))
            if (curr_start - prev_end) >= silence_gap:
                is_new_chunk = True
            elif len(current_chunk) >= max_words:
                is_new_chunk = True
            elif (current_char_count + len(word_text) + 1) > max_chars:
                is_new_chunk = True
            elif any(current_chunk[-1].get("word", "").endswith(p) for p in [".", "?", "!", ":"]):
                is_new_chunk = True

        if is_new_chunk and current_chunk:
            chunks.append(current_chunk)
            current_chunk = []
            current_char_count = 0

        current_chunk.append(w)
        current_char_count += len(word_text) + 1

    if current_chunk:
        chunks.append(current_chunk)

    return chunks


def build_ass_dynamic(
    segments: list[dict[str, Any]],
    words: list[dict[str, Any]] | None = None,
    *,
    preset: str = "hormozi",
    safe_zone: str = "universal",
    enable_emojis: bool = True,
    emoji_font: str = "Segoe UI Emoji",
    resolution: tuple[int, int] = (1080, 1920),
    custom_overrides: dict[str, Any] | None = None,
) -> str:
    cfg = {**VIRAL_PRESETS.get(preset, VIRAL_PRESETS["hormozi"]), **(custom_overrides or {})}
    sz = SAFE_ZONE_PRESETS.get(safe_zone, SAFE_ZONE_PRESETS["universal"])

    res_x, res_y = resolution
    f_name = cfg["font_name"]
    f_size = cfg["font_size"]
    p_color = cfg["primary_color"]
    h_color = cfg["highlight_color"]
    o_color = cfg["outline_color"]
    o_width = cfg["outline_width"]
    s_width = cfg["shadow_width"]
    align = sz["alignment"]
    margin_l = sz["margin_l"]
    margin_r = sz["margin_r"]
    margin_v = sz["margin_v"]

    header = [
        "[Script Info]",
        "ScriptType: v4.00+",
        f"PlayResX: {res_x}",
        f"PlayResY: {res_y}",
        "ScaledBorderAndShadow: yes",
        "",
        "[V4+ Styles]",
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
        f"Style: Default,{f_name},{f_size},{p_color},{h_color},{o_color},&H00000000,-1,0,0,0,100,100,0,0,1,{o_width},{s_width},{align},{margin_l},{margin_r},{margin_v},1",
        "",
        "[Events]",
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
    ]

    all_words = words or []
    if not all_words:
        for seg in segments:
            seg_text = str(seg.get("text", "")).strip()
            if not seg_text:
                continue
            seg_words = seg_text.split()
            seg_start = float(seg.get("start", 0))
            seg_end = float(seg.get("end", seg_start + 1.0))
            word_dur = max(0.1, (seg_end - seg_start) / max(1, len(seg_words)))
            for i, sw in enumerate(seg_words):
                w_s = seg_start + i * word_dur
                w_e = w_s + word_dur
                all_words.append({"word": sw, "start": w_s, "end": w_e})

    chunks = chunk_words(all_words, max_words=cfg.get("words_per_chunk", 3))
    events: list[str] = []
    last_emoji_time = -10.0

    for chunk in chunks:
        if not chunk:
            continue

        chunk_emoji = ""
        if enable_emojis:
            for w in chunk:
                token = normalize_token(w.get("word", ""))
                if token in EMOJI_KEYWORDS:
                    w_start = float(w.get("start", 0))
                    if (w_start - last_emoji_time) >= 1.8:
                        chunk_emoji = EMOJI_KEYWORDS[token]
                        last_emoji_time = w_start
                        break

        for active_idx, active_word in enumerate(chunk):
            w_start = float(active_word.get("start", 0))
            w_end = float(active_word.get("end", w_start + 0.3))

            if w_end <= w_start:
                w_end = w_start + 0.25

            start_str = format_ass_time(w_start)
            end_str = format_ass_time(w_end)

            formatted_words = []
            for idx, w in enumerate(chunk):
                raw_text = str(w.get("word", "")).strip()
                display_text = raw_text.upper() if cfg.get("uppercase") else raw_text

                if idx == active_idx:
                    anim_type = cfg.get("animation", "bounce")
                    if anim_type == "tilt_bounce":
                        anim_tag = f"{{\\c{h_color}&\\frz-2.5\\fscx118\\fscy118\\t(0,80,\\fscx100\\fscy100)}}"
                    elif anim_type == "glow_pulse":
                        anim_tag = f"{{\\c{h_color}&\\blur6\\fscx112\\fscy112\\t(0,90,\\blur3\\fscx100\\fscy100)}}"
                    elif anim_type == "fade":
                        anim_tag = f"{{\\c{h_color}&\\alpha&H00&}}"
                    else:
                        anim_tag = f"{{\\c{h_color}&\\fscx120\\fscy120\\t(0,80,\\fscx100\\fscy100)}}"

                    if chunk_emoji and (idx == len(chunk) - 1 or normalize_token(raw_text) in EMOJI_KEYWORDS):
                        emoji_str = f" {{\\fn{emoji_font}}}{chunk_emoji}{{\\fn{f_name}}}"
                        formatted_words.append(f"{anim_tag}{display_text}{emoji_str}{{\\r}}")
                    else:
                        formatted_words.append(f"{anim_tag}{display_text}{{\\r}}")
                else:
                    formatted_words.append(display_text)

            line_text = " ".join(formatted_words)
            events.append(f"Dialogue: 0,{start_str},{end_str},Default,,0,0,0,,{line_text}")

    return "\n".join(header + events) + "\n"


def build_ass_karaoke(
    segments: list[dict],
    words: list[dict] | None = None,
    *,
    theme: str | None = None,
    font_name: str | None = None,
    font_size: int | None = None,
    primary_color: str | None = None,
    highlight_color: str | None = None,
    outline_color: str | None = None,
    outline_width: int | None = None,
    shadow_width: int | None = None,
    margin_v: int | None = None,
) -> str:
    chosen_theme = KARAOKE_THEMES.get(theme or "hormozi", KARAOKE_THEMES["hormozi"])

    f_name = font_name or chosen_theme["font_name"]
    f_size = font_size or chosen_theme["font_size"]
    p_color = primary_color or chosen_theme["primary_color"]
    h_color = highlight_color or chosen_theme["highlight_color"]
    o_color = outline_color or chosen_theme["outline_color"]
    o_width = outline_width if outline_width is not None else chosen_theme["outline_width"]
    s_width = shadow_width if shadow_width is not None else chosen_theme["shadow_width"]
    m_v = margin_v if margin_v is not None else chosen_theme["margin_v"]

    header = [
        "[Script Info]",
        "ScriptType: v4.00+",
        "PlayResX: 1080",
        "PlayResY: 1920",
        "ScaledBorderAndShadow: yes",
        "",
        "[V4+ Styles]",
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
        f"Style: Karaoke,{f_name},{f_size},{p_color},{h_color},{o_color},&H80000000,-1,0,0,0,100,100,0,0,1,{o_width},{s_width},2,40,40,{m_v},1",
        "",
        "[Events]",
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
    ]

    all_words = words or []
    events = []

    for segment in segments:
        seg_start = float(segment.get("start", 0))
        seg_end = float(segment.get("end", 0))
        seg_text = str(segment.get("text", "")).strip()
        if not seg_text:
            continue

        start_str = format_ass_time(seg_start)
        end_str = format_ass_time(seg_end)

        # Match words within this segment's time boundary
        seg_words = [
            w for w in all_words
            if float(w.get("start", 0)) >= seg_start - 0.05 and float(w.get("end", 0)) <= seg_end + 0.05
        ]

        if seg_words:
            karaoke_parts = []
            for w in seg_words:
                w_start = float(w.get("start", seg_start))
                w_end = float(w.get("end", w_start + 0.3))
                duration_cs = max(1, int(round((w_end - w_start) * 100)))
                word_clean = str(w.get("word", "")).strip()
                karaoke_parts.append(f"{{\\k{duration_cs}}}{word_clean}")
            dialogue_text = " ".join(karaoke_parts)
        else:
            text_tokens = seg_text.split()
            if text_tokens:
                total_duration = max(0.1, seg_end - seg_start)
                cs_per_word = max(1, int(round((total_duration * 100) / len(text_tokens))))
                dialogue_text = " ".join(f"{{\\k{cs_per_word}}}{token}" for token in text_tokens)
            else:
                dialogue_text = seg_text

        events.append(f"Dialogue: 0,{start_str},{end_str},Karaoke,,0,0,0,,{dialogue_text}")

    return "\n".join(header + events) + "\n"


def parse_timestamp_seconds(ts: str) -> float:
    ts = ts.strip().replace(",", ".")
    parts = ts.split(":")
    if len(parts) == 3:
        h, m, s = parts
        return float(h) * 3600 + float(m) * 60 + float(s)
    elif len(parts) == 2:
        m, s = parts
        return float(m) * 60 + float(s)
    return float(ts)


def parse_subtitles_text(content: str) -> list[dict[str, Any]]:
    text = content.replace("\r\n", "\n").replace("\r", "\n")
    timing_pattern = re.compile(
        r"((?:\d{1,2}:)?\d{2}:\d{2}[,\.]\d{3})\s*-->\s*((?:\d{1,2}:)?\d{2}:\d{2}[,\.]\d{3})"
    )

    blocks = re.split(r"\n\s*\n", text.strip())
    segments: list[dict[str, Any]] = []

    for block in blocks:
        lines = [line.strip() for line in block.split("\n") if line.strip()]
        if not lines:
            continue

        match = None
        timing_idx = -1
        for idx, line in enumerate(lines):
            m = timing_pattern.search(line)
            if m:
                match = m
                timing_idx = idx
                break

        if not match:
            continue

        start_sec = parse_timestamp_seconds(match.group(1))
        end_sec = parse_timestamp_seconds(match.group(2))

        text_lines = lines[timing_idx + 1:]
        clean_text = " ".join(text_lines)
        clean_text = re.sub(r"<[^>]+>", "", clean_text).strip()

        if clean_text:
            segments.append({
                "start": start_sec,
                "end": end_sec,
                "text": clean_text,
            })

    return segments


def parse_subtitles_file(file_path: Path | str) -> list[dict[str, Any]]:
    path = Path(file_path)
    if not path.exists():
        return []
    content = path.read_text(encoding="utf-8", errors="replace")
    return parse_subtitles_text(content)


def convert_srt_to_styled_ass(
    sub_path: Path | str,
    *,
    style: str = "hormozi",
    safe_zone: str = "universal",
    resolution: tuple[int, int] = (1080, 1920),
) -> str:
    segments = parse_subtitles_file(sub_path)
    if not segments:
        return ""
    if style in VIRAL_PRESETS:
        return build_ass_dynamic(
            segments,
            preset=style,
            safe_zone=safe_zone,
            resolution=resolution,
        )
    return build_ass_karaoke(
        segments,
        theme=style if style in KARAOKE_THEMES else "hormozi",
    )


