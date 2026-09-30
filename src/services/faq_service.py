"""Carga y busqueda deterministica sobre la base de conocimiento de FAQs existente."""

import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path

_QA_PATTERN = re.compile(r"Q:\s*(?P<question>.+?)\s*\nA:\s*(?P<answer>.+?)(?=\n\s*\n|\Z)", re.DOTALL)
_CONTACT_PATTERN = re.compile(r"(?m)^5\. CONTACTO\s*\n(?P<body>[\s\S]*)\Z")
_STOP_WORDS = {
    "a", "al", "como", "con", "cual", "cuales", "cuanto", "de", "del", "donde",
    "el", "en", "es", "esta", "este", "hay", "la", "las", "lo", "los", "me",
    "mi", "para", "parachute", "persona", "por", "puedo", "que", "quiero",
    "sa", "salto", "saltar", "se", "su", "un", "una", "y", "evento",
}
_QUERY_ALIASES = {"pongo": "ropa", "ponerme": "ropa", "vestir": "ropa", "vestirme": "ropa", "vestimenta": "ropa"}


class FaqServiceError(RuntimeError):
    """La fuente de FAQs no existe, esta vacia o no se pudo interpretar."""


@dataclass(frozen=True)
class FaqEntry:
    question: str
    answer: str


def _normalize(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text.casefold())
    return "".join(char for char in decomposed if not unicodedata.combining(char))


def _terms(text: str, *, query: bool = False) -> set[str]:
    words = re.findall(r"[a-z0-9]+", _normalize(text))
    if query:
        words = [_QUERY_ALIASES.get(word, word) for word in words]
    return {word for word in words if len(word) > 2 and word not in _STOP_WORDS}


def load_knowledge_base_text(path: str | Path) -> str:
    faq_path = Path(path)
    try:
        content = faq_path.read_text(encoding="utf-8").strip()
    except FileNotFoundError as error:
        raise FaqServiceError(f"No se encontro el archivo FAQ: {faq_path}") from error

    if not content:
        raise FaqServiceError(f"El archivo FAQ esta vacio: {faq_path}")

    return content


def parse_faq_entries(knowledge_base_text: str) -> list[FaqEntry]:
    entries = [
        FaqEntry(question=match.group("question").strip(), answer=match.group("answer").strip())
        for match in _QA_PATTERN.finditer(knowledge_base_text)
    ]
    if not entries:
        raise FaqServiceError("No se encontraron pares Q/A en la fuente de FAQs.")
    contact = _CONTACT_PATTERN.search(knowledge_base_text)
    if contact:
        body = contact.group("body").strip()
        if body:
            entries.append(FaqEntry(question="Telefono, correo, redes sociales y sitio web de contacto", answer=body))
    return entries


@dataclass(frozen=True)
class FaqService:
    knowledge_base_text: str
    entries: list[FaqEntry]

    @classmethod
    def from_path(cls, path: str | Path) -> "FaqService":
        text = load_knowledge_base_text(path)
        return cls(knowledge_base_text=text, entries=parse_faq_entries(text))

    def search_faq(self, query: str, max_results: int = 3) -> list[FaqEntry]:
        """Busqueda por palabras clave (determinista) sobre las preguntas/respuestas conocidas."""
        clean_query = query.strip()
        if not clean_query:
            return []

        query_tokens = _terms(clean_query, query=True)
        if not query_tokens:
            return []

        entry_terms = [_terms(f"{entry.question} {entry.answer}") for entry in self.entries]
        document_frequency = {
            token: sum(token in terms for terms in entry_terms) for token in query_tokens
        }
        scored: list[tuple[int, FaqEntry]] = []
        for entry, terms in zip(self.entries, entry_terms):
            matches = query_tokens & terms
            if len(matches) >= 2 or (len(matches) == 1 and document_frequency[next(iter(matches))] == 1):
                scored.append((len(matches), entry))

        scored.sort(key=lambda pair: pair[0], reverse=True)
        return [entry for _, entry in scored[:max_results]]
