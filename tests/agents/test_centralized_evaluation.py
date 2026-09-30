"""The programmatic runner preserves turns and isolates each scenario."""

from datetime import date
from types import SimpleNamespace

import pytest

from src.agents.centralized.evaluation import run_centralized_session_async
from src.agents.common.context import ParachuteContext, SharedServices
from src.config import DEFAULT_FAQ_PATH
from src.services.calendar_service import InMemoryCalendarService
from src.services.faq_service import FaqService


def _build():
    agent = SimpleNamespace(name="Central Supervisor")
    context = ParachuteContext(
        services=SharedServices(
            weather_service=object(),
            calendar_service=InMemoryCalendarService(),
            faq_service=FaqService.from_path(DEFAULT_FAQ_PATH),
        ),
        architecture="centralized",
    )
    return agent, context


@pytest.mark.asyncio
async def test_programmatic_runner_keeps_turn_history_and_isolates_cases():
    histories = []

    async def fake_run(agent, history, *, context):
        histories.append([item.copy() for item in history])
        context.record_tool_event("search_faq", {}, {"match_count": 0}, "success")
        return SimpleNamespace(
            final_output=f"respuesta {len(histories)}",
            last_agent=agent,
            to_input_list=lambda: history + [{"role": "assistant", "content": "respuesta"}],
        )

    first = await run_centralized_session_async(
        ["hola", "otra pregunta"], build=_build, run=fake_run, fixed_today=date(2026, 9, 17)
    )
    second = await run_centralized_session_async(["hola"], build=_build, run=fake_run)
    assert first.answer == "respuesta 2"
    assert len(first.tool_calls) == 2
    assert len(second.tool_calls) == 1
    assert histories[1][0]["content"] == "hola"
    assert histories[1][-1]["content"] == "otra pregunta"
    assert histories[2] == [{"role": "user", "content": "hola"}]
    assert first.latency_ms >= 0


@pytest.mark.asyncio
async def test_programmatic_runner_rejects_empty_output():
    async def fake_run(agent, history, *, context):
        return SimpleNamespace(final_output="", last_agent=agent)

    with pytest.raises(RuntimeError, match="vacia"):
        await run_centralized_session_async(["hola"], build=_build, run=fake_run)


def test_promptfoo_provider_uses_only_answer_as_output(monkeypatch):
    from evals import provider
    from src.agents.centralized.evaluation import EvaluationResult

    monkeypatch.setattr(
        provider,
        "run_centralized_session",
        lambda turns, **kwargs: EvaluationResult("respuesta", [{"tool": "search_faq"}], [], 25),
    )
    response = provider.call_api("ignored", {}, {"vars": {"turns": ["consulta"], "scenario": "faq"}})
    assert response["output"] == "respuesta"
    assert response["metadata"]["tool_calls"][0]["tool"] == "search_faq"
    assert response["latencyMs"] == 25


def test_promptfoo_provider_handles_invalid_turns():
    from evals.provider import call_api

    assert "error" in call_api("", {}, {"vars": {"turns": 42}})
