"""Tools compartidos de calendarizacion. No permiten crear una cita sin evaluacion valida.

La logica vive en funciones planas (`evaluate_availability`, `book_appointment`)
testeables sin el runtime de agentes; los decoradores @function_tool solo las
conectan al contexto de la conversacion.
"""

from datetime import datetime

from agents import RunContextWrapper, function_tool

from src.agents.common.context import ParachuteContext
from src.domain.appointment_models import AppointmentData
from src.observability import log_event
from src.services.calendar_service import CalendarServiceError


def evaluate_availability(context: ParachuteContext, date_str: str) -> str:
    try:
        parsed_date = datetime.strptime(date_str.strip(), "%Y-%m-%d").date()
    except ValueError:
        return f"Formato de fecha invalido: '{date_str}'. Usa YYYY-MM-DD."

    available = context.services.calendar_service.check_availability(parsed_date)
    return "Hay cupo disponible." if available else f"No hay cupo disponible para {date_str}."


def book_appointment(
    context: ParachuteContext,
    customer_name: str,
    contact: str,
    is_experienced_tandem: bool = False,
    party_size: int = 1,
) -> str:
    log_event(architecture=context.architecture, tool="create_appointment", calendar_write_attempt=1)

    if context.jump_assessment is None or context.requested_date is None:
        log_event(architecture=context.architecture, tool="create_appointment", calendar_write_result="refused_no_assessment")
        return (
            "No se puede crear la cita: primero debes ejecutar check_jump_day para la fecha "
            "deseada y obtener una evaluacion valida."
        )

    data = AppointmentData(
        customer_name=customer_name,
        contact=contact,
        jump_date=context.requested_date,
        is_experienced_tandem=is_experienced_tandem,
        party_size=party_size,
    )

    try:
        record = context.services.calendar_service.create_appointment(data, context.jump_assessment)
    except CalendarServiceError as error:
        log_event(architecture=context.architecture, tool="create_appointment", calendar_write_result="rejected")
        return f"No se pudo crear la cita: {error}"

    context.appointment_data = data
    context.appointment_record = record
    log_event(architecture=context.architecture, tool="create_appointment", calendar_write_result="success")
    return f"Cita confirmada (id={record.id}) para {data.jump_date.isoformat()} a nombre de {data.customer_name}."


@function_tool
def check_appointment_availability(wrapper: RunContextWrapper[ParachuteContext], date_str: str) -> str:
    """Verifica si hay cupo disponible para una fecha.

    Args:
        date_str: fecha a verificar en formato YYYY-MM-DD.
    """
    return evaluate_availability(wrapper.context, date_str)


@function_tool
def create_appointment(
    wrapper: RunContextWrapper[ParachuteContext],
    customer_name: str,
    contact: str,
    is_experienced_tandem: bool = False,
    party_size: int = 1,
) -> str:
    """Crea la cita de salto para la fecha previamente verificada con check_jump_day.

    Args:
        customer_name: nombre completo del cliente.
        contact: telefono o correo del cliente.
        is_experienced_tandem: True si el cliente confirma que acepta un tandem experimentado
            (obligatorio para fechas con evaluacion MARGINAL).
        party_size: numero de personas que saltan juntas.
    """
    return book_appointment(wrapper.context, customer_name, contact, is_experienced_tandem, party_size)
