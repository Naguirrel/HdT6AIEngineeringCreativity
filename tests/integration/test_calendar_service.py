from datetime import date

import pytest

from src.domain.appointment_models import AppointmentData
from src.domain.weather_models import Decision, JumpAssessment, WeatherSnapshot
from src.services.calendar_service import CalendarServiceError, InMemoryCalendarService

JUMP_DATE = date(2026, 9, 29)


def make_weather(**overrides) -> WeatherSnapshot:
    values = dict(
        date=JUMP_DATE,
        wind_speed_10m_kmh=10.0,
        wind_gust_10m_kmh=10.0,
        precipitation_mm=0.0,
        cloud_cover_percent=10.0,
        temperature_2m_c=25.0,
    )
    values.update(overrides)
    return WeatherSnapshot(**values)


def make_assessment(decision: Decision, weather: WeatherSnapshot | None = None) -> JumpAssessment:
    return JumpAssessment(decision=decision, weather=weather or make_weather())


def make_data(**overrides) -> AppointmentData:
    values = dict(
        customer_name="Juan Perez",
        contact="juan@example.com",
        jump_date=JUMP_DATE,
        is_experienced_tandem=False,
    )
    values.update(overrides)
    return AppointmentData(**values)


def test_check_availability_true_when_no_bookings():
    service = InMemoryCalendarService()
    assert service.check_availability(JUMP_DATE) is True


def test_create_appointment_succeeds_for_ideal_assessment():
    service = InMemoryCalendarService()
    record = service.create_appointment(make_data(), make_assessment(Decision.IDEAL))
    assert record.data.customer_name == "Juan Perez"
    assert record.assessment.decision == Decision.IDEAL


def test_create_appointment_never_created_for_prohibited():
    service = InMemoryCalendarService()
    with pytest.raises(CalendarServiceError):
        service.create_appointment(make_data(), make_assessment(Decision.PROHIBITED))
    assert service.check_availability(JUMP_DATE) is True


def test_create_appointment_requires_experienced_tandem_for_marginal():
    service = InMemoryCalendarService()
    with pytest.raises(CalendarServiceError):
        service.create_appointment(
            make_data(is_experienced_tandem=False), make_assessment(Decision.MARGINAL)
        )


def test_create_appointment_succeeds_for_marginal_with_experienced_tandem():
    service = InMemoryCalendarService()
    record = service.create_appointment(
        make_data(is_experienced_tandem=True), make_assessment(Decision.MARGINAL)
    )
    assert record.assessment.decision == Decision.MARGINAL


def test_create_appointment_rejects_mismatched_assessment_date():
    service = InMemoryCalendarService()
    other_day_weather = make_weather(date=date(2026, 10, 1))
    with pytest.raises(CalendarServiceError):
        service.create_appointment(make_data(), make_assessment(Decision.IDEAL, other_day_weather))


def test_create_appointment_is_idempotent_for_same_customer_and_date():
    service = InMemoryCalendarService()
    assessment = make_assessment(Decision.IDEAL)
    first = service.create_appointment(make_data(), assessment)
    second = service.create_appointment(make_data(), assessment)
    assert first.id == second.id


def test_create_appointment_fails_when_no_slots_left():
    service = InMemoryCalendarService(max_slots_per_day=1)
    assessment = make_assessment(Decision.IDEAL)
    service.create_appointment(make_data(customer_name="Cliente Uno"), assessment)
    with pytest.raises(CalendarServiceError):
        service.create_appointment(make_data(customer_name="Cliente Dos"), assessment)
