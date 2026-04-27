"""Build STUDY_GUIDE.md from the 20 specs + the §6 answers in each notebook.

Output: STUDY_GUIDE.md at repo root. Render to PDF with:
    pandoc STUDY_GUIDE.md -o STUDY_GUIDE.pdf \
        --pdf-engine=wkhtmltopdf --toc --toc-depth=2 \
        -c scripts/study_guide.css
"""

from __future__ import annotations

import json
import pathlib
import re
import sys


REPO = pathlib.Path(__file__).resolve().parent.parent
SPECS = REPO / "specs"
KATAS = REPO / "katas"


COVER = """---
title: "Guía Maestra de Estudio — 20 katas para Claude Certified Architect"
subtitle: "Workshop ia-claude · concept-first cert prep"
author: "raul.alzate@sofka.com.co"
lang: es
toc-title: "Índice"
---

# Cómo usar esta guía

Este documento condensa los 20 katas del workshop `ia-claude` en una sola
guía imprimible para preparar el examen oral del **Claude Certified
Architect**. Cada kata aparece con la misma estructura:

1. **Concepto** — la idea en una página.
2. **Por qué importa** — la falla que evita.
3. **Modelo mental** — cómo pensar el patrón.
4. **Ejemplo mínimo** — pseudocódigo o snippet conceptual.
5. **Anti-patrón** — el error común y por qué falla.
6. **Argumento de certificación** — los puntos a defender en voz alta.
7. **Auto-evaluación** — preguntas con respuestas propuestas.

El **entregable real** de cada kata vive en
`katas/kata_NNN_<slug>/notebook.ipynb` y demuestra el patrón contra la
API de Anthropic. Esta guía es el complemento conceptual que se lee
imprimido, sin pantallas.

# Mapa temático

Los 20 katas se organizan en hilos:

| Hilo                       | Katas                              |
|----------------------------|------------------------------------|
| Determinismo               | 01, 02, 06, 13                     |
| Schemas y contratos        | 05, 13, 15, 16, 20                 |
| Economía de contexto       | 03, 08, 09, 10, 11, 12             |
| Memoria                    | 08, 11, 18, 19                     |
| Aislamiento                | 04, 12, 19                         |
| Human-in-the-loop          | 07, 15, 16                         |

Una decisión técnica suele tocar varios hilos a la vez. Las conexiones
inter-katas se enuncian al final de cada sección "Argumento de
certificación".

# Cómo leer un kata en 10 minutos

1. Lee la sección **Concepto** y formula con tus palabras la regla en una
   sola frase.
2. Cubre la sección **Anti-patrón** con la mano y trata de anticiparla.
3. Lee la **Auto-evaluación** sin mirar la respuesta. Compara después.
4. Si las respuestas no encajan, vuelve al **Modelo mental** — ahí está
   la falla de comprensión.
5. Salta al notebook si quieres ver el código corriendo.

"""


def parse_spec(text: str) -> dict[str, str]:
    """Extract sections from a spec.md keyed by H2 headings.

    Tracks fenced code-block state so that `## ...` inside ```` ``` ```` blocks
    is treated as content, not as a section break.
    """
    sections: dict[str, str] = {}
    current = None
    buf: list[str] = []
    title = ""
    in_fence = False
    for line in text.splitlines():
        if line.startswith("```"):
            in_fence = not in_fence
            if current is not None:
                buf.append(line)
            continue
        if not in_fence and line.startswith("# Kata "):
            title = line[2:].strip()
            continue
        m = re.match(r"^## (.+)$", line) if not in_fence else None
        if m:
            if current is not None:
                sections[current] = "\n".join(buf).strip()
            current = m.group(1).strip()
            buf = []
        else:
            if current is not None:
                buf.append(line)
    if current is not None:
        sections[current] = "\n".join(buf).strip()
    return {"_title": title, **sections}


def extract_self_check_md(nb_path: pathlib.Path) -> str:
    """Find the §6 markdown cell in a notebook and return its source."""
    nb = json.loads(nb_path.read_text())
    for cell in nb["cells"]:
        if cell["cell_type"] != "markdown":
            continue
        src = "".join(cell["source"]) if isinstance(cell["source"], list) else cell["source"]
        if "## 6. Auto-evaluación" in src:
            # Strip the heading itself; we add our own
            return src.split("## 6. Auto-evaluación", 1)[1].strip()
    return ""


def kata_section(spec_dir: pathlib.Path, nb_path: pathlib.Path) -> str:
    spec = parse_spec((spec_dir / "spec.md").read_text())
    answers = extract_self_check_md(nb_path)

    # Pull questions from the spec self-eval section so we present Q + A together
    spec_qs = spec.get("Auto-evaluación", "")

    title = spec.get("_title", spec_dir.name)
    body = []
    body.append(f"# {title}")
    body.append("")
    if "Concepto" in spec:
        body.append("## Concepto"); body.append(""); body.append(spec["Concepto"]); body.append("")
    if "Por qué importa" in spec:
        body.append("## Por qué importa"); body.append(""); body.append(spec["Por qué importa"]); body.append("")
    if "Modelo mental" in spec:
        body.append("## Modelo mental"); body.append(""); body.append(spec["Modelo mental"]); body.append("")
    if "Ejemplo mínimo" in spec:
        body.append("## Ejemplo mínimo"); body.append(""); body.append(spec["Ejemplo mínimo"]); body.append("")
    if "Anti-patrón" in spec:
        body.append("## Anti-patrón"); body.append(""); body.append(spec["Anti-patrón"]); body.append("")
    if "Argumento de certificación" in spec:
        body.append("## Argumento de certificación"); body.append("")
        body.append(spec["Argumento de certificación"]); body.append("")

    body.append("## Auto-evaluación")
    body.append("")
    if answers:
        body.append(answers)
    elif spec_qs:
        body.append(spec_qs)
    body.append("")
    return "\n".join(body)


GLOSSARY = """# Glosario

**Agentic Loop.** `while` controlado por `stop_reason`; `tool_use` ejecuta y
continúa, `end_turn` corta, otros valores cortan con motivo explícito. Núcleo
del Kata 01.

**Anti-patrón.** Implementación común que parece funcionar y falla en cuanto
cambia el input. Cada kata tiene uno; documentarlo es parte del entregable.

**Bootstrap (`katas._shared.bootstrap`).** Función que pide la API key con
`getpass`, devuelve cliente envuelto con guardia de presupuesto. Primera celda
de todo notebook del workshop.

**Budget guard.** Contador que envuelve `client.messages.create` y aborta con
`BudgetExceeded` antes de quemar la cuenta.

**Cache control (`cache_control: ephemeral`).** Marcador en bloques de
contenido que indica al SDK marcar el segmento como cacheable. Se usa para
implementar prefix caching (Kata 10).

**Cascada de `CLAUDE.md`.** Orden de precedencia: usuario → proyecto → módulo.
Más específico gana. Composable con `@imports` (Kata 08).

**Custom ID (Batch API).** Identificador único por request en un batch que
permite correlación 1:1 entre input y output (Kata 17).

**Determinismo.** Misma entrada → misma transición. Sólo señales estructuradas
(`stop_reason`, hook verdict) lo garantizan; texto generado no (Principio I).

**Edge placement.** Estrategia de ubicar reglas críticas al inicio Y al final
del contexto para sobrevivir la curva U de atención (Kata 11).

**Escape enum.** Valor del enum (`other`, `unclear`) acompañado de un campo
`_details` que permite al modelo admitir ambigüedad sin romper el contrato
(Kata 05).

**Evento estructurado.** Diccionario tipado `(iter, stop_reason, branch, …)`
emitido por iteración. Permite reconstruir la traza sin re-llamar al modelo.

**Few-shot.** 2-4 ejemplos input/output en el prompt para calibrar la
distribución del modelo en tareas subjetivas (Kata 14).

**Forced `tool_choice`.** Parámetro `tool_choice={"type":"tool","name":"X"}`
que obliga al modelo a invocar el tool X. Garantiza salida tipada por schema
(Kata 05, 13).

**Hub-and-spoke.** Topología de subagentes: un coordinador central, N
subagentes aislados, cero aristas laterales. Cero historial compartido
(Kata 04).

**Lost in the middle.** Efecto medible donde la atención del transformer
decae en el centro del contexto. Mitigación: edge placement (Kata 11).

**Mismatch flag.** Campo booleano que el extractor pone en `true` cuando
valores declarado y computado difieren más de un epsilon. Dispara revisión
humana (Kata 15).

**MCP (Model Context Protocol).** Estándar para herramientas/servidores que
expone errores tipados (`isError`, `errorCategory`, `isRetryable`). El cliente
decide retry o escalada desde flags, no desde prosa (Kata 06).

**Plan Mode.** Modo read-only previo a ejecución directa. El cliente entrega
distinto set de tools en cada fase (Kata 07).

**Prefix caching.** Reutilización del KV cache cuando el prefijo del prompt
es idéntico turno a turno. Regla práctica: estático arriba, dinámico abajo
(Kata 10).

**PreToolUse / PostToolUse hook.** Función que corre antes (gate) o después
(normalización) de la ejecución de la herramienta. Aplica políticas en código,
no en prompt (Katas 02, 03).

**Provenance.** Mapeo `claim → source` preservado tras agregación. Conflictos
no se resuelven en silencio (Kata 20).

**Scratchpad.** Archivo markdown estructurado donde el agente vuelca
descubrimientos durables. Sobrevive a `/compact` (Kata 18).

**`stop_reason`.** Metadato estructurado del Message que indica por qué
terminó el turno. Único árbitro legítimo del control de flujo (Kata 01).

**Subagente.** Llamada nueva e independiente al SDK con prompt mínimo y
salida tipada. Cero memoria heredada del coordinador (Kata 04).
"""

CHEAT_SHEET = """# Cheat sheet (una página)

| #  | Kata                                | Regla central                                                           |
|----|-------------------------------------|-------------------------------------------------------------------------|
| 01 | Bucle agéntico                      | Control por `stop_reason`, jamás por texto del modelo                   |
| 02 | PreToolUse                          | Política en código, prompt sólo sugiere                                 |
| 03 | PostToolUse                         | El modelo nunca ve datos crudos heterogéneos                            |
| 04 | Subagent isolation                  | Hub-and-spoke; subagente recibe prompt mínimo, devuelve JSON tipado     |
| 05 | Defensive extraction                | Schema con `tool_choice` forzado, enum con escape, nullable union       |
| 06 | MCP errors                          | `isError`+`errorCategory`+`isRetryable` tipados, retry en cliente       |
| 07 | Plan Mode                           | Tools de lectura → plan firmado → tools de escritura                    |
| 08 | CLAUDE.md memory                    | Cascada user → project → module; `@imports` para modularidad            |
| 09 | Path rules                          | Reglas heurísticas se cargan sólo cuando el target hace match           |
| 10 | Prefix caching                      | Estático arriba (cacheable), dinámico abajo                             |
| 11 | Softmax mitigation                  | Reglas duras en bordes; compactar al 50–60 % de capacidad               |
| 12 | Prompt chaining                     | Pase 1 tipado por unidad → pase 2 integra sin ver crudos                |
| 13 | Headless CI review                  | `claude -p` con schema; `jsonschema.validate` antes de publicar          |
| 14 | Few-shot                            | 2-4 ejemplos de bordes, no del centro fácil                             |
| 15 | Self-correction                     | `mismatch` y `needs_human_review` son required, no se autocorrige       |
| 16 | Human handoff                       | Tool con schema estricto y enum de motivo; suspende generación de prosa |
| 17 | Batch processing                    | `custom_id` único, polling/webhook, recuperación selectiva              |
| 18 | Scratchpad                          | Memoria persistente fuera de la conversación; sobrevive a `/compact`    |
| 19 | Adaptive investigation              | Topology → prioritize → deep-dive con presupuesto y re-plan             |
| 20 | Data provenance                     | Cada claim con `source_id`; conflictos preservados, no resueltos        |

## Antes del examen, repite

1. *El control de flujo es por señal estructurada, nunca por prosa.*
2. *Los schemas fallan cerrados; los prompts son sugerencias.*
3. *Estático arriba, dinámico abajo; bordes para reglas, centro para datos.*
4. *Subagentes con prompt mínimo y salida tipada; cero historial heredado.*
5. *Cuando dudes, escala al humano con payload tipado.*
"""


def main() -> int:
    parts = [COVER]

    spec_dirs = sorted([d for d in SPECS.iterdir() if d.is_dir() and d.name[:3].isdigit()])
    nb_paths = {d.name.split("_")[1]: d / "notebook.ipynb" for d in KATAS.iterdir() if d.name.startswith("kata_")}

    for spec_dir in spec_dirs:
        kata_id = spec_dir.name.split("-")[0]  # e.g. "001"
        nb = nb_paths.get(kata_id)
        if nb is None or not nb.exists():
            print(f"WARN: notebook missing for {spec_dir.name}", file=sys.stderr)
            continue
        parts.append(kata_section(spec_dir, nb))

    parts.append(GLOSSARY)
    parts.append(CHEAT_SHEET)

    out = REPO / "STUDY_GUIDE.md"
    out.write_text("\n\n".join(parts))
    print(f"wrote {out} ({out.stat().st_size:,} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
