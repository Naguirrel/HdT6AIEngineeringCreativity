"""Tests del flujo de negocio compartido detras de los tools de agentes.

Estas funciones (evaluate_jump_day, book_appointment, answer_from_faq) son las
que invocan las tres arquitecturas (centralizada, jerarquica, descentralizada),
por lo que probarlas aqui cubre el comportamiento comun a las tres.
"""

from datetime import date, timedelta

from tests.agents.conftest import make_snapshot

from src.domain.weather_models import Decision
from src.integrations.open_meteo import OpenMeteoError
from src.services.weather_service import WeatherService
from src.tools.calendar_tools import book_appointment, evaluate_availability
from src.tools.faq_tools import answer_from_faq
from src.tools.weather_tools import evaluate_jump_day

TOMORROW = date.today() + timedelta(days=1)


def test_answer_from_faq_returns_relevant_content(build_context):
    context = build_context({})
    answer = answer_from_faq(context, "edad minima")
    assert "P:" in answer and "R:" in answer


def test_answer_from_faq_handles_no_match(build_context):
    context = build_context({})
    answer = answer_from_faq(context, "xyzzyquantumteleportation")
    assert "No se encontro" in answer


def test_evaluate_jump_day_rejects_invalid_format(build_context):
    context = build_context({})
    result = evaluate_jump_day(context, "29/09/2026")
    assert "invalido" in result
    assert context.jump_assessment is None


def test_evaluate_jump_day_stores_assessment_in_context(build_context):
    context = build_context({TOMORROW: make_snapshot(TOMORROW)})
    result = evaluate_jump_day(context, TOMORROW.isoformat())
    assert "IDEAL" in result
    assert context.jump_assessment is not None
    assert context.jump_assessment.decision == Decision.IDEAL
    assert context.requested_date == TOMORROW


def test_evaluate_jump_day_rejects_date_outside_horizon(build_context):
    context = build_context({})
    too_far = date.today() + timedelta(days=200)
    result = evaluate_jump_day(context, too_far.isoformat())
    assert "Error" in result
    assert context.jump_assessment is None


def test_create_appointment_refused_without_prior_weather_check(build_context):
    context = build_context({})
    result = book_appointment(context, TOMORROW.isoformat(), "Juan Perez", "juan@example.com")
    assert "primero debes ejecutar check_jump_day" in result
    assert context.appointment_record is None


def test_create_appointment_succeeds_after_ideal_weather_check(build_context):
    context = build_context({TOMORROW: make_snapshot(TOMORROW)})
    evaluate_jump_day(context, TOMORROW.isoformat())

    result = book_appointment(context, TOMORROW.isoformat(), "Juan Perez", "juan@example.com")

    assert "Cita confirmada" in result
    assert context.appointment_record is not None


def test_create_appointment_blocked_for_prohibited_weather(build_context):
    context = build_context({TOMORROW: make_snapshot(TOMORROW, precipitation_mm=1.0)})
    evaluate_jump_day(context, TOMORROW.isoformat())

    result = book_appointment(context, TOMORROW.isoformat(), "Juan Perez", "juan@example.com")

    assert "No se pudo crear la cita" in result
    assert context.appointment_record is None


def test_create_appointment_requires_experienced_tandem_for_marginal(build_context):
    context = build_context({TOMORROW: make_snapshot(TOMORROW, wind_speed_10m_kmh=25.0)})
    evaluate_jump_day(context, TOMORROW.isoformat())

    refused = book_appointment(context, TOMORROW.isoformat(), "Juan Perez", "juan@example.com", is_experienced_tandem=False)
    assert "No se pudo crear la cita" in refused
    assert context.appointment_record is None

    confirmed = book_appointment(context, TOMORROW.isoformat(), "Juan Perez", "juan@example.com", is_experienced_tandem=True)
    assert "Cita confirmada" in confirmed
    assert context.appointment_record is not None


def test_create_appointment_is_idempotent(build_context):
    context = build_context({TOMORROW: make_snapshot(TOMORROW)})
    evaluate_jump_day(context, TOMORROW.isoformat())

    first = book_appointment(context, TOMORROW.isoformat(), "Juan Perez", "juan@example.com")
    second = book_appointment(context, TOMORROW.isoformat(), "Juan Perez", "juan@example.com")

    assert context.appointment_record is not None
    first_id = context.appointment_record.id
    book_appointment(context, TOMORROW.isoformat(), "Juan Perez", "juan@example.com")
    assert context.appointment_record.id == first_id
    assert first and second


def test_evaluate_availability_reports_no_slots_left(build_context):
    context = build_context({TOMORROW: make_snapshot(TOMORROW)})
    context.services.calendar_service.max_slots_per_day = 1
    evaluate_jump_day(context, TOMORROW.isoformat())
    book_appointment(context, TOMORROW.isoformat(), "Cliente Uno", "uno@example.com")

    result = evaluate_availability(context, TOMORROW.isoformat())
    assert "No hay cupo disponible" in result


def test_failed_new_weather_check_cannot_reuse_previous_assessment(build_context):
    other_day = TOMORROW + timedelta(days=1)
    context = build_context({TOMORROW: make_snapshot(TOMORROW)})
    assert "IDEAL" in evaluate_jump_day(context, TOMORROW.isoformat())

    class FailingClient:
        def get_weather(self, requested_date):
            raise OpenMeteoError("simulated outage")

    context.services.weather_service = WeatherService(FailingClient(), max_horizon_days=15)
    assert "Error" in evaluate_jump_day(context, other_day.isoformat())
    assert context.requested_date is None
    assert context.jump_assessment is None
    for attempted_day in (other_day, TOMORROW):
        result = book_appointment(context, attempted_day.isoformat(), "Juan Perez", "juan@example.com")
        assert "No se puede crear" in result
    assert context.services.calendar_service.check_availability(TOMORROW)


def test_booking_requires_explicit_matching_date(build_context):
    context = build_context({TOMORROW: make_snapshot(TOMORROW)})
    evaluate_jump_day(context, TOMORROW.isoformat())
    other_day = TOMORROW + timedelta(days=1)
    result = book_appointment(context, other_day.isoformat(), "Juan Perez", "juan@example.com")
    assert "no coincide" in result
    assert context.appointment_record is None


def test_invalid_new_date_clears_previous_assessment(build_context):
    context = build_context({TOMORROW: make_snapshot(TOMORROW)})
    evaluate_jump_day(context, TOMORROW.isoformat())
    assert "invalido" in evaluate_jump_day(context, "not-a-date")
    assert context.jump_assessment is None
    assert "No se puede crear" in book_appointment(
        context, TOMORROW.isoformat(), "Juan Perez", "juan@example.com"
    )


def test_out_of_range_new_date_clears_previous_assessment(build_context):
    context = build_context({TOMORROW: make_snapshot(TOMORROW)})
    evaluate_jump_day(context, TOMORROW.isoformat())
    assert "Error" in evaluate_jump_day(context, (TOMORROW + timedelta(days=30)).isoformat())
    assert context.jump_assessment is None


def test_booking_tool_reports_invalid_input_without_using_capacity(build_context):
    context = build_context({TOMORROW: make_snapshot(TOMORROW)})
    evaluate_jump_day(context, TOMORROW.isoformat())
    result = book_appointment(context, TOMORROW.isoformat(), "   ", "juan@example.com", party_size=0)
    assert "nombre" in result
    assert context.appointment_record is None
    assert context.services.calendar_service.check_availability(TOMORROW)
