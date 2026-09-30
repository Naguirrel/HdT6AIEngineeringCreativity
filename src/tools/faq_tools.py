"""Tool compartido para consultar la base de FAQs existente."""

from agents import RunContextWrapper, function_tool

from src.agents.common.context import ParachuteContext
from src.observability import log_event


def answer_from_faq(context: ParachuteContext, query: str) -> str:
    log_event(architecture=context.architecture, tool="search_faq")
    entries = context.services.faq_service.search_faq(query)
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
