from datetime import date

import pytest

from evals.fixtures.weather import FixtureError, make_weather_service
from src.agents.common.context import ParachuteContext, SharedServices
from src.domain.weather_models import Decision
from src.services.calendar_service import InMemoryCalendarService
from src.tools.weather_tools import evaluate_jump_day

TODAY = date(2026, 9, 17)
VALID_DATE = date(2026, 9, 20)


@pytest.mark.parametrize(
    ("fixture", "decision", "value"),
    [
        ("ideal", Decision.IDEAL, 10),
        ("marginal_wind_lower", Decision.MARGINAL, 20),
        ("marginal_wind_upper", Decision.MARGINAL, 28),
        ("prohibited_wind", Decision.PROHIBITED, 28.1),
        ("prohibited_gusts", Decision.PROHIBITED, 10),
        ("prohibited_rain", Decision.PROHIBITED, 10),
        ("marginal_clouds", Decision.MARGINAL, 10),
        ("prohibited_clouds", Decision.PROHIBITED, 10),
    ],
)
def test_fixture_values_and_boundaries(fixture, decision, value):
    service = make_weather_service(fixture)
    assessment = service.check_jump_day(VALID_DATE, TODAY)
    assert assessment.decision == decision
    assert assessment.weather.wind_speed_10m_kmh == value
    assert assessment.weather.source == "fixture"
    assert service.client.calls == [VALID_DATE]


def test_fixture_error_and_unknown_name():
    from src.services.weather_service import WeatherServiceError

    with pytest.raises(FixtureError):
        make_weather_service("missing")
    with pytest.raises(WeatherServiceError, match="simulado"):
        make_weather_service("error").check_jump_day(VALID_DATE, TODAY)


def test_clock_horizon_and_no_network_for_invalid_date():
    from src.services.weather_service import WeatherServiceError

    service = make_weather_service("ideal")
    assert service.check_jump_day(date(2026, 10, 2), TODAY).decision == Decision.IDEAL
    with pytest.raises(WeatherServiceError, match="horizonte"):
        service.check_jump_day(date(2026, 10, 3), TODAY)
    assert service.client.calls == [date(2026, 10, 2)]


def test_new_failed_assessment_clears_previous_one():
    service = make_weather_service("ideal")
    context = ParachuteContext(
        services=SharedServices(service, InMemoryCalendarService(), None),
        today=lambda: TODAY,
    )
    evaluate_jump_day(context, "2026-09-20")
    assert context.jump_assessment is not None
    evaluate_jump_day(context, "2026-10-03")
    assert context.jump_assessment is None
    assert context.requested_date is None
    assert service.client.calls == [VALID_DATE]


def test_each_service_has_independent_call_history():
    first = make_weather_service("ideal")
    second = make_weather_service("ideal")
    first.check_jump_day(VALID_DATE, TODAY)
    assert second.client.calls == []
