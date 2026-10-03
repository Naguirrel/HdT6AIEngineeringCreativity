# Guía operativa para agentes: Parachute S.A.

## Contexto y estado

Este proyecto académico conserva tres arquitecturas de agentes de la hoja
anterior: centralizada, jerárquica y descentralizada. La nueva hoja evalúa
**solo la arquitectura centralizada** con Promptfoo. Sus dos funciones son
responder FAQs usando el corpus oficial y calendarizar citas después de
validar fecha y clima.

La integración, el provider Python, el runner programático y los nueve perfiles
meteorológicos simulados están implementados. Hay **32 casos definidos**:
12 FAQ y 20 de citas. Una corrida real parcial anterior aprobó los primeros
tres FAQ (`faq_place_date`, `faq_weight`, `faq_camera`), **3/3**. La base local
también conserva intentos posteriores incompletos; uno registra 1 aprobado y
4 errores de ejecución en cinco FAQ. La evaluación
`eval-Mxc-2026-09-30T18:59:19` quedó pausada durante la calificación de
`factuality`. **No** se ha completado la corrida de 12 FAQ, la de 20 citas ni
la de 32 casos. Los reportes HTML/JSON aún no existen.

La verificación Python actual aprobó **138 pruebas** y `npm run eval:validate`
confirmó que la configuración de Promptfoo es válida. El resultado 3/3 es
parcial e histórico; no representa el porcentaje final de la hoja.

## Reglas obligatorias

1. Leer `README.md`, este archivo, `package.json`,
   `evals/promptfooconfig.yaml` y los casos relevantes antes de modificar.
2. Ejecutar `git status --short` antes y después. Trabajar en
   `promptfoo-evals`, salvo instrucción explícita contraria. No modificar
   `main` ni `fix-pre-errors`.
3. No modificar `.env`, leer o mostrar el valor de `LLM_API_KEY`, ni incluir
   secretos en archivos, logs, documentación o reportes. `.env` está ignorado
   por Git.
4. No llamar Open-Meteo real en evaluaciones determinísticas. Mantener el
   cliente falso y el reloj fijo por caso; no agregar persistencia ni
   servicios externos. El calendario debe seguir simulado en memoria.
5. No inventar resultados, generar reportes ficticios ni editar reportes a
   mano. Conservar los fallos reales y no debilitar assertions para elevar
   artificialmente el porcentaje.
6. No hacer push ni merge sin solicitud explícita. Mantener un commit por
   problema o etapa, separado y descriptivo.
7. Ejecutar pytest después de cambios Python y validar Promptfoo después de
   cambios YAML. Ejecutar subconjuntos antes de la suite completa.
8. Tratar variaciones de Markdown, espacios Unicode, acentos o redacción
   equivalente como posibles assertions frágiles, no automáticamente como
   errores factuales. Comprobar siempre el requisito semántico.
9. No modificar el corpus FAQ, los umbrales meteorológicos ni el calendario
   en memoria sin autorización. Al cambiar código compartido, conservar la
   compatibilidad con las tres arquitecturas.

## Preparación obligatoria en PowerShell

Desde la raíz del repositorio, con `.venv` y dependencias instaladas:

```powershell
.\.venv\Scripts\Activate.ps1
$env:PROMPTFOO_PYTHON = (Resolve-Path ".\.venv\Scripts\python.exe").Path
$env:PROMPTFOO_CONFIG_DIR = Join-Path (Resolve-Path .venv).Path "promptfoo-state"
$env:TEMP = Join-Path (Resolve-Path .venv).Path "tmp"
$env:TMP = $env:TEMP
New-Item -ItemType Directory -Force $env:TEMP | Out-Null
& "$env:PROMPTFOO_PYTHON" -c "import sys, agents; print(sys.executable); print(agents.__file__)"
```

Estas variables solo duran la sesión actual; configurarlas de nuevo en cada
terminal. `PROMPTFOO_PYTHON` debe apuntar a `.venv\Scripts\python.exe`.
Si apunta a otro intérprete, Promptfoo puede fallar con
`ModuleNotFoundError: No module named 'agents'`. El agente y el evaluador
usan `LLM_API_KEY` y `LLM_BASE_URL`. El agente usa `LLM_MODEL`; el grader de
`factuality` usa `LLM_GRADER_MODEL`. Para Groq, configurar en `.env` local
`LLM_GRADER_MODEL=qwen/qwen3.8-27b` es un ejemplo verificado en Groq. Puede igualar
`LLM_MODEL` si se desea, pero se recomienda un grader rápido. El YAML fija
`REQUEST_TIMEOUT_MS: 45000` para las solicitudes HTTP de Promptfoo y
`maxRetries: 0` para el grader. El provider Python fija
`config.timeout: 180000` para su worker y no hereda los 45 segundos. Mantener
`--max-concurrency 1` al ejecutar las evaluaciones. No quitar la assertion
`factuality`.
No imprimir sus valores.

## Procedimiento para continuar

Primero repetir pytest y la validación como indica el README. El **primer eval
pendiente** es:

```powershell
npm run eval:faq -- --env-file .env
```

Clasificar cada error y fallo sin confundir problemas del provider con fallos
del agente. Corregirlos uno por uno, manteniendo las assertions semánticas.
Después ejecutar citas en grupos pequeños y verificar las llamadas de
herramientas, argumentos, resultados, errores, recuento y orden desde
`metadata`; el texto final por sí solo no demuestra ejecución. Las
delegaciones internas `as_tool()` no forman parte de esa traza de negocio.

Luego ejecutar los 32 casos y generar el reporte **real** con el script
`eval:report` de `package.json`. Inspeccionar HTML y JSON en busca de secretos,
conservar los fallos y crear el commit final del reporte. No hacer push salvo
solicitud explícita. La advertencia de exportación opcional de trazas
`OPENAI_API_KEY is not set, skipping trace export` y la advertencia
experimental de Node no bloquearon la corrida parcial anterior.

## Criterios de finalización

Solo declarar terminada la hoja cuando pytest pase, la configuración sea
válida, los **32 casos se hayan ejecutado**, cada fallo se haya revisado,
existan reportes HTML y JSON procedentes de una corrida real, ambos estén
libres de secretos, el README refleje los resultados finales reales, el árbol
de Git esté limpio y los commits estén separados y descritos. El calendario
seguirá siendo simulado en memoria.

## Archivos importantes

| Función | Ruta verificada |
|---|---|
| Configuración Promptfoo | `evals/promptfooconfig.yaml` |
| Provider Python | `evals/provider.py` |
| Runner del supervisor centralizado | `src/agents/centralized/evaluation.py` |
| Casos FAQ | `evals/faq_scenarios.yaml` |
| Casos de citas | `evals/appointment_scenarios.yaml` |
| Fixtures meteorológicos | `evals/fixtures/weather.py`, `evals/fixtures/weather.json` |
| Assertion de herramientas | `evals/assertions/tool_trace.py` |
| Instrucciones y comandos | `README.md`, `package.json` |
| Directorio de reportes | `reports/` (solo contiene `.gitkeep` por ahora) |
