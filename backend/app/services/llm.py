from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any

from pydantic import BaseModel, Field, ValidationError

from ..config import GEMINI_MODEL, GOOGLE_API_KEY, OLLAMA_MODEL, OLLAMA_URL, WHISPER_MODEL


class AgentItem(BaseModel):
    title: str = Field(..., description="Titulo acionavel do item ou ideia")
    description: str = Field(..., description="Descricao detalhada do angulo")
    score: float = Field(default=0.7, ge=0.0, le=1.0, description="Score de relevancia")


class AgentRunResult(BaseModel):
    agent: str = Field(..., description="Nome do agente gerador")
    items: list[AgentItem] = Field(default_factory=list, description="Lista de ideias ou itens estruturados")


class MinedClipItem(BaseModel):
    start_seconds: float = Field(..., description="Timestamp de inicio em segundos")
    end_seconds: float = Field(..., description="Timestamp de termino em segundos")
    duration: float = Field(default=0.0, description="Duracao em segundos")
    viral_score: int = Field(default=85, ge=0, le=100, description="Pontuacao de viralizacao 0-100%")
    hook: str = Field(..., description="Primeira frase falada nos primeiros segundos")
    category: str = Field(default="Dica Pratica", description="Categoria do clipe")
    suggested_title: str = Field(..., description="Titulo de alto impacto")
    suggested_copy: str = Field(default="", description="Legenda pronta para postar")
    suggested_hashtags: list[str] = Field(default_factory=list, description="Lista de hashtags")
    reason: str = Field(default="", description="Justificativa da viralizacao")


class MinedClipsResult(BaseModel):
    clips: list[MinedClipItem] = Field(default_factory=list, description="Lista de cortes virais minerados")


class ViralHookItem(BaseModel):
    formula: str = Field(..., description="Formula viral: curiosidade, choque, beneficio_imediato, quebra_crenca")
    headline: str = Field(..., description="Gancho textual de alto CTR para topo do video")
    spoken_hook: str = Field(..., description="Primeira frase falada nos primeiros 3 segundos")
    retention_score: int = Field(default=85, ge=0, le=100, description="Score preditivo de retencao 0-100")


class ViralHooksResult(BaseModel):
    topic: str = Field(..., description="Tema ou assunto analisado")
    hooks: list[ViralHookItem] = Field(default_factory=list, description="Lista das 4 formulas de ganchos virais")


class ScriptBlockItem(BaseModel):
    block_name: str = Field(..., description="Nome do bloco: hook, context, solution, practical, cta")
    timing: str = Field(..., description="Janela de tempo estimada, ex: 0-5s")
    spoken_text: str = Field(..., description="Texto da fala ou narracao")
    visual_direction: str = Field(..., description="Orientacao visual para corte, b-roll ou expressao")
    visual_prompt: str = Field(default="", description="Prompt detalhado para gerador de imagens ou B-roll")
    keyword: str = Field(default="", description="Palavra-chave de busca de midia")


class ScriptToVideoResult(BaseModel):
    title: str = Field(..., description="Titulo do roteiro")
    target_duration: str = Field(default="45s", description="Duracao alvo estimada")
    word_count: int = Field(default=120, description="Contagem total de palavras")
    full_narration: str = Field(default="", description="Texto completo consolidado para TTS")
    blocks: list[ScriptBlockItem] = Field(default_factory=list, description="Os 5 blocos canonicos do roteiro")
    suggested_hashtags: list[str] = Field(default_factory=list, description="Hashtags sugeridas")
    suggested_audio_mood: str = Field(default="energetic_lofi", description="Estilo de trilha sonora")



def ollama_candidate_urls(endpoint: str) -> list[str]:
    path = "/" + endpoint.lstrip("/")
    bases = [
        OLLAMA_URL.rstrip("/"),
        "http://host.docker.internal:11434",
        "http://127.0.0.1:11434",
    ]
    urls: list[str] = []
    for base in bases:
        url = base + path
        if url not in urls:
            urls.append(url)
    return urls


def schema_for_agent_run() -> dict[str, Any]:
    return AgentRunResult.model_json_schema()



def ollama_status() -> dict[str, Any]:
    tried_urls = ollama_candidate_urls("/api/tags")
    for url in tried_urls:
        request = urllib.request.Request(url, method="GET")
        try:
            with urllib.request.urlopen(request, timeout=3) as response:
                data = json.loads(response.read().decode("utf-8"))
            return {
                "available": True,
                "models": [model.get("name") for model in data.get("models", []) if model.get("name")],
                "url": url,
                "tried_urls": tried_urls,
            }
        except (OSError, urllib.error.URLError, TimeoutError):
            continue
    return {"available": False, "models": [], "url": tried_urls[0], "tried_urls": tried_urls}


def fallback_structured_response(agent: str, brief: str, schema: dict[str, Any] | None = None) -> dict[str, Any]:
    cleaned = " ".join(brief.split())[:120] or "conteudo curto"
    return {
        "agent": agent,
        "items": [
            {"title": f"Ideia {index}", "description": f"{cleaned} - angulo {index}", "score": 0.7}
            for index in range(1, 4)
        ],
    }


def run_gemini_structured(
    system: str,
    user: str,
    schema: dict[str, Any] | None = None,
    model: str | None = None,
    api_key: str | None = None,
) -> dict[str, Any]:
    """Executa requisições estruturadas contra a API do Google Gemini via REST JSON nativo."""
    key = (api_key or GOOGLE_API_KEY).strip()
    if not key:
        raise ValueError("Chave de API do Google (GOOGLE_API_KEY) nao esta configurada.")
    m = model or GEMINI_MODEL or "gemini-2.0-flash"
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{m}:generateContent?key={key}"

    prompt = f"INSTRUCOES DO SISTEMA:\n{system}\n\nREQUISICAO DO USUARIO:\n{user}"
    if schema:
        prompt += f"\n\nRetorne EXCLUSIVAMENTE um objeto JSON valido compativel com o schema:\n{json.dumps(schema, ensure_ascii=False)}"

    payload = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.2,
            "responseMimeType": "application/json",
        },
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read().decode("utf-8"))

    candidates = data.get("candidates", [])
    if not candidates:
        raise RuntimeError("Google Gemini nao retornou candidatos validos.")
    raw_content = candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "").strip()
    if raw_content.startswith("```"):
        lines = raw_content.splitlines()
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        raw_content = "\n".join(lines).strip()
    return json.loads(raw_content)


def test_google_connection(api_key: str | None = None, model: str | None = None) -> dict[str, Any]:
    key = (api_key or GOOGLE_API_KEY).strip()
    if not key:
        return {"available": False, "error": "Nenhuma chave informada ou configurada.", "provider": "google_gemini"}
    m = model or GEMINI_MODEL or "gemini-2.0-flash"
    try:
        res = run_gemini_structured(
            system="Voce e um validador de conexao de API.",
            user="Responda com status ok.",
            schema={"type": "object", "properties": {"status": {"type": "string"}}, "required": ["status"]},
            api_key=key,
            model=m,
        )
        return {"available": True, "model": m, "provider": "google_gemini", "response": res}
    except Exception as exc:
        return {"available": False, "error": str(exc), "provider": "google_gemini"}


def get_ai_providers_status() -> dict[str, Any]:
    google_configured = bool(GOOGLE_API_KEY)
    masked_key = f"{GOOGLE_API_KEY[:6]}...{GOOGLE_API_KEY[-4:]}" if len(GOOGLE_API_KEY) > 10 else ("Configurada" if GOOGLE_API_KEY else "Nao configurada")
    return {
        "google": {
            "configured": google_configured,
            "model": GEMINI_MODEL or "gemini-2.0-flash",
            "masked_key": masked_key,
        },
        "ollama": ollama_status(),
        "tts": {
            "available": True,
            "engine": "Edge-TTS (Neural)",
            "default_voice": "pt-BR-AntonioNeural",
            "voices_count": 5,
        },
        "whisper": {
            "available": True,
            "model": WHISPER_MODEL,
        },
    }


def run_ollama_structured(model: str, system: str, user: str, schema: dict[str, Any]) -> dict[str, Any]:
    payload = {
        "model": model,
        "stream": False,
        "format": schema,
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
        "options": {"temperature": 0.2},
    }
    last_error: Exception | None = None
    for url in ollama_candidate_urls("/api/chat"):
        request = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=45) as response:
                data = json.loads(response.read().decode("utf-8"))
            raw_content = str(data["message"]["content"]).strip()
            if raw_content.startswith("```"):
                lines = raw_content.splitlines()
                if lines[0].startswith("```"):
                    lines = lines[1:]
                if lines and lines[-1].strip() == "```":
                    lines = lines[:-1]
                raw_content = "\n".join(lines).strip()
            parsed = json.loads(raw_content)
            validated = AgentRunResult.model_validate(parsed)
            return validated.model_dump()
        except (OSError, urllib.error.URLError, TimeoutError, KeyError, json.JSONDecodeError, ValidationError) as exc:
            last_error = exc
    if last_error:
        raise last_error
    raise RuntimeError("Nenhuma URL Ollama configurada.")


def run_agent_structured(agent: str, role: str, brief: str, model: str | None = None) -> dict[str, Any]:
    schema = schema_for_agent_run()
    # 1. Tentar Google Gemini se configurado
    if GOOGLE_API_KEY:
        try:
            parsed = run_gemini_structured(role, brief, schema, model=model)
            validated = AgentRunResult.model_validate(parsed)
            return validated.model_dump()
        except Exception:
            pass

    # 2. Fallback para Ollama
    selected_model = model or OLLAMA_MODEL or "llama3.1"
    try:
        return run_ollama_structured(selected_model, role, brief, schema)
    except (OSError, urllib.error.URLError, TimeoutError, KeyError, json.JSONDecodeError, ValidationError):
        return fallback_structured_response(agent, brief, schema)


def analyze_viral_clips_with_ai(
    transcript_text: str,
    segments: list[dict],
    min_seconds: int = 15,
    max_seconds: int = 60,
    target_count: int = 5,
) -> list[dict[str, Any]]:
    """Minera os melhores momentos de um video e calcula Viral Score (0-100%) estilo Opus Clip/Vizard."""
    schema = MinedClipsResult.model_json_schema()
    system_prompt = (
        "Voce e um editor senior de redes sociais e especialista em algoritmos virais do TikTok, Instagram Reels e YouTube Shorts. "
        f"Analise a transcricao e identifique os {target_count} melhores cortes virais que possuem alto potencial de retencao. "
        f"Cada corte deve ter duracao entre {min_seconds}s e {max_seconds}s. "
        "Para cada corte, avalie a forca do gancho nos primeiros 3 segundos, o ritmo da conversa e o climax. "
        "Atribua um viral_score realista de 0 a 100 baseado na capacidade de reter a audiencia."
    )
    user_prompt = f"Transcricao com minutagem e contexto:\n{transcript_text[:12000]}"

    if GOOGLE_API_KEY:
        try:
            parsed = run_gemini_structured(system_prompt, user_prompt, schema)
            validated = MinedClipsResult.model_validate(parsed)
            if validated.clips:
                results = []
                for clip in validated.clips:
                    item = clip.model_dump()
                    item["duration"] = round(item["end_seconds"] - item["start_seconds"], 2)
                    results.append(item)
                return results
        except Exception:
            pass

    # Heuristic Fallback usando split_transcript_into_candidates
    from .clip_analysis import split_transcript_into_candidates
    candidates = split_transcript_into_candidates(segments, min_seconds, max_seconds)
    mined: list[dict[str, Any]] = []
    for cand in candidates[:target_count]:
        score_val = int(cand["score"] * 100)
        dur = round(cand["end_seconds"] - cand["start_seconds"], 2)
        hook_text = cand.get("hook", "")
        cat = "Dica Pratica"
        if any(w in hook_text.lower() for w in ("erro", "cuidado", "perigo", "perdendo")):
            cat = "Alerta / Choque"
        elif any(w in hook_text.lower() for w in ("segredo", "ninguem conta", "revelado")):
            cat = "Revelacao"
        elif any(w in hook_text.lower() for w in ("como", "passo a passo", "tutorial")):
            cat = "Dica Pratica"
        else:
            cat = "Curiosidade"

        mined.append({
            "start_seconds": cand["start_seconds"],
            "end_seconds": cand["end_seconds"],
            "duration": dur,
            "viral_score": score_val,
            "hook": hook_text[:120],
            "category": cat,
            "suggested_title": f"O que voce precisa saber sobre {hook_text[:35]}...",
            "suggested_copy": f"Voce concorda com isso? Assista ate o final e me conte nos comentarios!\n\n#viral #cortes #reels #dicas",
            "suggested_hashtags": ["#viral", "#cortesvirais", "#reelsbrasil", "#tiktokbrasil", "#dicas"],
            "reason": cand.get("reason", "Alta densidade de fala e retencao de palavras-chave."),
        })
    return mined


def generate_viral_hooks(topic: str, model: str | None = None) -> dict[str, Any]:
    """Gera 4 ganchos virais estruturados baseados nas fórmulas comprovadas de retenção."""
    selected_model = model or OLLAMA_MODEL or "llama3.1"
    system_prompt = (
        "Você é um especialista em retenção de audiência e copywriting viral para vídeos curtos (Reels, TikTok, Shorts). "
        "Gere exatamente 4 ganchos aplicando as 4 fórmulas canônicas: curiosidade, choque, beneficio_imediato, quebra_crenca. "
        "Retorne estritamente o JSON com schema solicitado."
    )
    user_prompt = f"Tema do vídeo: {topic.strip()}"
    schema = ViralHooksResult.model_json_schema()
    try:
        payload = {
            "model": selected_model,
            "stream": False,
            "format": schema,
            "messages": [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
            "options": {"temperature": 0.4},
        }
        for url in ollama_candidate_urls("/api/chat"):
            req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers={"Content-Type": "application/json"}, method="POST")
            try:
                with urllib.request.urlopen(req, timeout=30) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                raw = str(data["message"]["content"]).strip()
                if raw.startswith("```"):
                    lines = raw.splitlines()
                    if lines[0].startswith("```"): lines = lines[1:]
                    if lines and lines[-1].strip() == "```": lines = lines[:-1]
                    raw = "\n".join(lines).strip()
                parsed = json.loads(raw)
                return ViralHooksResult.model_validate(parsed).model_dump()
            except Exception:
                continue
    except Exception:
        pass

    # Heuristic Fallback
    t = topic.strip()
    return {
        "topic": t,
        "hooks": [
            {
                "formula": "curiosidade",
                "headline": f"O segredo que ninguém te conta sobre {t}",
                "spoken_hook": f"Você não vai acreditar no que acontece se você fizer isso em {t}...",
                "retention_score": 92,
            },
            {
                "formula": "choque",
                "headline": f"Pare de errar em {t} agora mesmo!",
                "spoken_hook": f"90% das pessoas estão perdendo tempo com {t} por causa desse único detalhe.",
                "retention_score": 89,
            },
            {
                "formula": "beneficio_imediato",
                "headline": f"Como dominar {t} em menos de 3 minutos",
                "spoken_hook": f"Eu vou te mostrar o passo a passo exato para ter resultado com {t} hoje.",
                "retention_score": 87,
            },
            {
                "formula": "quebra_crenca",
                "headline": f"Esqueça tudo o que disseram sobre {t}",
                "spoken_hook": f"Eles mentiram para você sobre {t}. A verdade é completamente diferente.",
                "retention_score": 94,
            },
        ],
    }


def generate_script_to_video(topic: str, model: str | None = None) -> dict[str, Any]:
    """Gera roteiro completo de 40-60s estruturado nos 5 blocos canônicos."""
    t = topic.strip()
    schema = ScriptToVideoResult.model_json_schema()

    if GOOGLE_API_KEY:
        system_prompt = (
            "Você é um roteirista profissional premiado de vídeos curtos verticais (TikTok, Reels e YouTube Shorts). "
            "Crie um roteiro viral, dinâmico e hipnótico estruturado nos 5 blocos canônicos: hook (0-5s), context (5-15s), "
            "solution (15-35s), practical (35-50s) e cta (50-60s). "
            "Para cada bloco, forneça a fala exata (spoken_text), a orientação visual e um visual_prompt fotorrealista e cinematográfico "
            "para geração de imagens/B-rolls, além de uma palavra-chave para busca de mídia. "
            "Preencha 'full_narration' com a união fluida de todas as falas, pronta para ser lida por uma voz neural de IA."
        )
        user_prompt = f"Tema do vídeo: {t}"
        try:
            parsed = run_gemini_structured(system_prompt, user_prompt, schema, model=model)
            validated = ScriptToVideoResult.model_validate(parsed)
            res = validated.model_dump()
            if not res.get("full_narration"):
                res["full_narration"] = " ".join(b["spoken_text"] for b in res.get("blocks", []))
            return res
        except Exception:
            pass

    # Heuristic Fallback estruturado
    blocks = [
        {
            "block_name": "hook",
            "timing": "0-5s",
            "spoken_text": f"Você ainda comete esse erro comum quando o assunto é {t}?",
            "visual_direction": "Plano fechado com zoom dinâmico e expressão de atenção",
            "visual_prompt": f"Dramatic cinematic close-up shot of a person realization about {t}, modern aesthetic 8k",
            "keyword": "focus",
        },
        {
            "block_name": "context",
            "timing": "5-15s",
            "spoken_text": f"A maioria das pessoas tenta resolver {t} do jeito tradicional e só perde tempo e dinheiro.",
            "visual_direction": "Corte de B-Roll ilustrando frustração ou rotina acelerada",
            "visual_prompt": f"Fast paced cinematic montage showing daily struggles with {t}, moody cinematic lighting",
            "keyword": "struggle",
        },
        {
            "block_name": "solution",
            "timing": "15-35s",
            "spoken_text": f"Mas existe um método simples em 3 passos que muda todo o jogo. Primeiro, defina a meta clara. Segundo, automatize o fluxo. E terceiro, meça o resultado.",
            "visual_direction": "Apresentador na tela com legendas com cores dinâmicas e palavras-chave acesas",
            "visual_prompt": f"Futuristic holographic interface showing seamless growth and productivity solution for {t}",
            "keyword": "solution",
        },
        {
            "block_name": "practical",
            "timing": "35-50s",
            "spoken_text": f"Aplicando isso hoje, você corta metade do esforço e dobra a velocidade da sua entrega.",
            "visual_direction": "Sobreposição de gráfico ou tela de demonstração prática",
            "visual_prompt": "Exponential success graph glowing with neon cyan and green light, clean background",
            "keyword": "success",
        },
        {
            "block_name": "cta",
            "timing": "50-60s",
            "spoken_text": "Comenta 'EU QUERO' aqui embaixo que eu te mando o checklist completo no direct!",
            "visual_direction": "Sticker animado de CTA com sino e seta apontando para os comentários",
            "visual_prompt": "Smartphone mockup floating with vibrant social media engagement notifications",
            "keyword": "calltoaction",
        },
    ]
    full_text = " ".join(b["spoken_text"] for b in blocks)
    clean_tag = t.replace(" ", "").lower()[:20]
    return {
        "title": f"Roteiro: {t}",
        "target_duration": "45s",
        "word_count": len(full_text.split()),
        "full_narration": full_text,
        "blocks": blocks,
        "suggested_hashtags": [f"#{clean_tag}", "#dicas", "#viral", "#shorts", "#produtividade"],
        "suggested_audio_mood": "energetic_lofi",
    }

