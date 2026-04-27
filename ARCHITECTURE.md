# Arquitectura del workshop ia-claude

> Aplica a los 20 katas. Cada notebook implementa este patrón sin excepciones.

## Principio rector

**Cero mocks.** Cada kata se demuestra con llamadas reales a la API de
Anthropic. Los anti-patrones se ejercen con prompts diseñados para producir
de forma reproducible el comportamiento que queremos atacar — no con
respuestas pre-grabadas.

Razón: el examen evalúa si el practicante entendió el sistema real, no si
sabe simular su forma. Un kata que pasa con mocks puede ocultar bugs que
sólo aparecen contra la API real (caché, rate limits, formato exacto del
`tool_use`, etc.).

## Layout del repositorio

```
katas/
  __init__.py
  _shared/                       # utilidades comunes a los 20 katas
    __init__.py
    bootstrap.py                 # prompt de API key + cliente + settings
    eventlog.py                  # log estructurado por iteración
  kata_NNN_<slug>/
    notebook.ipynb               # único entregable del kata
    [helpers.py]                 # opcional: código reutilizado entre celdas
```

`katas/_shared/` se importa desde cualquier notebook con
`from katas._shared.bootstrap import bootstrap`. Para que el import
funcione, el notebook se abre con `jupyter` desde la raíz del repo, o
está instalado el paquete con `pip install -e .`.

## Bootstrap obligatorio

La primera celda de código de cada notebook es exactamente esta:

```python
from katas._shared.bootstrap import bootstrap

client, settings = bootstrap()
print("modelo:", settings.model, "| presupuesto:", settings.budget_calls, "llamadas")
```

`bootstrap()` hace tres cosas:

1. Si la variable de entorno `ANTHROPIC_API_KEY` no está, la pide con
   `getpass.getpass(...)` (no echo en pantalla) y la fija en el entorno
   del kernel.
2. Construye un `Anthropic()` envuelto con un guardia de presupuesto que
   cuenta llamadas y aborta con `BudgetExceeded` si excede `budget_calls`.
3. Devuelve `(client, settings)` donde `settings` expone `model`,
   `max_tokens`, `budget_calls`. Cada kata puede reasignar estos valores
   antes de empezar a llamar.

## Modelo por defecto

- Default: `claude-haiku-4-5-20251001`.
  Razón: cada notebook hace 3-10 llamadas; con Haiku el costo por kata
  está en centavos.
- Sobre-escribir cuando el kata lo justifique:
  ```python
  settings.model = "claude-sonnet-4-6"
  ```
  Casos típicos: extracción defensiva (Kata 5), code review (Kata 13),
  juicios subjetivos (Kata 14).
- `claude-opus-4-7` sólo si el kata realmente lo demanda; documentarlo en
  la celda de setup del notebook.

## Guardia de presupuesto

`bootstrap()` envuelve `client.messages.create` con un contador.
`settings.budget_calls` por defecto es 20. Si el notebook entra en un
bucle defectuoso, aborta con `BudgetExceeded` antes de quemar la cuenta.
Cada kata puede subir o bajar el límite explícitamente:

```python
settings.budget_calls = 5   # demo cortita
```

## Log estructurado

Para katas que demuestran control de flujo (1, 2, 4, 6, 12, 16, 19, 20),
se usa `katas._shared.eventlog.Logger`:

```python
from katas._shared.eventlog import Logger

log = Logger()
log.add(iter=1, stop_reason="tool_use", branch="dispatch", tool="get_weather")
log.show()                # tabla legible
```

El `Logger` es un wrapper trivial sobre una lista de dicts; existe para
que los 20 notebooks usen exactamente el mismo formato de evento, lo que
hace que la comparación visual entre katas sea inmediata.

## Estructura del notebook (Constitution Principio VIII)

Toda celda obedece este orden:

1. **Setup** — celda de código con `bootstrap()`. Imprime modelo y
   presupuesto.
2. **§1 Concepto** — markdown, 2-4 líneas.
3. **§2 Por qué importa** — markdown, 1-2 párrafos con la falla concreta.
4. **§3 Ejemplo correcto** — markdown intro + celdas de código con
   llamadas reales a la API. Cada celda imprime resultados visibles
   (texto del modelo, log estructurado, tokens).
5. **§4 Anti-patrón** — markdown intro + celdas de código que reproducen
   el error con la **misma** API real. Imprime el síntoma del fallo
   lado a lado con el caso correcto.
6. **§5 Argumento de certificación** — markdown, 4-6 bullets defendibles
   en voz alta.
7. **§6 Auto-evaluación** — markdown con las preguntas del `spec.md`
   respondidas en mis palabras.
8. **Apéndice (opcional)** — variantes, costo, links a la documentación
   oficial relevante.

## Estrategia de anti-patrón con API real

El reto: la API es no determinista, pero el anti-patrón requiere
condiciones específicas para fallar. Soluciones aceptadas en este
workshop:

- **Prompt dirigido**: el system prompt instruye al modelo a producir el
  texto/comportamiento exacto que dispara el anti-patrón (p. ej. "incluye
  la frase 'task complete' al inicio de tu turno"). Honesto: el kata
  prueba el bucle, no la creatividad del modelo.
- **Fixture de input controlado**: el input del usuario contiene el
  patrón trampa (p. ej. data sucia con códigos legacy en Kata 3). El
  modelo opera sobre ese input real.
- **Comparación lado a lado**: misma llamada, dos lectores distintos. El
  caso correcto consume `stop_reason`; el anti-patrón consume el texto.
  Cualquier respuesta del modelo expone la diferencia.

Lo que **no** se hace: parchar la respuesta del modelo, hardcodear texto
en el flujo, o falsear `stop_reason`. Si el modelo no coopera con el
prompt dirigido, el practicante itera el prompt hasta que sí — eso
también enseña.

## Dependencias

`pyproject.toml` ya las declara:

- `anthropic>=0.40` — cliente oficial.
- `pydantic>=2.7` — schemas tipados (Katas 5, 6, 13, 15, 16, 20).
- `jupyter>=1.0` — kernel para ejecutar los notebooks.
- `ruff>=0.5` — lint del código en `_shared/` y `helpers.py` por kata.

`pytest` queda como dependencia opcional para quien quiera correr asserts
inline de comprobación; no es un requisito de cierre de kata.

## Costo y reproducibilidad

- Cada notebook imprime `usage` (input/output/cache tokens) tras la
  primera llamada para que el practicante vea el costo real.
- Los outputs quedan grabados en el `.ipynb` tras la primera ejecución;
  un revisor puede inspeccionarlos sin re-correr la API.
- Para auditoría, las llamadas relevantes pueden serializarse a
  `katas/kata_NNN_<slug>/runs/<timestamp>.json` — no obligatorio, pero
  recomendado en katas con anti-patrón sutil (1, 11, 14, 15).

## Mapa modelo → kata

| Modelo recomendado por kata | Katas |
|---|---|
| `claude-haiku-4-5-20251001` (default) | 1, 2, 3, 4, 6, 7, 8, 9, 10, 11, 12, 17, 18, 19 |
| `claude-sonnet-4-6` | 5, 13, 14, 15, 16, 20 |
| `claude-opus-4-7` | sólo si el practicante decide subir el listón |

Los katas Sonnet son los que requieren juicio matizado o extracción
estructurada con bajos índices de fabricación.

## Flujo de trabajo por kata (5 pasos)

1. `cp specs/_templates/notebook-template.ipynb katas/kata_NNN_<slug>/notebook.ipynb`.
2. Abrir el notebook desde la raíz del repo: `jupyter notebook katas/kata_NNN_<slug>/notebook.ipynb`.
3. Ejecutar la celda de bootstrap; introducir API key si la pide.
4. Llenar las 6 secciones; cada celda de código corre llamadas reales.
5. "Restart & Run All" antes de hacer commit; un notebook que no corre
   no cuenta como entregado.

## Lo que esta arquitectura no hace

- No declara test suites, no impone coverage, no genera dashboards.
- No automatiza CI; el revisor humano evalúa los 6 bloques visualmente.
- No persiste API keys en disco (sólo en el entorno del kernel actual).
- No abstrae el SDK detrás de una capa propia: el practicante debe ver y
  escribir las llamadas reales.

## Versionado de la arquitectura

Cualquier cambio a este documento incrementa la versión y se anota
abajo. Las modificaciones a `_shared/` que rompan la API consumida por
notebooks existentes son MAJOR.

**Versión**: 1.0.0 | **Fecha**: 2026-04-27
