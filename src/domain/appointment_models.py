"""Modelos de dominio para la cita de salto."""

from dataclasses import dataclass
from datetime import date

from .weather_models import JumpAssessment


@dataclass(frozen=True)
class AppointmentData:
    customer_name: str
    contact: str
    jump_date: date
    is_experienced_tandem: bool = False
    party_size: int = 1


@dataclass(frozen=True)
class AppointmentRecord:
    id: str
    data: AppointmentData
    assessment: JumpAssessment
