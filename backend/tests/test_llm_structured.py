from __future__ import annotations

from app.services.llm import AgentItem, AgentRunResult, fallback_structured_response, schema_for_agent_run


def test_agent_structured_schema() -> None:
    schema = schema_for_agent_run()
    assert "properties" in schema
    assert "agent" in schema["properties"]
    assert "items" in schema["properties"]


def test_pydantic_agent_run_model() -> None:
    data = {
        "agent": "roteirista",
        "items": [
            {"title": "Gancho Curioso", "description": "Voce nao vai acreditar...", "score": 0.9},
            {"title": "Gancho de Dor", "description": "Pare de cometer esse erro...", "score": 0.85},
        ],
    }
    result = AgentRunResult.model_validate(data)
    assert result.agent == "roteirista"
    assert len(result.items) == 2
    assert result.items[0].score == 0.9


def test_fallback_structured_response() -> None:
    res = fallback_structured_response("editor", "crie 3 ganchos para reels")
    assert res["agent"] == "editor"
    assert len(res["items"]) == 3
    validated = AgentRunResult.model_validate(res)
    assert validated.agent == "editor"
