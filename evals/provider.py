"""Promptfoo Python provider. Output is only the final answer; trace stays in metadata."""

import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.agents.centralized.evaluation import run_centralized_session
from src.config import ConfigError


def call_api(prompt, options, context):
    """Return a Promptfoo ProviderResponse for one isolated scenario."""
    variables = context.get("vars", {})
    turns = variables.get("turns", prompt)
    if isinstance(turns, str):
        turns = [turns]
    if not isinstance(turns, list):
        return {"error": "turns debe ser una lista de mensajes o una cadena."}
    try:
        fixed_today = variables.get("fixed_today")
        if fixed_today is not None:
            fixed_today = date.fromisoformat(fixed_today)
        result = run_centralized_session(turns, fixed_today=fixed_today)
    except ConfigError as error:
        return {"error": f"Configuracion: {error}"}
    except ValueError as error:
        return {"error": f"Escenario invalido: {error}"}
    except Exception as error:
        # Model and tool exceptions may contain provider details. Do not echo them.
        return {"error": f"Fallo durante la ejecucion: {type(error).__name__}"}
    return {
        "output": result.answer,
        "metadata": {
            "scenario": variables.get("scenario", "unknown"),
            "tool_calls": result.tool_calls,
            "retrieved_context": result.retrieved_context,
            "latency_ms": result.latency_ms,
        },
        "latencyMs": result.latency_ms,
    }
