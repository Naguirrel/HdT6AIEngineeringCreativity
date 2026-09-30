"""Modelos tipados para clima y evaluacion de seguridad del salto."""

from dataclasses import dataclass, field
from datetime import date
from enum import Enum


class Decision(str, Enum):
    IDEAL = "IDEAL"
    MARGINAL = "MARGINAL"
    PROHIBITED = "PROHIBITED"


@dataclass(frozen=True)
class WeatherSnapshot:
    date: date
    wind_speed_10m_kmh: float
    wind_gust_10m_kmh: float
    precipitation_mm: float
    cloud_cover_percent: float
    temperature_2m_c: float
    source: str = "open-meteo"


@dataclass(frozen=True)
class JumpAssessment:
    decision: Decision
    reasons: list[str] = field(default_factory=list)
    weather: WeatherSnapshot | None = None

    @property
    def requires_experienced_tandem(self) -> bool:
        return self.decision == Decision.MARGINAL

    @property
    def allows_appointment(self) -> bool:
        return self.decision != Decision.PROHIBITED
