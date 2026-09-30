"""Cliente unico para Open-Meteo. No contiene reglas de seguridad."""

from dataclasses import dataclass
from datetime import date

import requests

from src.domain.weather_models import WeatherSnapshot

DAILY_VARIABLES = [
    "wind_gusts_10m_max",
    "temperature_2m_max",
    "precipitation_sum",
    "cloud_cover_mean",
    "wind_speed_10m_max",
]


class OpenMeteoError(RuntimeError):
    """Fallo al construir, ejecutar o interpretar la solicitud a Open-Meteo."""


@dataclass(frozen=True)
class OpenMeteoClient:
    latitude: float
    longitude: float
    base_url: str
    timeout_seconds: float = 10.0

    def get_weather(self, requested_date: date) -> WeatherSnapshot:
        """Obtiene el pronostico diario para `requested_date` y lo mapea al modelo interno."""
        params = {
            "latitude": self.latitude,
            "longitude": self.longitude,
            "daily": ",".join(DAILY_VARIABLES),
            "timezone": "auto",
            "wind_speed_unit": "kmh",
            "precipitation_unit": "mm",
            "temperature_unit": "celsius",
            "start_date": requested_date.isoformat(),
            "end_date": requested_date.isoformat(),
        }

        try:
            response = requests.get(self.base_url, params=params, timeout=self.timeout_seconds)
        except requests.RequestException as error:
            raise OpenMeteoError(f"Fallo de red al consultar Open-Meteo: {error}") from error

        if response.status_code != 200:
            raise OpenMeteoError(
                f"Open-Meteo respondio con estado {response.status_code}: {response.text[:200]}"
            )

        try:
            payload = response.json()
        except ValueError as error:
            raise OpenMeteoError("Open-Meteo devolvio un cuerpo que no es JSON valido.") from error

        return self._map_response(payload, requested_date)

    def _map_response(self, payload: dict, requested_date: date) -> WeatherSnapshot:
        daily = payload.get("daily")
        if not isinstance(daily, dict):
            raise OpenMeteoError("La respuesta de Open-Meteo no incluye la seccion 'daily'.")

        dates = daily.get("time")
        if not isinstance(dates, list) or requested_date.isoformat() not in dates:
            raise OpenMeteoError(
                f"Open-Meteo no devolvio pronostico para la fecha solicitada {requested_date.isoformat()}."
            )
        index = dates.index(requested_date.isoformat())

        try:
            wind_speed = daily["wind_speed_10m_max"][index]
            wind_gust = daily["wind_gusts_10m_max"][index]
            precipitation = daily["precipitation_sum"][index]
            cloud_cover = daily["cloud_cover_mean"][index]
            temperature = daily["temperature_2m_max"][index]
        except (KeyError, IndexError, TypeError) as error:
            raise OpenMeteoError("La respuesta de Open-Meteo tiene una estructura incompleta.") from error

        if any(value is None for value in (wind_speed, wind_gust, precipitation, cloud_cover, temperature)):
            raise OpenMeteoError(f"Open-Meteo devolvio datos incompletos para {requested_date.isoformat()}.")

        return WeatherSnapshot(
            date=requested_date,
            wind_speed_10m_kmh=float(wind_speed),
            wind_gust_10m_kmh=float(wind_gust),
            precipitation_mm=float(precipitation),
            cloud_cover_percent=float(cloud_cover),
            temperature_2m_c=float(temperature),
            source="open-meteo",
        )
