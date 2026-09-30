"""Estado/contexto tipado compartido por las tres arquitecturas de agentes.

Sobrevive a llamadas a subagentes, as_tool() y handoffs porque el SDK propaga el
mismo objeto de contexto (RunContextWrapper[ParachuteContext]) a lo largo de todo
el run, sin depender de que el LLM recuerde datos en texto libre.
"""

from dataclasses import dataclass, field
from datetime import date
import re
import unicodedata
from typing import Callable

from src.domain.appointment_models import AppointmentData, AppointmentRecord
from src.domain.clock import current_guatemala_date
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
    today: Callable[[], date] = field(default=current_guatemala_date, repr=False)
    requested_date: date | None = None
    jump_assessment: JumpAssessment | None = None
    appointment_data: AppointmentData | None = None
    appointment_record: AppointmentRecord | None = None
    confirmed_tandem_date: date | None = None

    def observe_user_message(self, message: str) -> None:
        """Record an explicit user confirmation for the currently assessed marginal day."""
        if self.requested_date is None or self.jump_assessment is None:
            return
        if not self.jump_assessment.requires_experienced_tandem:
            return

        normalized = unicodedata.normalize("NFKD", message.casefold())
        normalized = "".join(char for char in normalized if not unicodedata.combining(char))
        dates = re.findall(r"\b\d{4}-\d{2}-\d{2}\b", normalized)
        if dates and any(value != self.requested_date.isoformat() for value in dates):
            self.confirmed_tandem_date = None
            return
        if "?" in normalized or re.search(r"\b(no|nunca|rechazo|sin)\b", normalized):
            self.confirmed_tandem_date = None
            return
        accepts = re.match(r"^\s*(?:si[,\s]+)?(?:acepto|confirmo|estoy de acuerdo)\b", normalized)
        if accepts and "tandem" in normalized and "experimentado" in normalized:
            self.confirmed_tandem_date = self.requested_date
