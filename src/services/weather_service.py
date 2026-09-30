"""Servicio de aplicacion: valida fecha, consulta Open-Meteo y evalua condiciones."""

from dataclasses import dataclass
from datetime import date

from src.domain.date_policy import validate_forecast_date
from src.domain.weather_models import JumpAssessment
from src.domain.weather_policy import assess_jump_conditions
from src.integrations.open_meteo import OpenMeteoClient, OpenMeteoError


class WeatherServiceError(RuntimeError):
    """Error de negocio al obtener/evaluar el clima de una fecha."""


@dataclass(frozen=True)
class WeatherService:
    client: OpenMeteoClient
    max_horizon_days: int

    def check_jump_day(self, requested_date: date, today: date) -> JumpAssessment:
        """Valida la fecha, obtiene el pronostico y devuelve la evaluacion deterministica.

        Este es el unico camino que las tres arquitecturas deben usar para evaluar un dia:
        valida -> Open-Meteo -> evaluacion, siempre en el mismo orden.
        """
        validation = validate_forecast_date(requested_date, today, self.max_horizon_days)
        if not validation.is_valid:
            raise WeatherServiceError(validation.message)

        try:
            weather = self.client.get_weather(requested_date)
        except OpenMeteoError as error:
            raise WeatherServiceError(f"No fue posible obtener el pronostico: {error}") from error

        return assess_jump_conditions(weather)
