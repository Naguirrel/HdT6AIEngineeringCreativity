"""Keep user-facing text consistent with the appointments that really exist."""

import re

from src.agents.common.context import ParachuteContext
from src.agents.common.user_message import extract_dates, normalize_text
from src.domain.weather_models import Decision

_BOOKING_NOUN = r"(?:cita|reserva|reservacion|salto|turno|cupo|lugar)"
_DONE = r"(?:confirmad|cread|registrad|reservad|agendad|programad|apartad|asegurad)[oa]s?"
_CLAIM = re.compile(
    rf"\b{_BOOKING_NOUN}\b[^.!?\n]{{0,80}}\b{_DONE}\b"
    rf"|\b{_DONE}\b[^.!?\n]{{0,60}}\b{_BOOKING_NOUN}\b"
    r"|\b(?:he|hemos|ya)\s+(?:reservado|agendado|creado|registrado|confirmado|apartado)\b"
    r"|\b(?:reserve|agende|cree|registre|confirme|aparte)\s+(?:tu|la|su|el)\b"
    rf"|\b(?:tu|la|su)\s+{_BOOKING_NOUN}\s+(?:esta|quedo|ha quedado)\s+(?:lista|listo|hecha|hecho)\b"
)
# Conditional, negated or pending statements are not claims of a completed booking.
# Matched on casefolded text that keeps accents, so the conditional "si" differs from "sí".
_HEDGE = re.compile(
    r"\b(?:no|a[uú]n|todav[ií]a|sin|pendiente|falta|faltan|necesito|necesitamos|necesitaremos|para poder|"
    r"antes de|cuando|una vez|si|quedar[aá]|podr[aá]|podemos|puedo|deseas|quieres|confirma(?:s|r)?|"
    r"confirme(?:s)?|intent\w*|error|imposible|rechaz\w*)\b"
)
# A sentence ends at . ! ? followed by whitespace (not inside "28.1") or at a line break.
_SENTENCE = re.compile(r".+?(?:[.!?](?=\s|$)\s*|\n|$)", re.S)


def is_booking_claim(sentence: str) -> bool:
    plain = sentence.replace("*", "").replace("_", " ")
    return bool(_CLAIM.search(normalize_text(plain))) and not _HEDGE.search(plain.casefold())


def _claim_matches_records(context: ParachuteContext, sentence: str) -> bool:
    if not context.appointments:
        return False
    recorded = {record.data.jump_date for record in context.appointments}
    dates, _ambiguous = extract_dates(sentence, context.today())
    return all(value in recorded for value in dates)


def describe_booking_state(context: ParachuteContext) -> str:
    """Deterministic summary of what has and has not happened in the booking flow."""
    lines = ["Aun no se ha creado ninguna cita nueva en esta conversacion."]
    assessment = context.jump_assessment
    target = context.requested_date
    if assessment is None or target is None:
        lines.append("Falta evaluar el clima de la fecha solicitada (formato YYYY-MM-DD).")
    else:
        lines.append(f"Clima evaluado para {target.isoformat()}: {assessment.decision.value}.")
        if assessment.decision == Decision.PROHIBITED:
            lines.append("Las condiciones prohiben el salto; no se puede reservar ese dia.")
        elif assessment.decision == Decision.MARGINAL and context.confirmed_tandem_date != target:
            lines.append(
                "Falta tu confirmacion explicita del tandem con instructor experimentado; escribe: "
                f"'Acepto tandem experimentado para {target.isoformat()}'."
            )
        if assessment.allows_appointment:
            if context.availability_approved_date == target:
                lines.append("La disponibilidad ya fue aprobada.")
            else:
                lines.append("Falta comprobar la disponibilidad de cupo.")
    request = context.booking_request
    if request.blocked_reason:
        lines.append(f"La reserva no se pudo completar: {request.blocked_reason}")
    missing = [field for field in request.missing_fields() if field != "fecha"]
    if missing:
        lines.append("Faltan estos datos: " + ", ".join(missing) + ".")
    return " ".join(lines)


def enforce_truthful_booking_claims(context: ParachuteContext, text: str) -> str:
    """Drop sentences claiming an appointment that the calendar does not contain."""
    kept: list[str] = []
    removed = False
    for sentence in _SENTENCE.findall(text):
        if is_booking_claim(sentence) and not _claim_matches_records(context, sentence):
            removed = True
            continue
        kept.append(sentence)
    remaining = "".join(kept).strip()
    if not removed:
        return text
    status = describe_booking_state(context)
    return f"{remaining}\n\n{status}" if remaining else status
