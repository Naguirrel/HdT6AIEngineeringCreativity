"""Estado/contexto tipado compartido por las tres arquitecturas de agentes.

Sobrevive a llamadas a subagentes, as_tool() y handoffs porque el SDK propaga el
mismo objeto de contexto (RunContextWrapper[ParachuteContext]) a lo largo de todo
el run, sin depender de que el LLM recuerde datos en texto libre.
"""

from dataclasses import dataclass, field
from copy import deepcopy
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
    assessment_checked_on: date | None = None
    availability_approved_date: date | None = None
    appointment_data: AppointmentData | None = None
    appointment_record: AppointmentRecord | None = None
    appointment_confirmation: str | None = None
    confirmed_tandem_date: date | None = None
    retrieved_context: list[dict[str, str]] = field(default_factory=list)
    _tool_trace: list[dict] = field(default_factory=list, repr=False)

    def record_tool_event(self, tool: str, arguments: dict, result: dict, status: str) -> None:
        if status not in {"success", "error"}:
            raise ValueError("El estado de la herramienta debe ser success o error.")
        self._tool_trace.append({
            "sequence": len(self._tool_trace) + 1,
            "tool": tool,
            "arguments": deepcopy(arguments),
            "result": deepcopy(result),
            "status": status,
        })

    def get_tool_trace(self) -> list[dict]:
        """Return a copy so callers cannot alter the session's recorded events."""
        return deepcopy(self._tool_trace)

    def get_retrieved_context(self) -> list[dict[str, str]]:
        return deepcopy(self.retrieved_context)

    def has_current_booking_approvals(self, requested_date: date) -> bool:
        """Require matching, ordered approvals in this session's business trace."""
        if self.requested_date != requested_date or self.availability_approved_date != requested_date:
            return False
        if (
            self.jump_assessment is None or not self.jump_assessment.allows_appointment
            or self.assessment_checked_on != self.today()
        ):
            return False
        weather = self.jump_assessment.weather
        if weather is None or weather.date != requested_date:
            return False
        if self.jump_assessment.requires_experienced_tandem and self.confirmed_tandem_date != requested_date:
            return False

        weather_event = next(
            (event for event in reversed(self._tool_trace) if event["tool"] == "check_jump_day"), None
        )
        availability_event = next(
            (event for event in reversed(self._tool_trace) if event["tool"] == "check_appointment_availability"), None
        )
        return bool(
            weather_event and availability_event
            and weather_event["status"] == availability_event["status"] == "success"
            and weather_event["arguments"].get("date_str") == requested_date.isoformat()
            and weather_event["result"].get("decision") == self.jump_assessment.decision.value
            and availability_event["arguments"].get("date_str") == requested_date.isoformat()
            and availability_event["result"].get("available") is True
            and weather_event["sequence"] < availability_event["sequence"]
        )

    def observe_user_message(self, message: str) -> None:
        """Record an explicit user confirmation for the currently assessed marginal day."""
        self.appointment_confirmation = None
        if self.requested_date is None or self.jump_assessment is None:
            return

        normalized = unicodedata.normalize("NFKD", message.casefold())
        normalized = "".join(char for char in normalized if not unicodedata.combining(char))
        normalized = re.sub(r"[\u2010-\u2015\u2212]", "-", normalized)
        dates = re.findall(r"\b\d{4}-\d{2}-\d{2}\b", normalized)
        if dates and any(value != self.requested_date.isoformat() for value in dates):
            self.requested_date = None
            self.jump_assessment = None
            self.assessment_checked_on = None
            self.availability_approved_date = None
            self.confirmed_tandem_date = None
            return
        if not self.jump_assessment.requires_experienced_tandem:
            return
        if "?" in normalized or re.search(r"\b(no|nunca|rechazo|sin)\b", normalized):
            self.confirmed_tandem_date = None
            self.availability_approved_date = None
            return
        accepts = re.match(r"^\s*(?:si[,\s]+)?(?:acepto|confirmo|estoy de acuerdo)\b", normalized)
        if accepts and "tandem" in normalized and "experimentado" in normalized:
            self.confirmed_tandem_date = self.requested_date
