"""Programmatic runner for evaluating the real centralized supervisor."""

import asyncio
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import date
from time import perf_counter

from agents import Runner

from src.agents.centralized.main import build_supervisor


@dataclass(frozen=True)
class EvaluationResult:
    answer: str
    tool_calls: list[dict]
    retrieved_context: list[dict[str, str]]
    latency_ms: int
    weather_requests: list[str] | None = None
    confirmed_tandem_date: str | None = None


async def run_centralized_session_async(
    turns: Sequence[str],
    *,
    build: Callable = build_supervisor,
    run: Callable = Runner.run,
    weather_service=None,
    fixed_today: date | None = None,
) -> EvaluationResult:
    """Create fresh agent, services, context, history and calendar for each case."""
    if not turns or any(not isinstance(turn, str) or not turn.strip() for turn in turns):
        raise ValueError("La evaluacion requiere uno o mas mensajes no vacios.")
    started = perf_counter()
    supervisor, context = build()
    if weather_service is not None:
        context.services.weather_service = weather_service
    if fixed_today is not None:
        context.today = lambda: fixed_today

    history: list[dict] = []
    current_agent = supervisor
    answer = ""
    for turn in turns:
        context.observe_user_message(turn)
        history.append({"role": "user", "content": turn})
        result = await run(current_agent, history, context=context)
        if not isinstance(result.final_output, str) or not result.final_output.strip():
            raise RuntimeError("El modelo devolvio una respuesta vacia.")
        answer = result.final_output
        history = result.to_input_list()
        current_agent = result.last_agent

    return EvaluationResult(
        answer=answer,
        tool_calls=context.get_tool_trace(),
        retrieved_context=context.get_retrieved_context(),
        latency_ms=round((perf_counter() - started) * 1000),
        weather_requests=[value.isoformat() for value in weather_service.client.calls]
        if weather_service is not None else None,
        confirmed_tandem_date=context.confirmed_tandem_date.isoformat()
        if context.confirmed_tandem_date is not None else None,
    )


def run_centralized_session(turns: Sequence[str], **kwargs) -> EvaluationResult:
    return asyncio.run(run_centralized_session_async(turns, **kwargs))
