"""Carga y busqueda deterministica sobre la base de conocimiento de FAQs existente."""

import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path

_QA_PATTERN = re.compile(r"Q:\s*(?P<question>.+?)\s*\nA:\s*(?P<answer>.+?)(?=\n\s*\n|\Z)", re.DOTALL)


class FaqServiceError(RuntimeError):
    """La fuente de FAQs no existe, esta vacia o no se pudo interpretar."""


@dataclass(frozen=True)
class FaqEntry:
    question: str
    answer: str


def _normalize(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text.casefold())
    return "".join(char for char in decomposed if not unicodedata.combining(char))


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

        query_tokens = {token for token in _normalize(clean_query).split() if len(token) > 2}
        if not query_tokens:
            return []

        scored: list[tuple[int, FaqEntry]] = []
        for entry in self.entries:
            haystack = _normalize(f"{entry.question} {entry.answer}")
            score = sum(1 for token in query_tokens if token in haystack)
            if score > 0:
                scored.append((score, entry))

        scored.sort(key=lambda pair: pair[0], reverse=True)
        return [entry for _, entry in scored[:max_results]]
