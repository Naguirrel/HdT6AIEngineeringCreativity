"""Fabrica de agentes especialistas reutilizados por las tres arquitecturas.

Las instrucciones explican las reglas de negocio, pero las reglas en si (fecha,
clima, seguridad, anti-bypass) viven en src/domain y src/services, no aqui.
"""

from agents import Agent, Handoff, Model

from src.tools.calendar_tools import check_appointment_availability, create_appointment
from src.tools.faq_tools import search_faq
from src.tools.weather_tools import check_jump_day

FAQ_INSTRUCTIONS = """Eres el especialista en preguntas frecuentes de Parachute S.A.
Usa siempre la herramienta search_faq para responder preguntas sobre el evento,
requisitos, precios, horarios o preparacion. No inventes informacion que no
provenga de search_faq. Si la pregunta es sobre reservar una cita o el clima de
un dia especifico, dilo explicitamente para que se pueda coordinar con el
especialista correspondiente."""

WEATHER_INSTRUCTIONS = """Eres el especialista en clima y seguridad de salto de Parachute S.A.
Para cualquier fecha solicitada usa la herramienta check_jump_day(date_str) con
formato YYYY-MM-DD; nunca decidas tu solo si se puede saltar, la herramienta ya
aplica la politica oficial de seguridad. Explica el resultado (IDEAL, MARGINAL o
PROHIBITED) y, si es MARGINAL, aclara que solo aplica para tandem experimentado.
Si es PROHIBITED, indica que no se puede crear una cita para ese dia."""

SCHEDULING_INSTRUCTIONS = """Eres el especialista en calendarizacion de Parachute S.A.
Antes de crear una cita, la fecha debe haber sido evaluada con check_jump_day por
el especialista de clima (esto ya queda registrado en el contexto de la
conversacion). Usa check_appointment_availability para confirmar cupo y
create_appointment para confirmar la cita, solicitando al usuario nombre,
contacto y, si la evaluacion fue MARGINAL, confirmacion explicita de que acepta
un salto tandem con instructor experimentado."""


def build_faq_agent(model: Model, handoffs: list[Handoff | Agent] | None = None) -> Agent:
    return Agent(
        name="FAQ Agent",
        handoff_description="Responde preguntas frecuentes sobre el evento de paracaidismo.",
        instructions=FAQ_INSTRUCTIONS,
        tools=[search_faq],
        handoffs=handoffs or [],
        model=model,
    )


def build_weather_agent(model: Model, handoffs: list[Handoff | Agent] | None = None) -> Agent:
    return Agent(
        name="Weather Agent",
        handoff_description="Valida la fecha y evalua deterministicamente si se puede saltar.",
        instructions=WEATHER_INSTRUCTIONS,
        tools=[check_jump_day],
        handoffs=handoffs or [],
        model=model,
    )


def build_scheduling_agent(model: Model, handoffs: list[Handoff | Agent] | None = None) -> Agent:
    return Agent(
        name="Scheduling Agent",
        handoff_description="Verifica disponibilidad y crea la cita de salto.",
        instructions=SCHEDULING_INSTRUCTIONS,
        tools=[check_appointment_availability, create_appointment],
        handoffs=handoffs or [],
        model=model,
    )
