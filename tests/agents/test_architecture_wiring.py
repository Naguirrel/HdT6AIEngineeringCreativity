"""Verifica que las tres arquitecturas esten realmente diferenciadas y compartan
el mismo nucleo de dominio/servicios, sin necesidad de llamar a un LLM real.
"""

import pytest

from agents import Agent

from src.agents.centralized.main import build_supervisor
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
