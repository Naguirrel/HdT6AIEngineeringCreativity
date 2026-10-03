"""Tool compartido para consultar la base de FAQs existente."""

import hashlib

from agents import RunContextWrapper, function_tool

from src.agents.common.context import ParachuteContext, records_output
from src.observability import log_event


@records_output
def answer_from_faq(context: ParachuteContext, query: str) -> str:
    log_event(architecture=context.architecture, tool="search_faq")
    entries = context.services.faq_service.search_faq(query)
    context.record_faq_entries([{"question": entry.question, "answer": entry.answer} for entry in entries])
    context.record_tool_event(
        "search_faq",
        {"query_sha256": hashlib.sha256(query.encode("utf-8")).hexdigest(), "query_length": len(query)},
        {"match_count": len(entries)},
        "success",
    )
    if not entries:
        return "No se encontro informacion relacionada en las FAQs disponibles."
    return "\n\n".join(f"P: {entry.question}\nR: {entry.answer}" for entry in entries)


@function_tool
def search_faq(wrapper: RunContextWrapper[ParachuteContext], query: str) -> str:
    """Busca informacion relevante en las FAQs oficiales de Parachute S.A.

    Args:
        query: pregunta o palabras clave del usuario.
    """
    return answer_from_faq(wrapper.context, query)
