"""Deterministic extraction of booking data from the user's own words.

The supervisor delegates through as_tool(), so specialists only receive the text the
supervisor chooses to forward. Keeping the user's data in the context avoids losing
name, contact, party size or date between turns and nested agents.
"""

from dataclasses import dataclass
from datetime import date
import re
import unicodedata

_DASHES = re.compile(r"[‐-―−]")
_ISO_DATE = re.compile(r"(?<!\d)(\d{4})-(\d{1,2})-(\d{1,2})(?!\d)")
_EMAIL = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")
_PHONE = re.compile(r"(?<![\w+])(\+\d[\d\s\-]{6,16}\d|\d{4}[\s\-]?\d{4})(?![\w])")
_NAME_WORD = r"[A-ZÁÉÍÓÚÑÜ][a-záéíóúñü'\-]+"
_FULL_NAME = rf"{_NAME_WORD}(?:\s+{_NAME_WORD}){{1,3}}"
_NAME_PATTERNS = (
    re.compile(rf"\b(?:a nombre de|mi nombre es|me llamo|nombre:)\s+({_NAME_WORD}(?:\s+{_NAME_WORD}){{0,3}})"),
    re.compile(rf"\bpara\s+({_FULL_NAME})"),
    re.compile(rf":\s*({_FULL_NAME})\s*,"),
)
_NUMBER_WORDS = {
    "un": 1, "una": 1, "uno": 1, "dos": 2, "tres": 3, "cuatro": 4, "cinco": 5,
    "seis": 6, "siete": 7, "ocho": 8, "nueve": 9, "diez": 10,
}
_PARTY_SIZE = re.compile(
    r"\b(?:somos|seremos|para)?\s*(-?\d{1,3}|" + "|".join(_NUMBER_WORDS) + r")\s+(?:personas?|participantes?|saltadores?)\b"
)
_BOOKING_INTENT = re.compile(r"\b(?:reserv\w*|agend\w*|cita|apart\w*|confirma la cita)\b")


def normalize_text(text: str) -> str:
    """Casefold, strip accents and unify Unicode dashes and spaces."""
    decomposed = unicodedata.normalize("NFKD", text.casefold())
    without_marks = "".join(char for char in decomposed if not unicodedata.combining(char))
    return re.sub(r"\s+", " ", _DASHES.sub("-", without_marks))


def find_iso_dates(text: str) -> tuple[list[date], bool]:
    """Return valid ISO dates in the text and whether an invalid ISO-like value appeared."""
    found: list[date] = []
    ambiguous = False
    for year, month, day in _ISO_DATE.findall(_DASHES.sub("-", text)):
        try:
            found.append(date(int(year), int(month), int(day)))
        except ValueError:
            ambiguous = True
    return found, ambiguous


@dataclass(frozen=True)
class MessageDetails:
    dates: tuple[date, ...] = ()
    ambiguous_date: bool = False
    customer_name: str | None = None
    contact: str | None = None
    party_size: int | None = None
    booking_intent: bool = False


def extract_booking_details(message: str) -> MessageDetails:
    dates, ambiguous = find_iso_dates(message)
    normalized = normalize_text(message)

    contact = None
    email = _EMAIL.search(message)
    if email:
        contact = email.group(0)
    else:
        phone = _PHONE.search(_DASHES.sub("-", message))
        if phone:
            contact = phone.group(1).strip()

    booking_words = bool(_BOOKING_INTENT.search(normalized))
    name = None
    # "para Nombre Apellido" only names a customer when the message is about a booking.
    for pattern in _NAME_PATTERNS if booking_words else _NAME_PATTERNS[:1]:
        match = pattern.search(message)
        if match:
            name = match.group(1).strip()
            break

    party_size = None
    party = _PARTY_SIZE.search(normalized)
    if party:
        token = party.group(1)
        party_size = _NUMBER_WORDS.get(token, None) if not token.lstrip("-").isdigit() else int(token)

    intent = booking_words and "?" not in message
    return MessageDetails(
        dates=tuple(dates), ambiguous_date=ambiguous, customer_name=name,
        contact=contact, party_size=party_size, booking_intent=intent,
    )
