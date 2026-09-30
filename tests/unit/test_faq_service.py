from pathlib import Path

import pytest

from src.services.faq_service import (
    FaqService,
    FaqServiceError,
    load_knowledge_base_text,
    parse_faq_entries,
)

FAQ_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "FAQs_Parachute_SA_Guatemala_2026.txt"


def test_load_existing_faq_file_returns_content():
    content = load_knowledge_base_text(FAQ_PATH)
    assert "PARACHUTE S.A." in content


def test_load_missing_file_raises():
    with pytest.raises(FaqServiceError):
        load_knowledge_base_text("does-not-exist.txt")


def test_load_empty_file_raises(tmp_path):
    empty_file = tmp_path / "empty.txt"
    empty_file.write_text("", encoding="utf-8")
    with pytest.raises(FaqServiceError):
        load_knowledge_base_text(empty_file)


def test_parse_entries_from_real_faq_file():
    content = load_knowledge_base_text(FAQ_PATH)
    entries = parse_faq_entries(content)
    assert len(entries) >= 10
    assert all(entry.question and entry.answer for entry in entries)


def test_parse_entries_without_qa_pairs_raises():
    with pytest.raises(FaqServiceError):
        parse_faq_entries("Este texto no tiene preguntas frecuentes.")


def test_search_faq_finds_relevant_entry():
    service = FaqService.from_path(FAQ_PATH)
    results = service.search_faq("edad minima para saltar")
    assert results
    assert any("edad" in entry.question.lower() for entry in results)


def test_search_faq_no_match_returns_empty():
    service = FaqService.from_path(FAQ_PATH)
    results = service.search_faq("xyzzyquantumteleportation")
    assert results == []


def test_search_faq_ignores_accents_and_case():
    service = FaqService.from_path(FAQ_PATH)
    lower = service.search_faq("PESO MAXIMO")
    accented = service.search_faq("peso máximo")
    assert lower and accented
    assert {entry.question for entry in lower} == {entry.question for entry in accented}


def test_search_faq_respects_max_results():
    service = FaqService.from_path(FAQ_PATH)
    results = service.search_faq("salto", max_results=2)
    assert len(results) <= 2
