"""Smoke test manual (no pytest): corre una conversacion real contra Groq + Open-Meteo
para cada arquitectura y deja evidencia en docs/smoke-test-output.txt.

No forma parte de la suite automatizada porque depende de red y de un LLM real
(no deterministico); es la verificacion end-to-end pedida en la seccion 17 del
plan, corrida una vez para recolectar evidencia real de comportamiento.
"""

import asyncio
import sys
from datetime import date, timedelta

from agents import Runner

from src.agents.centralized.main import build_supervisor
from src.agents.decentralized.main import build_entry_agent
from src.agents.hierarchical.main import build_root_manager
from src.observability import configure_logging

VALID_DATE = (date.today() + timedelta(days=3)).isoformat()
OUT_OF_RANGE_DATE = (date.today() + timedelta(days=200)).isoformat()

SCRIPT = [
    "¿Cuál es la edad mínima para poder saltar?",
    f"Quiero saltar el {VALID_DATE}, ¿se puede? Si es posible resérvame, mi nombre es Ana Lopez y mi contacto es ana@example.com.",
    f"¿Puedo reservar para el {OUT_OF_RANGE_DATE}?",
]


async def run_architecture(name: str, starting_agent, context) -> list[str]:
    lines = [f"=== {name} ==="]
    current_agent = starting_agent
    history: list[dict] = []
    for turn in SCRIPT:
        history.append({"role": "user", "content": turn})
        lines.append(f"Usuario: {turn}")
        try:
            result = await Runner.run(current_agent, history, context=context)
        except Exception as error:
            lines.append(f"[ERROR] {error}")
            continue
        lines.append(f"[{result.last_agent.name}]: {result.final_output}")
        history = result.to_input_list()
        current_agent = result.last_agent
    lines.append("")
    return lines


async def main() -> None:
    configure_logging()

    supervisor, ctx1 = build_supervisor()
    root_manager, ctx2 = build_root_manager()
    entry_agent, ctx3 = build_entry_agent()

    all_lines: list[str] = []
    for name, agent, context in (
        ("centralized", supervisor, ctx1),
        ("hierarchical", root_manager, ctx2),
        ("decentralized", entry_agent, ctx3),
    ):
        all_lines.extend(await run_architecture(name, agent, context))

    output = "\n".join(all_lines)
    print(output)
    output_path = sys.argv[1] if len(sys.argv) > 1 else "docs/smoke-test-output.txt"
    with open(output_path, "w", encoding="utf-8") as handle:
        handle.write(output)


if __name__ == "__main__":
    asyncio.run(main())
