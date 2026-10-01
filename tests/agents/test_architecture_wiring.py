"""Verifica que las tres arquitecturas esten realmente diferenciadas y compartan
el mismo nucleo de dominio/servicios, sin necesidad de llamar a un LLM real.
"""

import pytest

from agents import Agent

from src.agents.centralized.main import build_supervisor
from src.agents.common.model_client import build_model
from src.agents.common.specialist_agents import build_faq_agent, build_scheduling_agent
from src.agents.decentralized.main import build_decentralized_agents
from src.agents.hierarchical.main import build_root_manager
from src.config import load_config


@pytest.fixture(autouse=True)
def llm_env(monkeypatch):
    monkeypatch.setenv("LLM_API_KEY", "test-key")
    monkeypatch.setenv("LLM_BASE_URL", "https://example.invalid/v1")
    monkeypatch.setenv("LLM_MODEL", "test-model")


def test_centralized_supervisor_exposes_three_specialists_as_tools():
    supervisor, context = build_supervisor()
    tool_names = {tool.name for tool in supervisor.tools}
    assert tool_names == {"faq_specialist", "weather_specialist", "scheduling_specialist"}
    assert context.services.faq_service.entries


def test_centralized_supervisor_instructions_enforce_domain_boundary():
    supervisor, _context = build_supervisor()
    instructions = " ".join(supervisor.instructions.casefold().split())
    assert "fuera de ese dominio" in instructions
    assert "no respondas con conocimiento general" in instructions
    assert "solo puedes ayudar con parachute s.a., sus faqs o citas" in instructions
    assert "saludos, despedidas y preguntas claramente fuera del dominio" in instructions
    assert "no invoques faq_specialist, weather_specialist ni scheduling_specialist" in instructions
    assert "delega siempre a faq_specialist antes de responder" in instructions
    assert "no respondas con memoria propia" in instructions
    assert "copia fielmente los datos exactos" in instructions
    assert "si el especialista no encuentra el dato solicitado" in instructions
    assert "prioriza el grupo indicado por el usuario" in instructions
    assert "no presentes la regla general como requisito absoluto" in instructions
    assert "las solicitudes de cita son parte de tu dominio" in instructions
    assert "nunca respondas a una reserva con la negativa" in instructions
    assert "check_jump_day, check_appointment_availability y create_appointment" in instructions
    assert "si create_appointment confirma la cita, comunica fielmente el resultado y su fecha" in instructions
    assert {tool.name for tool in supervisor.tools} == {
        "faq_specialist", "weather_specialist", "scheduling_specialist"
    }


def test_faq_specialist_grounding_contract():
    faq_agent = build_faq_agent(build_model(load_config()))
    instructions = " ".join(faq_agent.instructions.casefold().split())
    assert "usa siempre la herramienta search_faq" in instructions
    assert "responde exclusivamente con los datos devueltos por search_faq" in instructions
    assert "numeros telefonicos, correos, fechas, direcciones" in instructions
    assert "no completes datos con ejemplos comunes ni conocimiento general" in instructions
    assert "si el contexto no contiene el dato solicitado" in instructions
    assert "identifica el grupo del usuario y prioriza sus requisitos" in instructions
    assert "no presentes una regla general y su excepcion como obligaciones simultaneas" in instructions
    assert faq_agent.tool_use_behavior == "stop_on_first_tool"
    assert [tool.name for tool in faq_agent.tools] == ["search_faq"]


def test_scheduling_specialist_requires_complete_workflow():
    agent = build_scheduling_agent(build_model(load_config()))
    instructions = " ".join(agent.instructions.casefold().split())
    assert "check_jump_day, despues check_appointment_availability y finalmente create_appointment" in instructions
    assert "no llames create_appointment si la disponibilidad no fue comprobada y aprobada" in instructions
    assert "si la herramienta confirma la cita, informa el exito y la fecha" in instructions


def test_hierarchical_root_manager_has_two_levels():
    root_manager, _context = build_root_manager()
    root_tool_names = {tool.name for tool in root_manager.tools}
    assert root_tool_names == {"knowledge_manager", "booking_manager"}
    assert "faq_specialist" not in root_tool_names
    assert "weather_specialist" not in root_tool_names


def test_decentralized_agents_are_wired_with_handoffs():
    config = load_config()
    from src.agents.common.model_client import build_model

    model = build_model(config)
    faq_agent, weather_agent, scheduling_agent = build_decentralized_agents(model)

    faq_handoff_targets = {h.agent_name for h in faq_agent.handoffs}
    weather_handoff_targets = {h.agent_name for h in weather_agent.handoffs}
    scheduling_handoff_targets = {h.agent_name for h in scheduling_agent.handoffs}

    assert faq_handoff_targets == {"Weather Agent"}
    assert weather_handoff_targets == {"FAQ Agent", "Scheduling Agent"}
    assert scheduling_handoff_targets == {"FAQ Agent"}


def test_decentralized_has_no_permanent_global_supervisor():
    config = load_config()
    from src.agents.common.model_client import build_model

    model = build_model(config)
    faq_agent, weather_agent, scheduling_agent = build_decentralized_agents(model)

    for agent in (faq_agent, weather_agent, scheduling_agent):
        assert isinstance(agent, Agent)
        tool_names = {tool.name for tool in agent.tools}
        assert tool_names.isdisjoint({"faq_specialist", "weather_specialist", "scheduling_specialist"})
