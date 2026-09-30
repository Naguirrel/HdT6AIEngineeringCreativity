"""Estado/contexto tipado compartido por las tres arquitecturas de agentes.

Sobrevive a llamadas a subagentes, as_tool() y handoffs porque el SDK propaga el
mismo objeto de contexto (RunContextWrapper[ParachuteContext]) a lo largo de todo
el run, sin depender de que el LLM recuerde datos en texto libre.
"""

from dataclasses import dataclass
from datetime import date

from src.domain.appointment_models import AppointmentData, AppointmentRecord
from src.domain.weather_models import JumpAssessment
from src.services.calendar_service import CalendarService
from src.services.faq_service import FaqService
from src.services.weather_service import WeatherService


@dataclass
class SharedServices:
    weather_service: WeatherService
    calendar_service: CalendarService
    faq_service: FaqService


@dataclass
class ParachuteContext:
    services: SharedServices
    architecture: str = "unknown"
    requested_date: date | None = None
    jump_assessment: JumpAssessment | None = None
    appointment_data: AppointmentData | None = None
    appointment_record: AppointmentRecord | None = None
