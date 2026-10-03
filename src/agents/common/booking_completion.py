"""Finish bookings from trusted tool state and keep the final answer truthful.

The model decides when to talk to the user, but whether an appointment exists is decided
only by the calendar. Once weather, tandem confirmation (if MARGINAL), availability and
the user's data are all in place, the booking is completed with the real business tools.
"""

from agents import FunctionToolResult, RunContextWrapper, ToolsToFinalOutputResult

from src.agents.common.context import ParachuteContext
from src.agents.common.truthfulness import enforce_truthful_booking_claims
from src.tools.calendar_tools import book_appointment, evaluate_availability

# Tool names (business tools and as_tool() wrappers) that belong to the scheduling step.
SCHEDULING_TOOL_NAMES = {
    "check_appointment_availability", "create_appointment", "scheduling_specialist", "booking_manager",
}


def complete_pending_booking(context: ParachuteContext) -> str | None:
    """Create the requested appointment when every precondition is already satisfied."""
    if context.appointment_confirmation:
        return context.appointment_confirmation
    request = context.booking_request
    target = context.requested_date
    if (
        not request.requested or target is None or request.jump_date != target
        or request.missing_fields() or request.blocked_reason or context.booking_already_recorded()
    ):
        return None
    assessment = context.jump_assessment
    if assessment is None or not assessment.allows_appointment or context.assessment_checked_on != context.today():
        return None
    tandem = assessment.requires_experienced_tandem
    if tandem and context.confirmed_tandem_date != target:
        return None

    if not context.has_current_booking_approvals(target):
        evaluate_availability(context, target.isoformat())
        if not context.has_current_booking_approvals(target):
            request.blocked_reason = "no hay cupo aprobado para esa fecha."
            return None
    outcome = book_appointment(
        context, target.isoformat(), request.customer_name, request.contact, tandem,
        request.party_size if request.party_size is not None else 1,
    )
    if not context.appointment_confirmation:
        request.blocked_reason = outcome
    return context.appointment_confirmation


def booking_result_or_continue(
    wrapper: RunContextWrapper[ParachuteContext], tool_results: list[FunctionToolResult]
) -> ToolsToFinalOutputResult:
    """tool_use_behavior: end the run with the record-derived confirmation after a booking step."""
    if any(result.tool.name in SCHEDULING_TOOL_NAMES for result in tool_results):
        confirmation = complete_pending_booking(wrapper.context)
        if confirmation:
            return ToolsToFinalOutputResult(is_final_output=True, final_output=confirmation)
    return ToolsToFinalOutputResult(is_final_output=False, final_output=None)


def finish_turn(context: ParachuteContext, model_output: object) -> str:
    """Single exit point for CLI, evaluation and smoke test answers."""
    complete_pending_booking(context)
    if context.appointment_confirmation:
        return context.appointment_confirmation
    text = model_output if isinstance(model_output, str) else ""
    return enforce_truthful_booking_claims(context, text)
