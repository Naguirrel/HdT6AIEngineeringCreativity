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

    def __post_init__(self) -> None:
        if not isinstance(self.customer_name, str) or not self.customer_name.strip():
            raise ValueError("El nombre del cliente debe ser un texto no vacio.")
        if len(self.customer_name.strip()) > 200:
            raise ValueError("El nombre del cliente excede 200 caracteres.")
        if not isinstance(self.contact, str) or not self.contact.strip():
            raise ValueError("El contacto debe ser un texto no vacio.")
        if len(self.contact.strip()) > 254:
            raise ValueError("El contacto excede 254 caracteres.")
        if type(self.jump_date) is not date:
            raise ValueError("La fecha de la cita debe ser una fecha valida.")
        if type(self.is_experienced_tandem) is not bool:
            raise ValueError("La confirmacion de tandem debe ser un valor booleano.")
        if type(self.party_size) is not int or self.party_size < 1:
            raise ValueError("El numero de participantes debe ser un entero mayor o igual a 1.")


@dataclass(frozen=True)
class AppointmentRecord:
    id: str
    data: AppointmentData
    assessment: JumpAssessment
