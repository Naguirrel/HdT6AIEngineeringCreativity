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
