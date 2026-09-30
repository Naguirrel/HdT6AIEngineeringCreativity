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
| `LLM_GRADER_MODEL` | para evals | Modelo de `factuality`; en Groq, p.ej. `llama-3.1-8b-instant` |
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

Cada `ParachuteContext` conserva una traza estructurada de las cuatro tools de
negocio (`search_faq`, `check_jump_day`, `check_appointment_availability`,
`create_appointment`). `context.get_tool_trace()` devuelve eventos ordenados con
`sequence`, `tool`, `arguments`, `result` y `status`. Las consultas FAQ se
representan por longitud y SHA-256; nombre y contacto se representan por
indicadores de presencia y SHA-256. La traza pertenece al contexto de la sesion y no contiene los
valores de credenciales ni datos de contacto completos. Las delegaciones
`as_tool()` y los handoffs del SDK no se incluyen en esta traza de negocio;
su instrumentacion requiere observar eventos del Runner en una capa separada.

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

## Evaluaciones con Promptfoo

La hoja de evaluaciones prueba el supervisor **centralizado** porque recibe
todas las solicitudes y delega las consultas FAQ, clima y calendario mediante
`as_tool()`. El provider de Python en `evals/provider.py` construye ese
supervisor real en cada caso mediante `src/agents/centralized/evaluation.py`.
Cada caso obtiene contexto, historial, calendario y traza nuevos. `turns`
admite un mensaje o una lista para sesiones de varios turnos. La salida de
Promptfoo es solo la respuesta final; `metadata` contiene eventos de las
herramientas, contexto FAQ recuperado, fecha de confirmacion tandem y
duracion total. Las delegaciones `as_tool()` no aparecen en la traza de
herramientas de negocio.

### Requisitos e instalacion

- Python 3.12 con las dependencias de `requirements.txt`.
- Node.js 22.22.0 o superior; Node 24 LTS recomendado.
- `LLM_API_KEY`, `LLM_BASE_URL` y `LLM_MODEL` para el agente; al ejecutar
  evaluaciones con `factuality`, también `LLM_GRADER_MODEL`. `FAQ_PATH` es
  opcional. No se versionan claves.
- `PROMPTFOO_PYTHON` selecciona el Python del entorno virtual. En equipos con
  directorio de usuario restringido, `PROMPTFOO_CONFIG_DIR` puede señalar un
  directorio local ignorado por Git. `PROMPTFOO_DISABLE_TELEMETRY=1` desactiva
  la telemetria opcional.

### Configuración local en PowerShell

Desde la raíz del repositorio, instala las dependencias declaradas. Si aún no
existe `.venv`, créalo con Python 3.12 (`py -3.12 -m venv .venv`).

```powershell
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
npm ci

$env:PROMPTFOO_PYTHON = (Resolve-Path ".\.venv\Scripts\python.exe").Path
$env:PROMPTFOO_CONFIG_DIR = Join-Path (Resolve-Path .venv).Path "promptfoo-state"
$env:TEMP = Join-Path (Resolve-Path .venv).Path "tmp"
$env:TMP = $env:TEMP
New-Item -ItemType Directory -Force $env:TEMP | Out-Null
```

Estas variables solo existen en la sesión actual de PowerShell: al abrir otra
terminal hay que configurarlas nuevamente. Antes de Promptfoo, comprueba que
usa el Python con el SDK de agentes instalado:

```powershell
& "$env:PROMPTFOO_PYTHON" -c "import sys, agents; print(sys.executable); print(agents.__file__)"
```

Si `PROMPTFOO_PYTHON` apunta fuera de `.venv`, puede aparecer
`ModuleNotFoundError: No module named 'agents'`. La instalación por sí sola no
configura esa variable para terminales futuras.

Configura las cuatro variables `LLM_*` mediante un gestor de secretos o un archivo
`.env` local ignorado por Git. Promptfoo admite `--env-file .env` al ejecutar
los scripts; el archivo debe contener los valores reales en el equipo del
operador. El modelo evaluado usa el SDK de OpenAI Agents y `LLM_*`. El
evaluador de `factuality` es otro provider Promptfoo, declarado por separado
como `openai:chat:{{ env.LLM_GRADER_MODEL }}`. Reutiliza `LLM_BASE_URL` y
`LLM_API_KEY`; no cambia `LLM_MODEL` del agente. Para Groq, el ejemplo de
`.env.example` usa `llama-3.1-8b-instant` como grader rápido. Se puede poner
el mismo valor en `LLM_GRADER_MODEL` y `LLM_MODEL`, aunque se recomienda un
modelo rápido para evitar demoras en la calificación. Debe ser compatible con
Chat Completions y responder al prompt de `factuality` de Promptfoo.

Promptfoo 0.123.1 aplica `REQUEST_TIMEOUT_MS: 45000` desde `env` en
`evals/promptfooconfig.yaml` a cada solicitud HTTP del grader (45 segundos).
El grader tiene `maxRetries: 0`, por lo que un timeout se registra como fallo
en lugar de repetir una llamada bloqueada. Este límite no acorta las llamadas
del agente Python: usa su propio cliente del SDK. Las assertions de
`factuality` siguen activas.

### Validación, ejecución y reportes

```powershell
python -m pytest -q -p no:cacheprovider
npm run eval:validate
npm run eval -- --filter-first-n 3 --env-file .env
npm run eval -- --filter-first-n 12 --env-file .env
npm run eval -- --env-file .env
npm run eval:report -- --env-file .env
npm run eval:view
```

Los filtros `--filter-first-n 3` y `12` recorren, respectivamente, los tres
primeros FAQ y los doce FAQ completos, porque ese archivo aparece primero en
`evals/promptfooconfig.yaml`. `eval:report` lanza una **nueva** evaluación
completa y exporta sus resultados; no reutiliza una corrida previa porque el
script tiene `--no-cache`. Inspecciona los fallos antes de versionar el reporte.

`eval:report` exporta `reports/promptfoo-report.html` y
`reports/promptfoo-results.json`. Estos archivos se versionan solo tras una
ejecucion completa real y una revision de datos sensibles y resultados
fallidos. `--no-cache` evita reutilizar respuestas anteriores. El visor lee
las evaluaciones locales de Promptfoo. Sin credenciales, `pytest` y
`eval:validate` siguen disponibles, pero la evaluacion real y su reporte no.

### Casos, datos y metricas

Hay **32 casos**: 12 FAQ (hechos del evento, restricciones, contacto,
informacion ausente, saludo y despedida) y 20 citas (datos incompletos,
fronteras de fecha y clima, confirmacion marginal, errores, cambio de fecha,
intento de omitir clima y orden de herramientas). El reloj se fija por defecto
en `2026-09-17`; la fecha valida de referencia es `2026-09-20`, la ultima
`2026-10-02` y la primera fuera de horizonte `2026-10-03`.

Los perfiles de `evals/fixtures/weather.json` tienen ideal 10/15/0/10/25,
viento marginal 20 y 28 km/h, viento prohibido 28.1, rafagas prohibidas 35.1,
lluvia 0.1, nubes marginales 75, nubes prohibidas 75.1 y un error controlado.
Cada caso crea un cliente falso nuevo. El provider sustituye el servicio
meteorologico antes de procesar mensajes; ninguna prueba deterministica
consulta Open-Meteo real. El calendario tambien es simulado en memoria.

- `contains` y `regex` revisan hechos concretos de la respuesta; la
  assertion `python` comprueba metadatos y falla si faltan. Verifica
  herramientas presentes o ausentes, recuento, orden exacto, fecha,
  `party_size`, estado y resultado. Compara SHA-256 de nombre y contacto
  ficticios para confirmar los argumentos sin exponerlos en la traza.
- `factuality` compara la respuesta con referencias del corpus FAQ o con
  los resultados deterministas de la politica meteorologica. Es una
  calificacion de modelo y puede variar; no sustituye las verificaciones
  deterministas ni garantiza que se haya llamado una herramienta.
- `latency` usa 60 000 ms para FAQ y 180 000 ms para citas. El provider mide
  desde la construccion del supervisor hasta la ultima respuesta, incluidos
  todos los turnos y herramientas; el evaluador de factualidad se ejecuta
  despues y no forma parte de ese tiempo. Estos limites permiten varias
  llamadas del agente y distinguen consultas simples del flujo orquestado.

| Requisito | Archivos |
|-----------|----------|
| Supervisor centralizado y sesiones aisladas | `src/agents/centralized/evaluation.py`, `evals/provider.py` |
| FAQs y contexto recuperado | `evals/faq_scenarios.yaml`, `src/tools/faq_tools.py`, `src/agents/common/context.py` |
| Citas y herramientas | `evals/appointment_scenarios.yaml`, `evals/assertions/tool_trace.py`, `src/tools/calendar_tools.py` |
| Clima y reloj deterministas | `evals/fixtures/weather.py`, `evals/fixtures/weather.json` |
| Factuality y latencia | `evals/promptfooconfig.yaml`, archivos de casos |
| Instalacion y reproduccion | `package.json`, `package-lock.json`, este README |
| Reporte real | `reports/` despues de ejecutar `npm run eval:report` |

Las respuestas del modelo pueden variar entre ejecuciones y algunos casos
pueden fallar si el supervisor omite una herramienta obligatoria. Conservar
esos fallos permite auditar el comportamiento. El corpus FAQ usa busqueda
lexica; una reformulacion puede no recuperar la entrada deseada. Los casos
solo instrumentan herramientas de negocio, no las delegaciones internas del
SDK. No se debe interpretar un `eval:validate` exitoso como aprobacion de
las 32 evaluaciones: requiere las credenciales y una corrida completa.

### Estado de la hoja de evaluaciones

| Componente | Estado |
|---|---|
| Integración Promptfoo | Implementada |
| Provider Python | Implementado; ejecuta el supervisor real |
| Arquitectura centralizada | Conectada con sesiones aisladas y reloj fijo |
| Fixtures meteorológicos | Nueve perfiles simulados; los casos determinísticos no consultan Open-Meteo real |
| 12 casos FAQ | Implementados; ejecución completa pendiente |
| 20 casos de citas | Implementados; ejecución completa pendiente |
| Primeros 3 casos FAQ | **3/3 aprobados en una corrida real parcial anterior** (`faq_place_date`, `faq_weight`, `faq_camera`) |
| Suite Python | **138 aprobadas** en la verificación actual |
| Configuración Promptfoo | Válida en la verificación actual |
| Evaluación completa de 32 casos | Pendiente |
| Reporte HTML/JSON | Pendiente; ninguno de los dos archivos existe aún |

Los 3/3 son un resultado **parcial e histórico**, no el porcentaje final. La
base local de Promptfoo también conserva intentos posteriores incompletos:
uno registra **1 aprobado, 0 fallidos y 4 errores** en cinco casos FAQ. La
evaluación `eval-Mxc-2026-09-30T18:59:19` quedó pausada mientras esperaba un
grader de `factuality`. No se deben sustituir ni ocultar estos intentos con
el resultado anterior. La última corrida completa de los 12 FAQ, de los
20 casos de citas y de los 32 casos combinados sigue pendiente.

Un intento inicial tuvo un problema de selección de Python y no encontró el
módulo `agents`; después de configurar `PROMPTFOO_PYTHON` se obtuvo el 3/3
parcial usando el agente real con Groq. Las advertencias
`OPENAI_API_KEY is not set, skipping trace export` (exportación opcional de
trazas del SDK) y la advertencia experimental de Node no impidieron esa
ejecución. La evaluación usa `LLM_API_KEY`, `LLM_BASE_URL`, `LLM_MODEL` y
`LLM_GRADER_MODEL`; `.env` está ignorado por Git y sus valores no deben
aparecer en documentación ni reportes.

### Trabajo pendiente

1. Ejecutar nuevamente `python -m pytest -q -p no:cacheprovider`.
2. Validar con `npm run eval:validate`.
3. Ejecutar los 12 FAQ con `npm run eval -- --filter-first-n 12 --env-file .env`.
4. Revisar y clasificar cada fallo o error, incluidos los intentos parciales posteriores al 3/3.
5. Corregir solo assertions frágiles cuando la respuesta sea realmente correcta.
6. Mantener las assertions exigentes ante errores reales del agente.
7. Ejecutar los casos de citas en grupos pequeños.
8. Verificar herramientas, argumentos, resultados y orden mediante la metadata.
9. Ejecutar los 32 casos.
10. Generar HTML y JSON mediante `npm run eval:report -- --env-file .env`.
11. Revisar ambos reportes para detectar secretos; conservar los fallos reales.
12. Crear el commit final del reporte tras una corrida real verificada.
13. Confirmar que `git status --short` esté vacío.
14. Hacer push únicamente si el usuario lo solicita.

### Cómo clasificar un fallo

- **Error:** fallo del provider, dependencias, variables de entorno o ejecución; no se cuenta como respuesta incorrecta del agente.
- **Fallo del agente:** respuesta incorrecta, omisión de una herramienta obligatoria, argumento erróneo u orden indebido.
- **Assertion frágil:** respuesta semánticamente correcta que cambia solo en Markdown, espacios Unicode, acentos o redacción equivalente.
- **Factuality:** contrastar la respuesta con el corpus FAQ o la referencia de política/fixture correspondiente; el juicio del evaluador no sustituye la evidencia.
- **Tool execution:** contrastar la traza estructurada en `metadata`, no solo el texto final.

Flexibiliza una assertion únicamente si preserva el requisito semántico que
debía comprobar. No generes ni versiones un reporte hasta ejecutar realmente
la evaluación completa y revisar los resultados.
