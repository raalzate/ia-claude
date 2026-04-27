"""Build STUDY_GUIDE.md — guía práctica alineada al examen oficial.

Estructura:
    1. Cover
    2. Examen de un vistazo (5 dominios + scoring + formato)
    3. Mapa escenario→kata
    4. Cómo usar la guía
    5. Mapa temático
    6. Domain Deep Dives (uno por dominio, con task statements y código)
    7. Cards conceptuales por kata (los 30)
    8. Banco de preguntas de práctica (multiple-choice estilo oficial)
    9. Topics bonus no cubiertos a profundidad por los katas
   10. Glosario
   11. Cheat sheet
   12. Out-of-scope (lo que NO entra en el examen)

Render:
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
title: "Guía de Estudio Práctica — Claude Certified Architect (Foundations)"
subtitle: "Workshop ia-claude · alineada a los 5 dominios oficiales"
author: "raul.alzate@sofka.com.co"
lang: es
toc-title: "Índice"
---

# Cómo usar esta guía (TL;DR)

Esta guía está organizada para **prepararte directamente al examen
oficial**. Tiene tres usos:

1. **Estudio dirigido por dominio.** Las páginas siguientes recorren los 5
   dominios oficiales con sus *task statements* y los katas/notebooks que
   los cubren. Lee primero esto y identifica qué dominio te cuesta más.
2. **Práctica con preguntas.** El **Banco de preguntas** al final tiene
   ~20 preguntas multiple-choice en el formato exacto del examen
   (escenario + 4 opciones + explicación de por qué cada distractor
   falla).
3. **Repaso visual.** Las **cards conceptuales** (una por kata) son
   resúmenes de una página para hojear el día anterior.

> **Cero mocks.** Cada concepto está respaldado por un notebook ejecutable
> en `katas/kata_NNN_<slug>/notebook.ipynb`. La guía es la teoría; el
> notebook es la práctica.

"""


EXAM_AT_A_GLANCE = """# Examen de un vistazo

## Formato

| Atributo            | Valor                                                  |
|---------------------|--------------------------------------------------------|
| Tipo                | Multiple-choice (1 correcta, 3 distractores)           |
| Escenarios          | 4 de 6 escenarios fijos, escogidos al azar             |
| Score scale         | 100–1000 (mínimo aprobación: **720**)                  |
| Penalización        | No hay; preguntas en blanco cuentan como incorrectas   |

## Dominios y peso

| Dominio                                            | Peso  | Hilo principal               |
|----------------------------------------------------|-------|------------------------------|
| 1. Agentic Architecture & Orchestration            | 27%   | Bucles, hooks, subagentes    |
| 2. Tool Design & MCP Integration                   | 18%   | Tools, errores tipados, MCP  |
| 3. Claude Code Configuration & Workflows           | 20%   | CLAUDE.md, skills, plan mode |
| 4. Prompt Engineering & Structured Output          | 20%   | Schemas, few-shot, batch     |
| 5. Context Management & Reliability                | 15%   | Contexto, escalación, prov.  |

> **Lectura estratégica**: Dominios 1+3+4 = **67 % del examen**. Si tu
> tiempo es limitado, gasta el grueso ahí.

## Los 6 escenarios

El examen presenta 4 de estos 6 al azar. **Conoce los 6** porque las
preguntas son escenario-aware: una mala lectura del contexto cambia la
respuesta correcta.

1. **Customer Support Resolution Agent** — Agent SDK; tools `get_customer`,
   `lookup_order`, `process_refund`, `escalate_to_human`; meta 80%+ de
   first-contact resolution.
2. **Code Generation with Claude Code** — Claude Code; CLAUDE.md, slash
   commands, plan mode vs direct execution.
3. **Multi-Agent Research System** — coordinador + subagentes (web search,
   document analysis, synthesis, report).
4. **Developer Productivity with Claude** — built-in tools (Read, Write,
   Bash, Grep, Glob), exploración de codebases, MCP servers.
5. **Claude Code for Continuous Integration** — `claude -p`,
   `--output-format json`, anotaciones inline en PRs.
6. **Structured Data Extraction** — `tool_use` con JSON Schema, validación,
   manejo de edge cases, downstream integration.

"""


SCENARIO_TO_KATA_MAP = """# Mapa escenario → kata

Para cada escenario oficial, los katas (de los 30) que lo cubren
directamente:

| Escenario                          | Katas relevantes                                       |
|------------------------------------|--------------------------------------------------------|
| Customer Support Agent             | 01, 02, 06, 15, 16, 21, 22, 25, 28, 30                 |
| Code Generation con Claude Code    | 07, 08, 09, 19, 23, 24, 25, 27                         |
| Multi-Agent Research               | 04, 12, 19, 20, 21, 28, 29                             |
| Developer Productivity             | 07, 18, 19, 22, 23, 24, 25                             |
| CI/CD Headless                     | 13, 17, 26, 27, 30                                     |
| Structured Data Extraction         | 05, 14, 15, 17, 26, 29, 30                             |

> **Tip de examen**: cuando te toque un escenario, recorre primero los
> tres katas más asociados antes de mirar las opciones. Los distractores
> a menudo "huelen bien" si los lees en abstracto.

## Mapa temático — los 30 katas por hilo

Una decisión técnica suele tocar varios hilos a la vez. Las conexiones
inter-katas aparecen también al final de cada sección "Argumento de
certificación" del kata.

| Hilo                            | Katas                                       |
|---------------------------------|---------------------------------------------|
| Determinismo                    | 01, 02, 06, 13                              |
| Tools & MCP                     | 02, 03, 06, 21, 22, 23, 24                  |
| Schemas y contratos             | 05, 13, 15, 16, 20, 26, 29                  |
| Economía de contexto            | 03, 08, 09, 10, 11, 12                      |
| Memoria y sesión                | 08, 11, 18, 19, 25                          |
| Aislamiento y subagentes        | 04, 12, 19, 28                              |
| Human-in-the-loop               | 07, 15, 16, 30                              |
| Calidad pragmática (false pos.) | 13, 14, 27, 30                              |
| Provenance y confianza          | 15, 20, 29                                  |

"""


DOMAIN_DEEP_DIVES = """# Domain 1 — Agentic Architecture & Orchestration (27 %)

## Task Statement 1.1: Agentic loops

**Lo que tienes que saber con tus dedos:**

```python
# Patrón canónico (cero mocks; ver Kata 01)
while True:
    resp = client.messages.create(messages=history, tools=tools, ...)
    if resp.stop_reason == "tool_use":
        result = run_tool(resp.content)            # ejecutar
        history.append({"role": "assistant", "content": resp.content})
        history.append({"role": "user", "content": [
            {"type": "tool_result", "tool_use_id": tu.id, "content": str(result)}
        ]})
        continue
    if resp.stop_reason == "end_turn":
        return resp                                # éxito
    raise UnhandledStop(resp.stop_reason)          # nunca silencioso
```

**Anti-patrones que el examen ataca:**

- Parsear texto del modelo para decidir terminación (`if "done" in text`).
- Usar `max_iterations` como mecanismo primario de corte.
- Inferir éxito de la ausencia de errores.

> Notebook de referencia: `kata_001_agentic_loop`.

## Task Statement 1.2: Coordinador-subagente (hub-and-spoke)

**Reglas duras:**

- El coordinador es el **único** que recibe la query final del usuario.
- Cada subagente es una **sesión nueva** con prompt mínimo y tools recortadas.
- Subagentes devuelven **JSON tipado**, jamás prosa libre.
- La memoria conversacional **NO se hereda automáticamente**.

```python
def coordinator(user_query):
    plan = decompose(user_query)                   # subtareas tipadas
    results = [run_subagent(t) for t in plan]      # cada uno: sesión nueva
    return synthesize(results)                     # agrega claims tipados

def run_subagent(subtask):
    return client.messages.create(
        system=focused_system_for(subtask),        # prompt MÍNIMO
        messages=[{"role":"user","content": subtask.prompt}],
        tools=subtask.scoped_tools,                # subset acotado
        tool_choice={"type":"any"},                # fuerza salida tipada
    )
```

> Notebooks: `kata_004_subagent_isolation`, `kata_019_adaptive_investigation`.

## Task Statement 1.3: Spawning de subagentes (Agent SDK)

Términos del SDK que aparecen en el examen:

- **`Task` tool**: el mecanismo del Agent SDK para que el coordinador
  invoque subagentes. Para que esto funcione, `allowedTools` del
  coordinador **debe** incluir `"Task"`.
- **`AgentDefinition`**: configuración por subagente — descripción, system
  prompt y tool restrictions. Cada tipo de subagente puede tener su propio
  `AgentDefinition`.
- **Paralelismo**: el coordinador emite **múltiples `Task` calls en una
  sola respuesta** para que corran en paralelo. Calls en turnos separados
  son secuenciales.

> Punto de examen: si un subagente "olvida" el contexto del coordinador,
> es porque NO lo hereda automáticamente — hay que pasarlo explícito en
> su prompt.

## Task Statement 1.4: Workflows multi-paso con enforcement

**Programmatic enforcement vs prompt-based**:

| Necesidad                       | Mecanismo                                  |
|---------------------------------|--------------------------------------------|
| Compliance crítico (financiero) | Hook que bloquea hasta cumplir prereq.     |
| Workflow ordering "preferido"   | System prompt o few-shot                   |

**Patrón "prerequisite gate":**

```python
def pretool_gate(tool_name, tool_input, session_state):
    if tool_name == "process_refund" and not session_state.customer_verified:
        return {"action":"deny","reason":"prereq:get_customer required"}
    return {"action":"allow"}
```

> El examen mete preguntas con frase "production data shows that in 12 %
> of cases…" para forzarte a elegir hooks (deterministic) sobre prompt.

## Task Statement 1.5: Hooks de Agent SDK

- **`PostToolUse`**: normaliza el resultado **antes** de que el modelo lo
  vea (Kata 03). Caso típico: timestamps Unix → ISO 8601, status codes
  → strings legibles.
- **Tool call interception**: equivalente del `PreToolUse` (Kata 02).
  Bloquea por política, redirige a escalación.

## Task Statement 1.6: Task decomposition

- **Prompt chaining** (Kata 12): pasos *fijos* y *secuenciales*. Apto
  cuando el flujo es predecible (analizar 50 archivos, luego integrar).
- **Adaptive decomposition** (Kata 19): generar el plan al vuelo cuando
  el problema es exploratorio (codebase desconocido).

## Task Statement 1.7: Session management

| Comando / función     | Cuándo usar                                   |
|-----------------------|-----------------------------------------------|
| `--resume <name>`     | Continuar sesión nombrada (contexto válido)   |
| `fork_session`        | Explorar dos enfoques desde una baseline      |
| Sesión nueva + summary| Cuando los tool results previos están stale   |

> Notebooks: `kata_018_scratchpad_persistence` cubre el patrón de summary
> persistente que sobrevive al `/compact`.

# Domain 2 — Tool Design & MCP Integration (18 %)

## Task Statement 2.1: Descripciones de tools

**El error #1 que el examen detecta**: tools con descripciones genéricas
que se solapan.

| Mal                                         | Bien                                        |
|---------------------------------------------|---------------------------------------------|
| `analyze_content`: "Analyzes content"       | `extract_web_results`: "Parses HTML…"       |
| `analyze_document`: "Analyzes documents"    | `verify_claim_against_source`: "Validates…" |

**Receta**: descripción debe incluir **input format**, **example queries**,
**edge cases**, **boundary** (cuándo usar este vs un similar).

## Task Statement 2.2: Errores estructurados (MCP)

```json
{
  "isError": true,
  "errorCategory": "rate_limit",        // transient | validation | business | permission
  "isRetryable": true,
  "retryAfterSeconds": 30,
  "explanation": "API quota exceeded for tenant X"
}
```

**Reglas**:

- `errorCategory` distingue 4 familias; cada una tiene política de retry
  distinta.
- `isRetryable: false` para business/permission errors → el agente
  **no** debe reintentar.
- **Local recovery primero**: el subagente reintenta transient localmente
  y sólo propaga al coordinador lo que no pudo resolver.

## Task Statement 2.3: Distribución de tools y `tool_choice`

| `tool_choice`                       | Significado                          |
|-------------------------------------|--------------------------------------|
| `{"type": "auto"}` (default)        | Modelo decide; puede no llamar tool  |
| `{"type": "any"}`                   | DEBE llamar algún tool               |
| `{"type": "tool", "name": "X"}`     | DEBE llamar exactamente ese tool     |

**Anti-patrón #1**: dar 18 tools a un agente. **Regla del 4-5**: cada
agente debe tener tools del tamaño de un dedo de la mano.

## Task Statement 2.4: MCP servers

| Scope            | Path                              | Compartido |
|------------------|-----------------------------------|------------|
| Project          | `.mcp.json`                       | Sí (git)   |
| User             | `~/.claude.json`                  | No         |

```jsonc
// .mcp.json — credenciales por env var, NO hardcoded
{
  "mcpServers": {
    "github": {
      "command": "npx",
      "args": ["-y","@modelcontextprotocol/server-github"],
      "env": {"GITHUB_TOKEN": "${GITHUB_TOKEN}"}
    }
  }
}
```

## Task Statement 2.5: Built-in tools

| Tool   | Para qué                                              |
|--------|-------------------------------------------------------|
| Grep   | Buscar contenido (regex en archivos)                  |
| Glob   | Buscar archivos por patrón de path (`**/*.test.tsx`)  |
| Read   | Cargar archivo completo                               |
| Edit   | Modificación dirigida con anchor único                |
| Write  | Sobrescribir; fallback cuando Edit no encuentra anchor|
| Bash   | Comandos shell                                        |

**Anti-patrón**: leer todos los archivos al inicio. Estrategia correcta:
Grep para hallar entry points → Read para seguir imports → Edit/Write
puntual.

# Domain 3 — Claude Code Configuration & Workflows (20 %)

## Task Statement 3.1: CLAUDE.md hierarchy

| Nivel              | Path                              | Compartido |
|--------------------|-----------------------------------|------------|
| User               | `~/.claude/CLAUDE.md`             | No         |
| Project            | `.claude/CLAUDE.md` o `CLAUDE.md` | Sí         |
| Directory          | `<subdir>/CLAUDE.md`              | Sí         |

```markdown
# CLAUDE.md raíz
@docs/coding-standards.md          # @import modular
@docs/testing.md
```

**`@import`** vs `.claude/rules/`: ambos valen. `@import` es bueno para
reutilizar standards entre paquetes. `.claude/rules/` es mejor cuando
quieres reglas condicionales por path (ver 3.3).

> Comando útil: `/memory` muestra qué archivos están cargados en la
> sesión actual.

## Task Statement 3.2: Custom commands & skills

| Artefacto                        | Path                       | Frontmatter clave                    |
|----------------------------------|----------------------------|--------------------------------------|
| Slash command (proyecto)         | `.claude/commands/X.md`    | (ninguno requerido)                  |
| Slash command (personal)         | `~/.claude/commands/X.md`  |                                      |
| Skill (proyecto)                 | `.claude/skills/X/SKILL.md`| `context`, `allowed-tools`, `argument-hint` |

```markdown
---
name: codebase-analysis
context: fork                      # corre en sub-agente aislado
allowed-tools: ["Read","Grep","Glob"]   # NO Write/Bash
argument-hint: "<file-or-dir>"
---
# Skill body
Analiza la estructura de {{argument}}…
```

**`context: fork`** = la skill no contamina el main session con su
output verbose. Crítico para skills exploratorias.

## Task Statement 3.3: Path-scoped rules

```yaml
# .claude/rules/tests.md
---
paths: ["**/*.test.tsx", "**/*.test.ts"]
---

# Convenciones de tests
- Usa Vitest, no Jest.
- AAA pattern: arrange/act/assert.
```

**Cuándo glob-rules superan a CLAUDE.md de subdirectorio**: cuando los
archivos a los que aplica la regla están **dispersos por todo el repo**
(p. ej., tests al lado del código). Subdirectorio sólo cubre un árbol.

## Task Statement 3.4: Plan mode vs direct execution

| Caso                                          | Modo                |
|-----------------------------------------------|---------------------|
| Refactor monolito → microservicios            | **Plan mode**       |
| Bug fix en una función con stack trace        | **Direct execution**|
| Migración de librería que toca 45+ archivos   | **Plan mode**       |
| Añadir validación de fecha a 1 endpoint       | **Direct execution**|

> Heurística: si hay **decisiones arquitectónicas** o **caminos
> alternativos**, plan mode. Si hay un patch claro de scope acotado,
> direct.

## Task Statement 3.5: Iterative refinement

Patrones del examen:

- **Few-shot examples** (2-4) cuando la prosa no comunica el formato.
- **Test-driven**: escribir tests primero, iterar con failures.
- **Interview pattern**: que Claude haga preguntas antes de implementar.
- **Sequential vs single-message**: si los problemas interactúan, mensaje
  único con todos los issues; si son independientes, secuencial.

## Task Statement 3.6: CI/CD pipelines

```bash
claude -p "$REVIEW_PROMPT" \
       --output-format json \
       --json-schema annotations.schema.json
```

**Reglas**:

- `-p` evita hangs en CI (no espera input interactivo).
- `--output-format json` + `--json-schema` produce salida machine-parseable.
- **Sesión independiente para review**: la misma sesión que generó el
  código es **peor** revisora que una instancia limpia.

# Domain 4 — Prompt Engineering & Structured Output (20 %)

## Task Statement 4.1: Criterios explícitos

| Vago                                      | Explícito                                       |
|-------------------------------------------|-------------------------------------------------|
| "be conservative with findings"           | "report issues only when actual code behavior contradicts comments" |
| "only report high-confidence issues"      | "severity ≥ medium **AND** matches one of these 5 categories"      |

> Falsos positivos altos en una categoría matan la confianza en TODAS.
> A veces conviene **deshabilitar** temporalmente la categoría problemática.

## Task Statement 4.2: Few-shot

- **2-4 ejemplos** de bordes, no de centro fácil.
- Mostrar **razonamiento** (por qué se eligió tal opción) en escenarios
  ambiguos.
- Cubrir **formatos variados** (citas inline vs bibliografía, narrativo vs
  tabla) cuando el documento puede venir en varias formas.

## Task Statement 4.3: Structured output con tool_use

```python
EXTRACT = {
    "name": "extract_invoice",
    "input_schema": {
        "type": "object",
        "properties": {
            "invoice_id": {"type": "string"},
            "stated_total": {"type": "number"},
            "computed_total": {"type": "number"},
            "currency": {"type": "string", "enum": ["USD","EUR","COP","other"]},
            "currency_other_details": {"type": ["string","null"]},
            "status": {"type": "string", "enum": ["paid","pending","unclear"]},
            "due_date": {"type": ["string","null"], "format": "date"},
        },
        "required": ["invoice_id","stated_total","computed_total","currency","status"]
    }
}
resp = client.messages.create(
    tools=[EXTRACT],
    tool_choice={"type": "tool", "name": "extract_invoice"},
    ...
)
```

**Diseño defensivo**:

- `enum` cerrado **+** `"other"` con detail string para extensibilidad.
- `null` en lugar de string vacío cuando el dato no existe.
- `tool_use` elimina errores de **sintaxis** JSON; **no** elimina errores
  semánticos (sumas que no cuadran).

## Task Statement 4.4: Validation + retry

Loop de auto-corrección:

```python
def extract_with_retry(doc, attempts=2):
    extraction = extract(doc)
    error = pydantic_validate(extraction)
    if not error: return extraction
    for _ in range(attempts):
        extraction = extract(doc, error_feedback=error)
        error = pydantic_validate(extraction)
        if not error: return extraction
    return {"extraction": extraction, "validation_error": error}
```

**Cuándo retry NO ayuda**: el dato simplemente NO está en el documento.
Reintentar es alucinación garantizada — mejor `null` + `needs_human_review`.

## Task Statement 4.5: Batch processing

| Caso                                  | API                                  |
|---------------------------------------|--------------------------------------|
| Pre-merge checks (devs esperando)     | Synchronous (real-time)              |
| Reportes overnight, audits semanales  | **Message Batches** (50% más barato) |

Restricciones del Batch API:

- Hasta 24 h de ventana, sin SLA garantizada.
- **NO soporta multi-turn tool calling** dentro de un request — batch es
  para llamadas de un solo turno.
- `custom_id` correlaciona request↔response; resubmissions sólo de los
  fallidos.

## Task Statement 4.6: Multi-pass review

- **Self-review limitations**: el modelo que generó código retiene
  contexto de razonamiento — es peor revisor de su propio output.
- **Independent instance**: una instancia limpia (sin la cadena de
  generación) detecta más issues.
- **Per-file pass + cross-file integration pass** para PRs grandes; evita
  attention dilution.

# Domain 5 — Context Management & Reliability (15 %)

## Task Statement 5.1: Conversation context

**Riesgos de la summarización progresiva**:

- Valores numéricos (montos, fechas, customer-stated expectations) se
  comprimen a frases vagas.
- "Lost in the middle": atención U-shape, hallazgos del centro se
  diluyen.

**Patrón "case facts"**: extraer datos transaccionales (`order_id`,
`amount`, `status`) a un bloque persistente que se incluye **en cada
prompt**, fuera del summary.

## Task Statement 5.2: Escalación

**Triggers válidos**:

- Cliente pide explícitamente un humano (honra inmediato).
- Policy gap (la política no cubre el caso).
- Inability to make meaningful progress.

**Triggers inválidos** (que el examen ataca):

- Sentiment-based ("cliente parece molesto") — no correlaciona con
  complejidad.
- Self-reported confidence score del LLM — está mal calibrado.

**Caso "multiple matches"**: si una búsqueda devuelve N resultados, **pide
un identificador adicional** al cliente, no escojas heurísticamente.

## Task Statement 5.3: Error propagation multi-agente

| Patrón correcto                        | Anti-patrón                              |
|----------------------------------------|------------------------------------------|
| Subagente: error tipado al coordinador | Suprimir error como "success vacío"      |
| `{failure_type, attempted, partial}`   | `"search unavailable"` genérico          |
| Retry transients localmente            | Propagar todo error al coordinador       |
| Annotaciones de coverage gap en synth  | Terminar workflow al primer error        |

## Task Statement 5.4: Context en codebases grandes

- **Subagent delegation**: el main agent coordina; los subagentes
  exploran (ver Explore subagent).
- **Scratchpad files**: hallazgos durables sobreviven `/compact`.
- **Summary-injected new session** > resumir 60 mensajes de history que
  contiene tool results stale.

## Task Statement 5.5: Human review workflows

- **Stratified random sampling** sobre extracciones high-confidence para
  detectar nuevos patrones de error.
- **Field-level confidence scores** calibrados con un validation set
  etiquetado (no la confianza self-reported del modelo).
- Aggregate "97 % accuracy" puede ocultar mal performance en un tipo de
  doc → mide por tipo y campo.

## Task Statement 5.6: Provenance

- Cada claim con `source_id`, `source_name`, `publication_date`,
  `relevant_excerpt`.
- **Conflictos preservados, no resueltos**: dos sources con stats distintas
  → registrar ambos con anotación, no promediar.
- **Fechas explícitas** evitan que diferencias temporales legítimas se
  lean como contradicciones.

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
            return src.split("## 6. Auto-evaluación", 1)[1].strip()
    return ""


def kata_section(spec_dir: pathlib.Path, nb_path: pathlib.Path) -> str:
    spec = parse_spec((spec_dir / "spec.md").read_text())
    answers = extract_self_check_md(nb_path)
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


PRACTICE_INTRO = """# Banco de preguntas de práctica

Veinte preguntas multiple-choice en el formato exacto del examen.
Cada una incluye:

- Setup (escenario en producción).
- 4 opciones A/B/C/D — los distractores son plausibles si entiendes
  el concepto a medias.
- **Respuesta correcta** y por qué cada distractor falla.

> Para que esto sea útil: tapa la respuesta antes de leerla. Si caes
> en un distractor, vuelve al kata correspondiente y al *Domain Deep
> Dive* del dominio.
"""


PRACTICE_QUESTIONS = """## Q1 (Domain 1 / Kata 01)

Tu agente de soporte llama a `process_refund` al final de un turno. La
respuesta tiene `stop_reason="end_turn"` y el texto del modelo dice
"voy a procesar el reembolso ahora mismo, listo." Tu bucle agéntico
termina. ¿Qué afirmación describe correctamente lo que pasó?

A) El modelo procesó el reembolso porque el texto confirma la acción.
B) El modelo NO procesó el reembolso; `stop_reason="end_turn"` significa
   que terminó el turno sin invocar tool, y `process_refund` quedó sin
   ejecutar.
C) El bucle debe iterar una vez más para confirmar el reembolso.
D) `stop_reason="end_turn"` indica éxito de la ejecución del tool.

**Respuesta: B**

`stop_reason="tool_use"` es la única señal que indica que hay un tool
para ejecutar. Con `end_turn`, el modelo cerró el turno; el texto
prometiendo la acción es **prosa**, no señal. A confunde texto con
ejecución (anti-patrón clásico). C suma iteraciones que no harán
ejecutar lo que ya no se requirió. D es semánticamente falso —
`end_turn` significa terminar, no éxito de tool.

---

## Q2 (Domain 1 / Kata 02)

Un agente de support tiene `process_refund` y un system prompt:
"NUNCA proceses reembolsos > $1000". En producción, el 3 % de
reembolsos ejecutados están entre $1000 y $5000. ¿Cómo lo arreglas?

A) Reforzar el system prompt con MAYÚSCULAS y repetir la regla 3 veces.
B) Añadir few-shot examples mostrando que reembolsos > $1000 deben
   rechazarse.
C) Implementar un hook `PreToolUse` que valide `tool_input["amount"]`
   y deniegue si excede $1000.
D) Añadir una nota al final de cada user message recordando el límite.

**Respuesta: C**

Los reembolsos > $1000 son una regla de **negocio crítica**. Prompt-only
(A, B, D) es probabilístico — fallará el día que un user message lo
persuada o el modelo parafrasee la política. El hook es deterministic:
el tool **no se ejecuta** si la condición no se cumple.

---

## Q3 (Domain 1 / Kata 04)

Tu sistema multi-agente coordina 3 subagentes (web search, document
analysis, synthesis). Notas que synthesis cita información que web
search no le pasó. El log muestra que el coordinador pasa a synthesis
**solo el output JSON tipado** de los otros dos. ¿Qué pasa?

A) Synthesis está alucinando porque no ve el contenido completo de
   los documentos; necesita herencia automática del historial del
   coordinador.
B) Synthesis tiene memoria entre invocaciones del coordinator que
   debe limpiarse.
C) Synthesis está alucinando; el coordinador debe pasar
   `relevant_excerpt` y `source_url` por cada finding, no solo el
   `claim`.
D) El subagente synthesis debe tener acceso directo al web search tool
   para verificar.

**Respuesta: C**

Hub-and-spoke estricto **prohíbe** herencia automática (descarta A).
El subagente no tiene memoria entre invocaciones (descarta B). Darle
acceso directo a herramientas que no son su especialidad (D) es
exactamente el anti-patrón. La causa real: el coordinador está pasando
`claim` pero no `relevant_excerpt` ni `source_url` — synthesis no tiene
de dónde extraer la evidencia.

---

## Q4 (Domain 2 / Kata 02 — Tool descriptions)

Tienes dos tools: `analyze_content` ("Analyzes content") y
`analyze_document` ("Analyzes documents"). El 23 % de las invocaciones
usa el tool incorrecto. ¿Primer paso?

A) Eliminar uno de los dos y usar uno solo para todo.
B) Reescribir las descripciones detallando input format, ejemplos de
   queries, edge cases y la frontera entre los dos.
C) Añadir un router que pre-clasifique inputs por keywords antes de
   exponerlos al modelo.
D) Bajar la temperatura del modelo a 0.

**Respuesta: B**

Las descripciones son el **único** mecanismo del LLM para escoger tool.
Si son ambiguas, el modelo no tiene cómo distinguir. B es el cambio de
mayor leverage. A puede tener sentido a largo plazo pero requiere
rediseño; B es el "primer paso" pedido. C es over-engineering. D no
ataca la causa raíz.

---

## Q5 (Domain 2 / Kata 06 — MCP errors)

Tu MCP tool `search_db` falla intermitentemente. Hoy devuelve
`{"error": "something went wrong"}`. El agente entra en bucle de
retries que agotan budget. ¿Mejor cambio?

A) Devolver `{"isError": true, "errorCategory": "transient",
   "isRetryable": true, "retryAfterSeconds": 5}` y dejar que el cliente
   gestione retries con backoff.
B) Aumentar el max_tokens para que el modelo razone mejor sobre el
   error.
C) Añadir al system prompt: "si search_db falla, no reintentes más
   de 3 veces."
D) Capturar la excepción del lado del MCP y devolver `{"results": []}`.

**Respuesta: A**

Política de retry vive en el **cliente**, no en el modelo (descarta B,
C). Devolver `[]` enmascara el fallo y el agente cree que la búsqueda
fue exitosa pero vacía (descarta D — anti-patrón). A da metadata
suficiente para que el cliente decida.

---

## Q6 (Domain 2 / Kata 16 — tool_choice)

Tu agente de extracción debe llamar SIEMPRE al tool `extract_invoice`
y nunca devolver texto. ¿Configuración correcta?

A) `tool_choice` no especificado.
B) `tool_choice = {"type": "auto"}`.
C) `tool_choice = {"type": "any"}`.
D) `tool_choice = {"type": "tool", "name": "extract_invoice"}`.

**Respuesta: D**

`auto` (default; A y B) deja al modelo decidir y puede devolver texto.
`any` (C) garantiza que llame **algún** tool, pero si tienes 3 tools
puede llamar otro. **Forced** con nombre garantiza que el tool
específico se llame.

---

## Q7 (Domain 3 / Kata 08 — CLAUDE.md hierarchy)

Un nuevo dev del equipo dice que Claude no respeta la convención de
"siempre usar Pydantic en lugar de dataclasses". Otros devs sí la ven
respetada. ¿Causa más probable?

A) El nuevo dev tiene una versión vieja de Claude Code.
B) La regla está en `~/.claude/CLAUDE.md` del dev que la creó, no en
   el `CLAUDE.md` del proyecto.
C) Los demás devs usan plan mode y el nuevo no.
D) El proyecto necesita un `.mcp.json` para servir la regla.

**Respuesta: B**

Configuración user-level (`~/.claude/CLAUDE.md`) es **local al usuario**.
Convenciones de equipo van al CLAUDE.md del proyecto (versionado en
git). El error clásico: el creador escribió la regla pensando que era
del equipo pero la dejó en su home.

---

## Q8 (Domain 3 / Kata 09 — Path-scoped rules)

Quieres que ciertas convenciones se apliquen a TODOS los archivos
`*.test.tsx`, que están **dispersos** por todo el repo (al lado del
código que testean). ¿Mecanismo correcto?

A) Un único `CLAUDE.md` raíz con la regla.
B) Un `CLAUDE.md` en cada subdirectorio que contenga tests.
C) Un archivo en `.claude/rules/` con frontmatter
   `paths: ["**/*.test.tsx"]`.
D) Un slash command `/lint-tests` que el dev invoque manualmente.

**Respuesta: C**

A carga la regla siempre, gastando tokens cuando no aplica. B es
inviable: tests están dispersos, no en un árbol contenido. D es
manual y olvidable. C es la herramienta exacta para este caso: glob-
based conditional loading.

---

## Q9 (Domain 3 / Kata 07 — Plan mode vs direct)

Tarea: refactorizar un monolito a microservicios; afecta 60+ archivos
con decisiones sobre boundaries de servicios. ¿Modo correcto?

A) Plan mode — explorar el codebase, mapear dependencias, diseñar
   antes de tocar código.
B) Direct execution — empezar por mover funciones y dejar que el
   diseño emerja.
C) Direct execution con instrucciones detalladas upfront.
D) Direct execution; cambiar a plan si surgen problemas.

**Respuesta: A**

Plan mode existe exactamente para este tipo de tarea: cambios de
gran escala con decisiones arquitectónicas. B asume que el diseño
emergerá — costoso si las dependencias se descubren tarde. C asume
que ya conoces la respuesta. D ignora que la complejidad ya está
declarada en el requirement.

---

## Q10 (Domain 3 / Custom slash command)

Quieres un `/review` disponible para todos los devs del equipo
cuando clonen el repo. ¿Dónde lo creas?

A) `.claude/commands/review.md` (en el repo).
B) `~/.claude/commands/review.md` (home del dev).
C) En el `CLAUDE.md` del proyecto.
D) En un `.claude/config.json` con un array `commands`.

**Respuesta: A**

Project-scoped commands viven en `.claude/commands/`, versionados con
el repo, disponibles tras `git pull`. B es para personal. C es para
context/instructions, no comandos. D no existe.

---

## Q11 (Domain 4 / Kata 05 — Schema design)

Extraes facturas. Algunas no tienen `due_date`. El agente está
inventando fechas plausibles cuando no hay. ¿Cambio?

A) Añadir un few-shot example mostrando una factura sin due_date.
B) Marcar `due_date` como nullable union (`{"type": ["string","null"]}`)
   y declararlo opcional, no required.
C) Bajar la temperatura.
D) Aumentar el max_tokens.

**Respuesta: B**

`required` fuerza al modelo a poner algo → alucina. Nullable union +
opcional le da una vía honesta para representar ausencia. A puede
ayudar pero no es la causa raíz: el schema mismo lo está empujando a
inventar.

---

## Q12 (Domain 4 / Kata 14 — Few-shot)

Clasificas tickets en 5 categorías. Algunos tickets ambiguos
("podría ser billing o auth") suelen mal clasificarse. ¿Mejor
intervención?

A) Añadir 2-3 few-shot examples de tickets ambiguos mostrando el
   razonamiento de por qué se eligió cierta categoría.
B) Añadir 20 examples cubriendo todas las categorías.
C) Bajar la temperatura.
D) Cambiar a un modelo más grande.

**Respuesta: A**

Few-shot bien construido (B) cubre los **bordes**, no el centro.
2-4 ejemplos de bordes con razonamiento explícito enseñan
generalización. 20 ejemplos saturan atención (Kata 11).

---

## Q13 (Domain 4 / Kata 15 — Validation/retry)

Una extracción Pydantic-validada falla porque el modelo devolvió
fechas en formato `MM/DD/YYYY` cuando el schema pide `YYYY-MM-DD`.
¿Estrategia?

A) Reintentar con la misma prompt; el modelo "verá" el error.
B) Reintentar incluyendo el doc original, la extracción fallida, y
   el specific validation error como feedback.
C) Aceptar `MM/DD/YYYY` también; no es grave.
D) Devolver error y enrutar a humano.

**Respuesta: B**

Retry-with-error-feedback es el patrón canónico para errors de
**formato/structure** (resolvable por el modelo si se le dice qué
falló). A no funciona si el modelo no sabe qué cambiar. C debilita el
contrato downstream. D es overreach para un fix automático
disponible.

---

## Q14 (Domain 4 / Kata 17 — Batch API)

Tu manager propone migrar a Batch API tanto los pre-merge checks
(blocking, devs esperando) como los reportes de tech debt overnight.
¿Cómo evalúas?

A) Migrar ambos; ahorra 50 % en costo.
B) Migrar solo los reportes overnight; mantener pre-merge en API
   real-time.
C) Mantener ambos en real-time para evitar reordenamiento de
   resultados.
D) Migrar ambos con timeout fallback a real-time.

**Respuesta: B**

Batch tiene ventana hasta 24h sin SLA. Bloquear a un dev en pre-merge
mientras Batch procesa es inaceptable. Reportes overnight encajan
perfectamente. A ignora la latencia. C deja dinero en la mesa cuando
hay un workflow ideal para batch. D agrega complejidad innecesaria.

---

## Q15 (Domain 4 / Kata 13 — Multi-pass review)

Un PR modifica 14 archivos. Tu review single-pass produce feedback
inconsistente: detallado en algunos, superficial en otros, contradictorio
entre archivos. ¿Restructuración?

A) Pasar por archivo individualmente, luego un pass de integración
   que mire data flow cross-file.
B) Pedirle al dev que parta el PR en chunks de 3-4 archivos.
C) Usar un modelo con context window más grande.
D) Correr 3 reviews independientes y reportar solo issues que
   aparezcan en al menos 2.

**Respuesta: A**

Causa raíz: attention dilution sobre 14 archivos. A ataca la causa
con **multi-pass**: profundidad por archivo + integración cross-file
en pass dedicado. B desplaza el problema al dev. C confunde tamaño de
contexto con calidad de atención. D suprime issues que sólo se
detectan intermitentemente — pierde recall.

---

## Q16 (Domain 5 / Kata 11 — Context management)

Una sesión de soporte de 30 turnos: el agente empieza a referenciar
"typical patterns" en lugar de los detalles específicos del caso.
¿Causa más probable?

A) El modelo está confundido; subir temperatura.
B) Context degradation: los detalles transaccionales (order_id,
   amount, status) se diluyeron en summary; falta un bloque de "case
   facts" persistente en cada prompt.
C) Necesitas cambiar a un modelo con context window más grande.
D) Hay que reiniciar la sesión.

**Respuesta: B**

El patrón "typical" en lugar de "specific" es la huella de
summarización progresiva. Solución: extraer datos transaccionales a
un **case facts block** que se inyecta en cada prompt fuera del
summary. C no resuelve la calidad de atención. D pierde contexto.

---

## Q17 (Domain 5 / Kata 16 — Escalación)

Un cliente dice "estoy frustrado, quiero hablar con un humano". El
issue es estándar (cambio de password, hay procedimiento claro).
¿Acción correcta?

A) Resolver el issue autónomamente, ignorando la petición.
B) Reconocer la frustración pero ofrecer resolver; escalar sólo si el
   cliente reitera la petición.
C) Honrar la petición de humano inmediatamente sin investigar.
D) Pedirle al cliente que confirme con un email.

**Respuesta: B**

Cuando el issue es **straightforward** y el cliente expresa
frustración pero el agent puede resolverlo, ofrecer resolución
acknowledging la frustración es óptimo — escalar sólo si reitera la
petición. C es válido si el cliente **explícitamente y firmemente**
demanda humano (no aplica aquí). A ignora una preference del cliente.
D introduce fricción innecesaria.

---

## Q18 (Domain 5 / Kata 06 — Error propagation multi-agente)

Un subagente de web search timeoutea. ¿Diseño de propagación correcto?

A) Subagent retorna `{"results": []}` marcado como successful.
B) Subagent propaga la excepción al top-level, terminando el workflow.
C) Subagent retorna structured error `{failure_type, attempted_query,
   partial_results, suggested_alternatives}` al coordinador.
D) Subagent reintenta indefinidamente hasta éxito.

**Respuesta: C**

Structured error context permite recovery decisions inteligentes en
el coordinador. A enmascara el fallo (anti-patrón). B termina todo
cuando había recovery posible. D bloquea el workflow.

---

## Q19 (Domain 5 / Kata 20 — Provenance)

Synthesis recibe findings de 2 subagentes con cifras de revenue
diferentes (12M vs 12.4M, ambas de fuentes credibles). ¿Acción?

A) Promediar a 12.2M y reportar.
B) Reportar la cifra del documento más reciente.
C) Estructurar el output preservando ambos valores con su source
   attribution; marcar conflict; no resolver arbitrariamente.
D) Pedir a un subagente que decida cuál es correcta.

**Respuesta: C**

Conflictos se preservan, no se resuelven. Promediar (A) introduce un
número fabricado. "Más reciente gana" (B) no es siempre cierto y
oculta el conflicto. D es delegación sin información — el subagente
no tiene mejor base para decidir.

---

## Q20 (Domain 5 / Kata 18 — Scratchpad)

Una investigación de codebase de varias horas alcanza el límite de
contexto. `/compact` viene; vas a perder hallazgos detallados. ¿Mejor
defensa preventiva?

A) Subir el max_tokens.
B) Mantener un scratchpad file con findings clave (qué funciones
   importan, decisiones tomadas) que el agente lee al reanudar.
C) Reiniciar la sesión cada hora.
D) Imprimir todo el output a un log al terminar.

**Respuesta: B**

Scratchpad estructurado sobrevive `/compact` y reanudaciones — es la
contramedida específica para context degradation en investigaciones
largas. A no resuelve nada. C pierde contexto. D no recupera nada en
la sesión actual.

"""


BONUS_TOPICS = """# Topics bonus — examen-relevantes pero no profundos en katas

Estos aparecen en el examen y los katas los tocan tangencialmente. Vale
la pena memorizarlos:

## Session resumption y forking (Agent SDK / Claude Code CLI)

| Comando                         | Para qué                                          |
|---------------------------------|---------------------------------------------------|
| `--resume <session-name>`       | Continúa una sesión nombrada (named resume)       |
| `fork_session`                  | Crea una rama paralela desde una baseline        |
| Sesión nueva + summary inyectado| Mejor que resume cuando los tool results stale    |

**Decisión clave**: si el contexto previo sigue *válido*, resume. Si los
tool results pueden estar stale (archivos modificados, datos cambiados),
**comienza nueva** con summary inyectado.

## Skills frontmatter (Claude Code)

```markdown
---
name: explore-architecture
context: fork                   # corre en sub-agente aislado
allowed-tools: ["Read","Grep","Glob"]
argument-hint: "<dir-or-feature>"
---
```

- **`context: fork`**: la skill corre en sesión separada; su output verbose
  no contamina la principal.
- **`allowed-tools`**: restricción de tools durante la skill. Útil para
  prevenir destructive actions.
- **`argument-hint`**: prompt al dev cuando invoca la skill sin args.

## Comandos de Claude Code

| Comando      | Uso                                                  |
|--------------|------------------------------------------------------|
| `/memory`    | Ver qué CLAUDE.md y rules están cargados             |
| `/compact`   | Comprimir context manualmente                        |
| `/resume`    | Reanudar sesión nombrada                             |

## Tools built-in vs MCP — cuándo cada uno

- **Built-in**: Read, Write, Edit, Bash, Grep, Glob — cubren operaciones
  de filesystem y shell. Fast, no requieren config.
- **MCP**: integraciones externas (GitHub, Jira, DBs custom). Configurar
  via `.mcp.json` con env-var expansion para tokens.

> **Anti-patrón**: usar MCP para algo que un built-in resuelve. Si un
> dev pregunta "necesito buscar imports en el repo", la respuesta es
> Grep, no un MCP server custom.

## Confidence calibration y stratified sampling

Para extracciones automatizadas en producción:

- **Field-level confidence** (output del modelo) calibrado contra un
  **labeled validation set** — la confianza self-reported sin calibrar
  está sesgada.
- **Stratified random sampling** sobre extracciones high-confidence:
  permite detectar nuevos patrones de error que la validación normal no
  captura.
- Reportar accuracy por **document type** y **field segment**, no
  agregada — el 97 % global puede ocultar 60 % en un tipo de doc.

## Coverage gap reporting (Multi-agent)

Synthesis output debe estructurarse con secciones que distinguen:

- **Well-supported findings** (varias fuentes confirman).
- **Contested findings** (fuentes disagree; preservar ambas).
- **Coverage gaps** (topic donde las fuentes no devolvieron data).

> Si un subagente no encuentra info, el output del synthesis debe
> reflejar el gap, no rellenar.

"""


GLOSSARY = """# Glosario

**`@import`.** Sintaxis en CLAUDE.md para incluir otros markdown files
modularmente. Permite reutilizar standards entre proyectos.

**`AgentDefinition`.** Configuración del Agent SDK por subagente:
descripción, system prompt, tool restrictions.

**`allowedTools`.** Configuración del coordinador que restringe qué
tools puede usar. Para spawnear subagentes vía `Task`, debe incluir
`"Task"`.

**Agent SDK (Claude Agent SDK).** Librería para construir agentes
custom. Provee bucles agénticos, hooks (`PostToolUse`, tool call
interception), spawning de subagentes.

**Anti-patrón.** Implementación que parece funcionar y falla en
producción. Cada kata documenta uno; el examen los detecta.

**Bootstrap (`katas._shared.bootstrap`).** Helper del workshop que pide
la API key y construye un cliente con presupuesto.

**Budget guard.** Wrapper sobre `client.messages.create` que aborta
después de N llamadas, previniendo loops costosos.

**Cache control (`cache_control: ephemeral`).** Marca un bloque como
cacheable a nivel SDK. Implementa prefix caching.

**Case facts block.** Sub-bloque persistente del prompt con datos
transaccionales (order_id, amount, status) que sobrevive a la
summarización progresiva.

**`CLAUDE.md`.** Configuración persistente. Tres niveles: user
(`~/.claude/CLAUDE.md`), project (`.claude/CLAUDE.md` o `CLAUDE.md`),
directory (subdirs).

**Claude Code.** CLI/IDE para desarrollo asistido. Diferente del
Anthropic API SDK.

**Coordinator-subagent.** Patrón hub-and-spoke. El coordinador delega,
no comparte historial automáticamente.

**`context: fork`.** Frontmatter de SKILL.md que ejecuta la skill en
sub-agente aislado.

**`custom_id`.** Identificador único por request en Message Batches API.
Permite correlación 1:1 input↔output.

**Determinismo.** Mismas señales → mismas decisiones. Sólo metadata
estructurada (`stop_reason`, hook verdict) lo garantiza.

**Edge placement.** Reglas críticas al inicio Y al final del contexto
para sobrevivir lost-in-the-middle.

**Escape enum.** Enum value (`other`, `unclear`) acompañado de un
detail string. Permite al modelo admitir ambigüedad.

**`errorCategory`.** Campo MCP estructurado: `transient | validation |
business | permission`. Cada categoría tiene política de retry distinta.

**`fork_session`.** Crea rama paralela desde una baseline para explorar
enfoques divergentes.

**Hub-and-spoke.** Topología: coordinador central, N subagentes
aislados, cero aristas laterales.

**`isError` / `isRetryable`.** Flags MCP en el resultado de un tool.
Cliente decide retry/escalate desde estos flags, no desde prosa.

**`isolation_fork` / `--resume`.** Mecanismos de session management.

**Lost in the middle.** Atención U-shape: bordes alta, centro baja.

**MCP (Model Context Protocol).** Protocolo estándar para tools y
resources externos. Servidores se configuran en `.mcp.json`.

**Multi-pass review.** Revisar PRs grandes en pasadas: per-file
analysis + cross-file integration pass.

**Plan mode.** Modo read-only para tareas con decisiones
arquitectónicas. Cliente entrega tools distintas en cada fase.

**Prefix caching.** Reutilización del KV cache cuando el prefijo del
prompt coincide turno a turno. Estático arriba, dinámico abajo.

**`PreToolUse` / `PostToolUse` hook.** Funciones que corren antes
(gate) o después (normalización) de la herramienta.

**Provenance.** Mapeo `claim → source` preservado. Conflictos se
mantienen anotados, no se resuelven.

**Scratchpad.** Archivo markdown estructurado con findings durables.
Sobrevive `/compact` y resume.

**Skill (`.claude/skills/X/SKILL.md`).** Pieza on-demand con
frontmatter (`context`, `allowed-tools`, `argument-hint`).

**`stop_reason`.** Metadata estructurada del Message: único árbitro
del control de flujo.

**Stratified random sampling.** Muestreo proporcional sobre
extracciones high-confidence para detectar nuevos errores.

**Subagent.** Llamada nueva e independiente con prompt mínimo y
salida tipada. Cero memoria heredada.

**`Task` tool.** Mecanismo del Agent SDK para spawnear subagentes
desde el coordinador.

**`tool_choice`.** Configuración: `auto` (default), `any` (fuerza
algún tool), forced (`{"type":"tool","name":"X"}`).

**`tool_use` block.** Bloque del response cuando `stop_reason="tool_use"`.
Contiene `name`, `input`, `id`.
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
| 13 | Headless CI review                  | `claude -p` con schema; `jsonschema.validate` antes de publicar         |
| 14 | Few-shot                            | 2-4 ejemplos de bordes, no del centro fácil                             |
| 15 | Self-correction                     | `mismatch` y `needs_human_review` son required, no se autocorrige       |
| 16 | Human handoff                       | Tool con schema estricto y enum de motivo; suspende generación de prosa |
| 17 | Batch processing                    | `custom_id` único, polling/webhook, recuperación selectiva              |
| 18 | Scratchpad                          | Memoria persistente fuera de la conversación; sobrevive a `/compact`    |
| 19 | Adaptive investigation              | Topology → prioritize → deep-dive con presupuesto y re-plan             |
| 20 | Data provenance                     | Cada claim con `source_id`; conflictos preservados, no resueltos        |
| 21 | Tool descriptions                   | Descripción = árbitro de selección; explícita y diferenciadora          |
| 22 | MCP server config                   | Project (`.mcp.json`) vs user (`~/.claude.json`); env-var expansion     |
| 23 | Built-in tools                      | Grep contenido, Glob paths; Edit fail → Read+Write; incremental         |
| 24 | Slash commands & skills             | `.claude/commands/` proyecto; SKILL.md frontmatter `context: fork`      |
| 25 | Session management                  | Resume si válido; fork para paralelo; fresh+summary si stale            |
| 26 | Validation-retry                    | Loop con feedback específico; recuperable vs ausente                    |
| 27 | Multi-pass review                   | Independent reviewer (sesión nueva); per-file + cross-file              |
| 28 | Multi-agent errors                  | Distinguir failure vs empty_valid; local recovery + structured prop.    |
| 29 | Confidence calibration              | Calibrar conf raw vs labeled set; stratified sampling                   |
| 30 | Explicit criteria                   | Categorías con criterios "report SI / NO SI" + ejemplos; FP por cat.    |

## Diez reglas para repetir antes del examen

1. **Control por señal**, no por prosa.
2. **Hooks, no prompts** para reglas críticas (financial, identity).
3. **Schemas fallan cerrados**; nullable union antes que required-fabricado.
4. **Subagentes con prompt mínimo y output tipado**; cero historial heredado.
5. **Estático arriba, dinámico abajo**; reglas en bordes.
6. **Errores tipados** (`isError`, `errorCategory`, `isRetryable`), retry en cliente.
7. **Plan mode** ante decisiones arquitectónicas; **direct** ante scope claro.
8. **Few-shot 2-4 de bordes**, schema-consistent.
9. **Batch para no-blocking**; synchronous para blocking.
10. **Provenance preservada**, conflictos anotados, no resueltos.

## Diez anti-patrones para reconocer al instante

| Síntoma                                      | Anti-patrón                  |
|----------------------------------------------|------------------------------|
| `if "done" in text`                          | Prose-based termination      |
| Política sólo en system prompt               | Prompt-only enforcement      |
| Subagente recibe history del coordinador     | Telepatía compartida         |
| `required: true` para todos los campos       | Forced fabrication           |
| Tool error como string `"failed"`            | Untyped error                |
| Reembolsos > X aprobados con prompt warning  | Soft control on hard rule    |
| Timestamp al inicio del system prompt        | Cache-breaking               |
| Regla crítica en mitad de un prompt largo    | Lost-in-the-middle           |
| 18 tools al mismo agente                     | Tool overload                |
| Resumen agregado sin source_id               | Provenance loss              |
"""


OUT_OF_SCOPE = """# Out-of-scope (NO entra en el examen)

No pierdas tiempo estudiando esto:

- Fine-tuning o entrenamiento de modelos custom.
- Authentication, billing, o account management de la Claude API.
- Implementación detallada en lenguajes/frameworks específicos (más
  allá de tools y schemas).
- Deploying o hosting de MCP servers (infra, networking, contenedores).
- Arquitectura interna de Claude, training process, model weights.
- Constitutional AI, RLHF, safety training.
- Embedding models o vector DB internals.
- Computer use (browser automation, desktop interaction).
- Vision/image analysis.
- Streaming API o server-sent events.
- Rate limiting, cuotas o cálculos de pricing.
- OAuth, rotación de API keys, protocolos auth.
- Configuraciones específicas de cloud (AWS/GCP/Azure).
- Performance benchmarking entre modelos.
- Detalles de implementación de prompt caching más allá de "existe".
- Algoritmos de tokenización.

> **Lo que sí cubre el examen** (resumen): ver "Examen de un vistazo" al
> inicio. Si una pregunta empieza con "you are deploying an MCP server
> on Kubernetes…", revisa el wording — probablemente es una distracción
> que apunta a la decisión arquitectónica (qué scope usar), no a la
> mecánica de despliegue.

"""


def main() -> int:
    parts = [
        COVER,
        EXAM_AT_A_GLANCE,
        SCENARIO_TO_KATA_MAP,
        DOMAIN_DEEP_DIVES,
    ]

    spec_dirs = sorted([d for d in SPECS.iterdir() if d.is_dir() and d.name[:3].isdigit()])
    nb_paths = {d.name.split("_")[1]: d / "notebook.ipynb" for d in KATAS.iterdir() if d.name.startswith("kata_")}

    parts.append("# Cards conceptuales por kata")
    parts.append("")
    parts.append("Una página por kata. Útil como repaso visual el día anterior.")
    parts.append("")

    for spec_dir in spec_dirs:
        kata_id = spec_dir.name.split("-")[0]
        nb = nb_paths.get(kata_id)
        if nb is None or not nb.exists():
            print(f"WARN: notebook missing for {spec_dir.name}", file=sys.stderr)
            continue
        parts.append(kata_section(spec_dir, nb))

    parts.append(PRACTICE_INTRO)
    parts.append(PRACTICE_QUESTIONS)
    parts.append(BONUS_TOPICS)
    parts.append(GLOSSARY)
    parts.append(CHEAT_SHEET)
    parts.append(OUT_OF_SCOPE)

    out = REPO / "STUDY_GUIDE.md"
    out.write_text("\n\n".join(parts))
    print(f"wrote {out} ({out.stat().st_size:,} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
