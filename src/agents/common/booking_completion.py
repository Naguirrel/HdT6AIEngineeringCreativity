"""Finish a successful booking from trusted tool state, without another model turn."""

from agents import FunctionToolResult, RunContextWrapper, ToolsToFinalOutputResult

from src.agents.common.context import ParachuteContext


def booking_result_or_continue(
    wrapper: RunContextWrapper[ParachuteContext], tool_results: list[FunctionToolResult]
) -> ToolsToFinalOutputResult:
    confirmation = wrapper.context.appointment_confirmation
    booking_tools = {"create_appointment", "scheduling_specialist", "booking_manager"}
    if confirmation and any(result.tool.name in booking_tools for result in tool_results):
        return ToolsToFinalOutputResult(is_final_output=True, final_output=confirmation)
    return ToolsToFinalOutputResult(is_final_output=False, final_output=None)


def final_answer(context: ParachuteContext, model_output: object) -> str:
    """Keep the user-facing answer tied to a booking that actually succeeded."""
    if context.appointment_confirmation:
        return context.appointment_confirmation
    return model_output if isinstance(model_output, str) else ""
