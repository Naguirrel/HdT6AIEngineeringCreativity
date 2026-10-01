"""Tool compartido de clima/seguridad. Envuelve el unico camino: validar -> Open-Meteo -> evaluar.

La logica vive en `evaluate_jump_day`, una funcion plana testeable sin necesidad
de instanciar el runtime de agentes; el decorador @function_tool solo la conecta
al contexto de la conversacion.
"""

from datetime import date, datetime
import re

from agents import RunContextWrapper, function_tool

from src.agents.common.context import ParachuteContext
from src.domain.weather_models import Decision
from src.observability import log_event
from src.services.weather_service import WeatherServiceError


def _parse_date(date_str: str) -> date:
    return datetime.strptime(date_str.strip(), "%Y-%m-%d").date()


def _format_assessment(assessment) -> str:
    weather = assessment.weather
    lines = [
        f"Fecha: {weather.date.isoformat()}",
        f"Decision: {assessment.decision.value}",
        f"Viento superficie: {weather.wind_speed_10m_kmh} km/h",
        f"Rafagas: {weather.wind_gust_10m_kmh} km/h",
        f"Precipitacion: {weather.precipitation_mm} mm",
        f"Cobertura de nubes: {weather.cloud_cover_percent}%",
        f"Temperatura: {weather.temperature_2m_c} C",
    ]
    if assessment.reasons:
        lines.append("Motivos: " + "; ".join(assessment.reasons))
    if assessment.decision == Decision.PROHIBITED:
        lines.append("No se puede crear una cita para este dia.")
    elif assessment.decision == Decision.MARGINAL:
        lines.append("Solo se permite salto tandem con instructor experimentado.")
    return "\n".join(lines)


def evaluate_jump_day(context: ParachuteContext, date_str: str) -> str:
    """Logica del tool check_jump_day, invocable directamente en tests."""
    # A failed new request must not leave an earlier day eligible for booking.
    context.requested_date = None
    context.jump_assessment = None
    context.availability_approved_date = None
    context.appointment_data = None
    context.appointment_record = None
    context.confirmed_tandem_date = None
    trace_args = {
        "date_str": date_str if isinstance(date_str, str) and re.fullmatch(r"\d{4}-\d{2}-\d{2}", date_str) else None
    }
    log_event(architecture=context.architecture, tool="check_jump_day", requested_date=trace_args["date_str"])

    try:
        parsed_date = _parse_date(date_str)
    except (AttributeError, ValueError):
        context.record_tool_event("check_jump_day", trace_args, {"error": "invalid_date_format"}, "error")
        return f"Formato de fecha invalido: '{date_str}'. Usa YYYY-MM-DD."

    try:
        assessment = context.services.weather_service.check_jump_day(parsed_date, context.today())
    except WeatherServiceError as error:
        log_event(architecture=context.architecture, tool="check_jump_day", weather_check_result="error")
        context.record_tool_event("check_jump_day", trace_args, {"error": "weather_check_failed"}, "error")
        return f"Error: {error}"

    context.requested_date = parsed_date
    context.jump_assessment = assessment
    log_event(
        architecture=context.architecture,
        tool="check_jump_day",
        weather_check_result="ok",
        jump_assessment=assessment.decision.value,
    )
    context.record_tool_event(
        "check_jump_day", trace_args,
        {"decision": assessment.decision.value, "date": parsed_date.isoformat()}, "success",
    )
    return _format_assessment(assessment)


@function_tool
def check_jump_day(wrapper: RunContextWrapper[ParachuteContext], date_str: str) -> str:
    """Valida la fecha, consulta Open-Meteo y evalua deterministicamente si se puede saltar.

    Args:
        date_str: fecha solicitada en formato YYYY-MM-DD.
    """
    return evaluate_jump_day(wrapper.context, date_str)
