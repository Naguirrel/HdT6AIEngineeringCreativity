"""Abstraccion de calendarizacion con una implementacion local in-memory.

El proyecto previo (Sistema-RAG) no usa ningun proveedor de calendario, por lo que
no se asume Google Calendar. Esta clase concentra las garantias anti-bypass: ninguna
implementacion de CalendarService puede crear una cita sin una evaluacion aprobada.
"""

import uuid
from dataclasses import dataclass, field
from datetime import date
from typing import Protocol

from src.domain.appointment_models import AppointmentData, AppointmentRecord
from src.domain.weather_models import Decision, JumpAssessment


class CalendarServiceError(RuntimeError):
    """La cita no pudo crearse por una regla de negocio o de disponibilidad."""


class CalendarService(Protocol):
    def check_availability(self, jump_date: date) -> bool: ...

    def create_appointment(
        self, data: AppointmentData, assessment: JumpAssessment
    ) -> AppointmentRecord: ...


@dataclass
class InMemoryCalendarService:
    max_slots_per_day: int = 8
    _records: dict[str, AppointmentRecord] = field(default_factory=dict)
    _by_day: dict[date, list[str]] = field(default_factory=dict)

    def check_availability(self, jump_date: date) -> bool:
        booked = len(self._by_day.get(jump_date, []))
        return booked < self.max_slots_per_day

    def create_appointment(
        self, data: AppointmentData, assessment: JumpAssessment
    ) -> AppointmentRecord:
        """Crea la cita solo si la evaluacion lo permite; es idempotente por cliente+fecha."""
        if assessment.weather is None or assessment.weather.date != data.jump_date:
            raise CalendarServiceError(
                "La evaluacion meteorologica no corresponde a la fecha de la cita solicitada."
            )

        if assessment.decision == Decision.PROHIBITED:
            raise CalendarServiceError(
                "No se puede crear la cita: las condiciones climaticas estan prohibidas para saltar."
            )

        if assessment.decision == Decision.MARGINAL and not data.is_experienced_tandem:
            raise CalendarServiceError(
                "Condiciones marginales: solo se permite tandem experimentado. "
                "Confirma esta condicion antes de calendarizar."
            )

        idempotency_key = f"{data.customer_name.strip().lower()}|{data.contact.strip().lower()}|{data.jump_date.isoformat()}"
        if idempotency_key in self._records:
            return self._records[idempotency_key]

        if not self.check_availability(data.jump_date):
            raise CalendarServiceError(f"No hay cupo disponible para {data.jump_date.isoformat()}.")

        record = AppointmentRecord(id=str(uuid.uuid4()), data=data, assessment=assessment)
        self._records[idempotency_key] = record
        self._by_day.setdefault(data.jump_date, []).append(idempotency_key)
        return record
