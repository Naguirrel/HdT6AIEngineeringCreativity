# HDT5 — Orquestacion multiagente: Parachute S.A.

Tres arquitecturas de agentes (centralizada, jerarquica, descentralizada) que
resuelven el mismo problema de Parachute S.A. — responder FAQs del evento y
gestionar citas de salto validando el clima con Open-Meteo — reutilizando
exactamente el mismo nucleo de dominio, integraciones y tools. Lo unico que
cambia entre las tres es la estrategia de orquestacion de agentes.

## Demo en video

[Video demostrativo](https://youtu.be/vHEtqMTmSos) de las tres arquitecturas
funcionando contra Groq + Open-Meteo reales (FAQ, reserva con clima real,
fecha fuera de horizonte).

## Prerequisites

- Docker y Docker Compose (recomendado, no requiere instalar Python localmente).
- Alternativamente: Python 3.12 si prefieres correrlo sin Docker.
- Una API key compatible con la API de OpenAI Chat Completions para el LLM
  (por ejemplo [Groq](https://console.groq.com/), que ofrece un tier gratuito).
  El nucleo de dominio y sus tests **no** requieren ninguna API key.

## Installation

```bash
cp .env.example .env
# edita .env con tu LLM_API_KEY / LLM_BASE_URL / LLM_MODEL
docker compose build
```

## Environment variables

| Variable       | Requerida | Descripcion                                                        |
|----------------|-----------|---------------------------------------------------------------------|
| `LLM_API_KEY`  | si        | API key del proveedor compatible con OpenAI (Groq, OpenAI, etc.)     |
| `LLM_BASE_URL` | si        | URL base de la API, p.ej. `https://api.groq.com/openai/v1`          |
| `LLM_MODEL`    | si        | Id del modelo, p.ej. `openai/gpt-oss-20b`                            |
| `FAQ_PATH`     | no        | Ruta alterna al archivo de FAQs (por defecto `data/FAQs_...txt`)     |

Open-Meteo no requiere credenciales, por lo que no tiene variable de entorno.

## How to run tests

Los tests de dominio, integraciones y flujos de agentes son deterministas y
**no** llaman a ningun LLM real ni a Internet (Open-Meteo se mockea con
`requests-mock`), por lo que corren con variables de entorno ficticias:

```bash
docker compose --profile test run --rm tests
```

Sin Docker:

```bash
pip install -r requirements.txt
pytest
```

## How to run each architecture

Cada arquitectura arranca un chat interactivo por terminal (escribe `Bye` o
`Ctrl-C` para salir). Requieren un `.env` valido con credenciales de LLM reales.

```bash
# centralizada: un unico supervisor con especialistas expuestos via as_tool()
docker compose run --rm centralized

# jerarquica: Root Manager -> Knowledge/Booking Manager -> especialistas
docker compose run --rm hierarchical

# descentralizada: agentes que se transfieren el control via handoffs
docker compose run --rm decentralized
```

Sin Docker (con el `.env` cargado en el entorno):

```bash
python -m src.agents.centralized.main
python -m src.agents.hierarchical.main
python -m src.agents.decentralized.main
```

## Project structure

```
src/
  config.py              # coordenadas fijas, horizonte de pronostico, carga de .env
  domain/                # reglas puras: validacion de fecha y politica de seguridad
  integrations/          # cliente unico de Open-Meteo (sin reglas de negocio)
  services/              # WeatherService, CalendarService (in-memory), FaqService
  tools/                 # tools de agentes: envuelven los servicios, no duplican logica
  agents/
    common/               # contexto compartido, cliente de modelo (Groq), CLI
    centralized/main.py   # arquitectura 1
    hierarchical/main.py  # arquitectura 2
    decentralized/main.py # arquitectura 3
tests/
  unit/         # dominio y FAQ service (sin red)
  integration/  # Open-Meteo (mockeado), WeatherService, CalendarService
  agents/       # tools/flujo de negocio compartido + wiring de las 3 arquitecturas
data/           # FAQs oficiales de Parachute S.A. (reutilizadas del proyecto Sistema-RAG)
docs/diagrams/  # diagramas de las tres arquitecturas
```

## Weather rules

Politica deterministica (no depende del LLM), en `src/domain/weather_policy.py`:

| Variable            | Ideal    | Marginal   | Prohibido |
|---------------------|----------|------------|-----------|
| Viento superficie    | < 20 km/h | 20-28 km/h | > 28 km/h |
| Rafagas              | -        | -          | > 35 km/h |
| Precipitacion        | 0.0 mm   | -          | > 0.0 mm  |
| Cobertura de nubes   | < 30%    | 30-75%     | > 75%     |

Se aplica "peor condicion prevalece". `MARGINAL` exige confirmar tandem
experimentado antes de crear la cita; `PROHIBITED` nunca crea una cita. La
temperatura se obtiene y se muestra, pero no participa en la decision (el
enunciado no define un umbral).

El horizonte de pronostico valido es `hoy` hasta `hoy + 15 dias` (16 dias en
total, segun documenta Open-Meteo).

## Observability

`src/observability.py` provee logging estructurado (`architecture=... agent=...
tool=... requested_date=... weather_check_result=... jump_assessment=...
handoff=... calendar_write_attempt=... calendar_write_result=...`), usado por
los tools compartidos y el CLI de cada arquitectura. No registra secretos ni
el contenido libre del usuario. Tambien desactiva el exportador de trazas del
SDK (`set_tracing_disabled`), necesario porque no usamos una API key de OpenAI
para tracing.

## Manual end-to-end smoke test

`scripts/smoke_test.py` corre una conversacion real de 3 turnos (FAQ, reserva
con clima real, fecha fuera de horizonte) contra Groq + Open-Meteo reales para
las tres arquitecturas, y guarda la transcripcion en
`docs/smoke-test-output.txt`. No es parte de la suite de pytest porque
depende de red y de un LLM no determinista; es la verificacion end-to-end que
complementa a los 73 tests automatizados. La corrida grabada en el
[video demo](https://youtu.be/vHEtqMTmSos) usa este mismo script.

```bash
docker compose run --rm -v "$(pwd)/docs:/app/docs" centralized \
  python -m scripts.smoke_test /app/docs/smoke-test-output.txt
```

## Known limitations

- `CalendarService` es una implementacion in-memory pensada para demostrar el
  flujo (no persiste entre ejecuciones ni maneja concurrencia real).
- La busqueda de FAQs es por palabras clave sobre pares Q/A parseados del
  archivo de texto existente, no un retriever semantico.
- La arquitectura descentralizada, en la corrida real, a veces resuelve una
  reserva en mas turnos que las otras dos (el agente que recibe el handoff
  puede anunciar la transferencia antes de actuar); ver
  `docs/analisis-arquitecturas.md` seccion 2.2.

## Diagrams

Fuente editable en `docs/diagrams/*.mmd` (Mermaid); son los diagramas de las
tres arquitecturas mostrando agentes, `as_tool()`/handoffs, tools y los
servicios/integraciones compartidos.

## PDF deliverable

`docs/analisis-arquitecturas.md` (fuente) y `docs/analisis-arquitecturas.pdf`
(exportado) responden las dos preguntas obligatorias —que arquitectura
resuelve mejor el problema y si hace falta un sistema multiagente— con
evidencia real de la suite de tests y de `docs/smoke-test-output.txt`.
