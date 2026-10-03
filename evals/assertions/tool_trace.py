"""Promptfoo assertion that checks real business-tool events in provider metadata."""

from collections import Counter
import hashlib


def _result(passed: bool, reason: str):
    return {"pass": passed, "score": 1 if passed else 0, "reason": reason}


def get_assert(output: str, context: dict):
    metadata = context.get("metadata") or (context.get("providerResponse") or {}).get("metadata")
    if not isinstance(metadata, dict) or not isinstance(metadata.get("tool_calls"), list):
        return _result(False, "Falta metadata estructurada de tool_calls")
    events = metadata["tool_calls"]
    variables = context.get("vars", {})
    names = [event.get("tool") for event in events]
    counts = Counter(names)

    for tool in variables.get("expect_tools", []):
        if counts[tool] == 0:
            return _result(False, f"Falta la herramienta {tool}")
    for tool in variables.get("forbid_tools", []):
        if counts[tool] != 0:
            return _result(False, f"Herramienta prohibida ejecutada: {tool}")
    if "expect_tool_counts" in variables:
        for tool, expected in variables["expect_tool_counts"].items():
            if counts[tool] != expected:
                return _result(False, f"{tool}: {counts[tool]} ejecuciones; se esperaban {expected}")
    if "expect_tool_order" in variables:
        expected = variables["expect_tool_order"]
        if names != expected:
            return _result(False, f"Orden observado {names}; esperado {expected}")
    if "min_retrieved_context" in variables:
        retrieved = metadata.get("retrieved_context")
        if not isinstance(retrieved, list) or len(retrieved) < variables["min_retrieved_context"]:
            return _result(False, "El contexto FAQ recuperado es insuficiente")
    for specification in variables.get("expect_tool_events", []):
        matching = [event for event in events if event.get("tool") == specification["tool"]]
        occurrence = specification.get("occurrence", 0)
        if occurrence >= len(matching):
            return _result(False, f"Falta evento {specification['tool']} #{occurrence + 1}")
        event = matching[occurrence]
        for field in ("arguments", "result"):
            for key, expected_value in specification.get(field, {}).items():
                if (event.get(field) or {}).get(key) != expected_value:
                    return _result(False, f"{specification['tool']}.{field}.{key} no coincide")
        if "status" in specification and event.get("status") != specification["status"]:
            return _result(False, f"Estado inesperado de {specification['tool']}")
    if "expect_customer_name" in variables or "expect_contact" in variables:
        bookings = [event for event in events if event.get("tool") == "create_appointment"]
        if not bookings:
            return _result(False, "No se intentó crear la cita con datos de cliente")
        arguments = bookings[-1].get("arguments") or {}
        for variable, key in (("expect_customer_name", "customer_name_sha256"),
                              ("expect_contact", "contact_sha256")):
            if variable in variables:
                digest = hashlib.sha256(variables[variable].strip().encode("utf-8")).hexdigest()
                if arguments.get(key) != digest:
                    return _result(False, f"No coincide el dato ficticio {variable}")
    if "expect_confirmed_tandem_date" in variables:
        if metadata.get("confirmed_tandem_date") != variables["expect_confirmed_tandem_date"]:
            return _result(False, "La confirmación tándem no corresponde a la fecha evaluada")
    if variables.get("forbid_tandem_confirmation") and metadata.get("confirmed_tandem_date") is not None:
        return _result(False, "Se registró una confirmación tándem que el usuario no dio para esa fecha")
    if "expect_weather_requests" in variables:
        if metadata.get("weather_requests") != variables["expect_weather_requests"]:
            return _result(False, "Consultas meteorológicas simuladas inesperadas")
    if variables.get("require_assessed_before_create"):
        assessed = None
        for event in events:
            if event.get("tool") == "check_jump_day":
                assessed = (event.get("result") or {}).get("date") if event.get("status") == "success" else None
            if event.get("tool") == "create_appointment" and event.get("status") == "success":
                if (event.get("arguments") or {}).get("date_str") != assessed:
                    return _result(False, "Cita creada antes de evaluar el clima de esa fecha")
    if metadata.get("real_open_meteo_contacted") is not False:
        return _result(False, "No hay prueba de aislamiento de Open-Meteo")
    return _result(True, "Traza de herramientas verificada")
