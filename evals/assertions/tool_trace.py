"""Promptfoo assertion that checks real business-tool events in provider metadata."""

from collections import Counter


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
        relevant = [name for name in names if name in expected]
        if relevant != expected:
            return _result(False, f"Orden observado {relevant}; esperado {expected}")
    if "min_retrieved_context" in variables:
        retrieved = metadata.get("retrieved_context")
        if not isinstance(retrieved, list) or len(retrieved) < variables["min_retrieved_context"]:
            return _result(False, "El contexto FAQ recuperado es insuficiente")
    if metadata.get("real_open_meteo_contacted") is not False:
        return _result(False, "No hay prueba de aislamiento de Open-Meteo")
    return _result(True, "Traza de herramientas verificada")
