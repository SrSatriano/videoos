from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any

from ..config import OLLAMA_MODEL
from .llm import ollama_candidate_urls


AGENTS = [
    {
        "id": "roteirista_tech",
        "name": "Roteirista Tech",
        "role": "Cria roteiros curtos, didaticos e com CTA para canais de dicas tech.",
    },
    {
        "id": "adaptador_dark",
        "name": "Adaptador Dark",
        "role": "Transforma uma ideia em variações para Reels, TikTok e Shorts sem depender de rosto.",
    },
    {
        "id": "pesquisador_tendencias",
        "name": "Pesquisador de Tendencias",
        "role": "Organiza perguntas de pesquisa, angulos e pautas para validar antes de produzir.",
    },
    {
        "id": "copy_publicacao",
        "name": "Copy de Publicacao",
        "role": "Gera legenda, hashtags e checklist de postagem manual.",
    },
    {
        "id": "auditor_direitos",
        "name": "Auditor de Direitos",
        "role": "Checa riscos de reaproveitamento, autoria, privacidade e claims.",
    },
    {
        "id": "otimizador_lote",
        "name": "Otimizador de Lote",
        "role": "Sugere variações de template, CTA, cortes e ordem de renderização.",
    },
    {
        "id": "clipper",
        "name": "Cacador de Cortes",
        "role": "Encontra momentos fortes e transforma em shorts com hook, motivo e CTA.",
    },
    {
        "id": "hook",
        "name": "Editor de Gancho",
        "role": "Melhora os 3 primeiros segundos do video para aumentar retencao.",
    },
    {
        "id": "caption",
        "name": "Legenda Viral",
        "role": "Cria captions curtas, destaca keywords e remove vicios de fala.",
    },
    {
        "id": "seo",
        "name": "SEO Social",
        "role": "Gera titulos, descricoes e hashtags por plataforma.",
    },
    {
        "id": "broll",
        "name": "Curador de B-roll",
        "role": "Sugere cenas de apoio e assets locais para reforcar a mensagem.",
    },
    {
        "id": "music",
        "name": "Diretor Musical",
        "role": "Cria briefs de trilha, moods e orientacoes de ducking para videos curtos.",
    },
    {
        "id": "qa",
        "name": "Revisor Final",
        "role": "Checa legibilidade, audio, CTA, direitos e pacote final antes da publicacao.",
    },
]


def list_agents() -> list[dict[str, str]]:
    return AGENTS


def find_agent(agent_id: str) -> dict[str, str]:
    return next((agent for agent in AGENTS if agent["id"] == agent_id), AGENTS[0])


def fallback_agent_response(agent: dict[str, str], brief: str) -> str:
    return "\n".join(
        [
            f"Agente: {agent['name']}",
            f"Missao: {agent['role']}",
            "",
            "Plano sugerido:",
            "1. Defina a promessa principal do video em uma frase.",
            "2. Abra com gancho direto nos 2 primeiros segundos.",
            "3. Mostre 3 passos praticos ou uma demonstracao curta.",
            "4. Termine com CTA simples para comentario, salvamento ou envio.",
            "",
            f"Brief recebido: {brief}",
            "",
            "Ollama nao respondeu. Instale/abra Ollama e configure VIDEO_OS_OLLAMA_MODEL para respostas por LLM local.",
        ]
    )


def run_agent(agent_id: str, brief: str) -> dict[str, Any]:
    agent = find_agent(agent_id)
    prompt = (
        "Voce e um agente local do Video OS.\n"
        f"Nome: {agent['name']}\n"
        f"Funcao: {agent['role']}\n"
        "Responda em portugues do Brasil, com passos acionaveis, foco em conteudo curto vertical e uso etico.\n\n"
        f"Brief:\n{brief}"
    )
    payload = json.dumps({"model": OLLAMA_MODEL, "prompt": prompt, "stream": False}).encode("utf-8")
    for url in ollama_candidate_urls("/api/generate"):
        request = urllib.request.Request(
            url,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                data = json.loads(response.read().decode("utf-8"))
            return {
                "agent": agent,
                "provider": "ollama",
                "model": OLLAMA_MODEL,
                "output": data.get("response", "").strip(),
            }
        except (OSError, urllib.error.URLError, TimeoutError, json.JSONDecodeError):
            continue
    return {
        "agent": agent,
        "provider": "fallback",
        "model": None,
        "output": fallback_agent_response(agent, brief),
    }
