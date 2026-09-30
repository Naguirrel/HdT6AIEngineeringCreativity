"""Logging estructurado minimo, compartido por las tres arquitecturas.

No registra secretos (API keys, contactos completos) ni contenido libre del
usuario; solo los campos que el plan pide para poder comparar arquitecturas:
architecture, agent, tool, requested_date, weather_check_result,
jump_assessment, handoff/delegation, calendar_write_attempt/result.
"""

import logging
import sys

from agents import set_tracing_disabled

logger = logging.getLogger("parachute")


def configure_logging(level: int = logging.INFO) -> None:
    if logger.handlers:
        return
    handler = logging.StreamHandler(stream=sys.stderr)
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    logger.addHandler(handler)
    logger.setLevel(level)
    logger.propagate = False
    set_tracing_disabled(True)


def log_event(**fields) -> None:
    """Emite un evento como pares clave=valor en una sola linea (facil de grep/parsear)."""
    rendered = " ".join(f"{key}={value}" for key, value in fields.items() if value is not None)
    logger.info(rendered)
