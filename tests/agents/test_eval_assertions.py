from evals.assertions.tool_trace import get_assert


def _context(events, **variables):
    return {
        "metadata": {
            "tool_calls": events,
            "retrieved_context": [{"question": "Q", "answer": "A"}],
            "real_open_meteo_contacted": False,
        },
        "vars": variables,
    }


def test_tool_assertion_checks_presence_absence_and_context():
    events = [{"tool": "search_faq", "sequence": 1}]
    passed = get_assert("respuesta", _context(events, expect_tools=["search_faq"],
                                             forbid_tools=["create_appointment"],
                                             min_retrieved_context=1))
    assert passed["pass"] is True
    assert get_assert("respuesta", _context([], expect_tools=["search_faq"]))["pass"] is False
    assert get_assert("respuesta", _context(events, forbid_tools=["search_faq"]))["pass"] is False


def test_tool_assertion_fails_closed_without_metadata():
    assert get_assert("respuesta", {"vars": {}})["pass"] is False


def test_tool_assertion_checks_counts_and_order():
    events = [
        {"tool": "check_jump_day"},
        {"tool": "check_appointment_availability"},
        {"tool": "create_appointment"},
    ]
    variables = {
        "expect_tool_counts": {"create_appointment": 1},
        "expect_tool_order": ["check_jump_day", "check_appointment_availability", "create_appointment"],
    }
    assert get_assert("ok", _context(events, **variables))["pass"] is True
    assert get_assert("ok", _context(events[::-1], **variables))["pass"] is False


def test_tool_assertion_checks_arguments_results_status_and_hashed_identity():
    import hashlib

    events = [{
        "tool": "create_appointment",
        "arguments": {
            "date_str": "2026-09-20",
            "party_size": 2,
            "customer_name_sha256": hashlib.sha256(b"Ana Ejemplo").hexdigest(),
            "contact_sha256": hashlib.sha256(b"ana@example.invalid").hexdigest(),
        },
        "result": {"created": True},
        "status": "success",
    }]
    variables = {
        "expect_customer_name": "Ana Ejemplo",
        "expect_contact": "ana@example.invalid",
        "expect_tool_events": [{"tool": "create_appointment", "arguments": {"party_size": 2},
                                "result": {"created": True}, "status": "success"}],
    }
    assert get_assert("ok", _context(events, **variables))["pass"] is True
    assert get_assert("ok", _context(events, **{**variables, "expect_contact": "wrong"}))["pass"] is False
    assert get_assert("ok", _context(events, expect_tool_events=[{"tool": "create_appointment",
                                                                  "result": {"created": False}}]))["pass"] is False


def test_tool_assertion_rejects_unexpected_tandem_confirmation():
    context = _context([], forbid_tandem_confirmation=True)
    assert get_assert("ok", context)["pass"] is True
    context["metadata"]["confirmed_tandem_date"] = "2026-09-20"
    assert get_assert("ok", context)["pass"] is False


def test_tool_assertion_requires_weather_before_successful_booking():
    create = {"tool": "create_appointment", "status": "success", "arguments": {"date_str": "2026-09-20"}}
    check = {"tool": "check_jump_day", "status": "success", "result": {"date": "2026-09-20"}}
    assert get_assert("ok", _context([check, create], require_assessed_before_create=True))["pass"] is True
    assert get_assert("ok", _context([create, check], require_assessed_before_create=True))["pass"] is False
