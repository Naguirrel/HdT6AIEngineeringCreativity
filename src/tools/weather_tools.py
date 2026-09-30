"""Tool compartido de clima/seguridad. Envuelve el unico camino: validar -> Open-Meteo -> evaluar.

La logica vive en `evaluate_jump_day`, una funcion plana testeable sin necesidad
de instanciar el runtime de agentes; el decorador @function_tool solo la conecta
al contexto de la conversacion.
"""

from datetime import date, datetime

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
    log_event(architecture=context.architecture, tool="check_jump_day", requested_date=date_str)

    try:
        parsed_date = _parse_date(date_str)
    except ValueError:
        return f"Formato de fecha invalido: '{date_str}'. Usa YYYY-MM-DD."

    try:
        assessment = context.services.weather_service.check_jump_day(parsed_date, date.today())
    except WeatherServiceError as error:
        log_event(architecture=context.architecture, tool="check_jump_day", weather_check_result="error")
        return f"Error: {error}"

    context.requested_date = parsed_date
    context.jump_assessment = assessment
    log_event(
        architecture=context.architecture,
        tool="check_jump_day",
        weather_check_result="ok",
        jump_assessment=assessment.decision.value,
    )
    return _format_assessment(assessment)


@function_tool
def check_jump_day(wrapper: RunContextWrapper[ParachuteContext], date_str: str) -> str:
    """Valida la fecha, consulta Open-Meteo y evalua deterministicamente si se puede saltar.

    Args:
        date_str: fecha solicitada en formato YYYY-MM-DD.
    """
    return evaluate_jump_day(wrapper.context, date_str)
