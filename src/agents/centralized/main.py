"""Arquitectura centralizada: un unico supervisor que expone especialistas via as_tool()."""

import sys

from agents import Agent

from src.agents.common.bootstrap import build_context
from src.agents.common.booking_completion import booking_result_or_continue
from src.agents.common.cli import run_chat
from src.agents.common.context import ParachuteContext
from src.agents.common.model_client import build_model
from src.agents.common.specialist_agents import build_faq_agent, build_scheduling_agent, build_weather_agent
from src.config import ConfigError, load_config
from src.observability import configure_logging

SUPERVISOR_INSTRUCTIONS = """Eres el supervisor central de Parachute S.A.
Tu alcance se limita a Parachute S.A., sus FAQs, el evento, el clima para saltar
y las citas. Ante una pregunta claramente fuera de ese dominio, no respondas
con conocimiento general aunque sepas la respuesta; indica brevemente que
solo puedes ayudar con Parachute S.A., sus FAQs o citas.
Responde directamente a saludos, despedidas y preguntas claramente fuera del
dominio. En esos casos no invoques faq_specialist, weather_specialist ni
scheduling_specialist, ni sus herramientas search_faq, clima o calendario.
Para preguntas sobre hechos de Parachute S.A. o sus FAQs, delega siempre a
faq_specialist antes de responder. No respondas con memoria propia. Basa tu
respuesta solo en el resultado recuperado; copia fielmente los datos exactos.
Si el especialista no encuentra el dato solicitado, indícalo sin completarlo.
Si una FAQ distingue reglas para grupos diferentes, prioriza el grupo indicado
por el usuario. No presentes la regla general como requisito absoluto cuando
el contexto recuperado establece una excepcion aplicable; si citas ambas,
explica claramente a quien corresponde cada una.
Las solicitudes de cita son parte de tu dominio. Nunca respondas a una reserva
con la negativa para preguntas fuera del dominio. Para crear una cita, completa
en orden check_jump_day, check_appointment_availability y create_appointment;
no termines tras comprobar el cupo si el usuario ya proporciono los datos y
las condiciones permiten reservar. Nunca invoques create_appointment sin cupo
aprobado para la misma fecha. Si create_appointment confirma la cita, comunica
fielmente el resultado y su fecha; no sustituyas ese exito por una negativa.
Recibes toda interaccion del usuario y decides que especialista usar:
- faq_specialist para preguntas frecuentes sobre el evento;
- weather_specialist para validar una fecha y evaluar si se puede saltar;
- scheduling_specialist para verificar disponibilidad y crear una cita.
Puedes combinar varios especialistas en una misma respuesta si el usuario pide
varias cosas a la vez (por ejemplo, reservar una fecha y tambien preguntar que
llevar). Nunca calendarices una cita sin antes haber evaluado el clima de esa
fecha con weather_specialist."""


def build_supervisor() -> tuple[Agent, ParachuteContext]:
    config = load_config()
    context = build_context(config, architecture="centralized")
    model = build_model(config)

    faq_agent = build_faq_agent(model)
    weather_agent = build_weather_agent(model)
    scheduling_agent = build_scheduling_agent(model)

    supervisor = Agent(
        name="Central Supervisor",
        instructions=SUPERVISOR_INSTRUCTIONS,
        model=model,
        tool_use_behavior=booking_result_or_continue,
        tools=[
            faq_agent.as_tool(
                tool_name="faq_specialist",
                tool_description="Responde preguntas frecuentes sobre el evento de paracaidismo.",
            ),
            weather_agent.as_tool(
                tool_name="weather_specialist",
                tool_description="Valida una fecha y evalua si las condiciones permiten saltar.",
            ),
            scheduling_agent.as_tool(
                tool_name="scheduling_specialist",
                tool_description="Verifica disponibilidad y crea la cita de salto.",
            ),
        ],
    )
    return supervisor, context


def main() -> int:
    configure_logging()
    try:
        supervisor, context = build_supervisor()
    except ConfigError as error:
        print(f"Error de configuracion: {error}", file=sys.stderr)
        return 2

    run_chat(supervisor, context, "centralizada")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
