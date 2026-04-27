# Specs — 20 katas para Claude Certified Architect

Cada carpeta `NNN-<slug>/` contiene **un único archivo**: `spec.md`. Una página
de concepto enfocada al examen.

El **entregable de cada kata** es un Jupyter notebook en
`katas/kata_NNN_<slug>/notebook.ipynb`. La plantilla está en
[`_templates/notebook-template.ipynb`](_templates/notebook-template.ipynb).
La arquitectura común a los 20 notebooks (bootstrap, cliente real, presupuesto,
log) está documentada en [`../ARCHITECTURE.md`](../ARCHITECTURE.md).

## Estructura del `spec.md`

1. **Concepto** — qué es la idea, en 1-2 párrafos.
2. **Por qué importa** — la falla real que evita.
3. **Modelo mental** — cómo pensarlo (3-5 bullets).
4. **Ejemplo mínimo** — pseudocódigo o snippet conceptual.
5. **Anti-patrón** — el error común y por qué falla.
6. **Argumento de certificación** — lo que el arquitecto debe defender.
7. **Auto-evaluación** — preguntas para medirse.

## Estructura del `notebook.ipynb` (Constitución, Principio VIII)

1. **Concepto en mis palabras**
2. **Por qué importa**
3. **Ejemplo correcto** (código corriendo)
4. **Anti-patrón lado a lado** (código corriendo, fallando o degradado)
5. **Argumento de certificación**
6. **Auto-evaluación respondida**

Sin TDD, sin pytest, sin `.feature`, sin `plan.md`/`tasks.md` por kata. El
notebook es el documento, la prueba y el portafolio del practicante.

## Cómo trabajar un kata

1. Lee el `spec.md` completo.
2. Responde mentalmente la sección "Auto-evaluación".
3. Copia `_templates/notebook-template.ipynb` a `katas/kata_NNN_<slug>/notebook.ipynb`.
4. Llena las seis secciones; ejecuta de arriba a abajo sin manualidades.
5. Si algo no queda claro, consulta `ia-claude-manual-20-katas.pdf` y la
   documentación oficial de Anthropic.

## Mapa de katas

| #  | Tema                                | Principio dominante      |
|----|-------------------------------------|--------------------------|
| 01 | Bucle agéntico determinista         | Determinismo             |
| 02 | Guardarraíles `PreToolUse`          | Determinismo             |
| 03 | Normalización `PostToolUse`         | Economía de contexto     |
| 04 | Aislamiento de subagentes           | Aislamiento              |
| 05 | Extracción defensiva con schema     | Schemas                  |
| 06 | Errores estructurados en MCP        | Determinismo             |
| 07 | Plan Mode (exploración segura)      | Human-in-the-loop        |
| 08 | Memoria jerárquica `CLAUDE.md`      | Economía de contexto     |
| 09 | Reglas condicionales por ruta       | Economía de contexto     |
| 10 | Prefix caching                      | Economía de contexto     |
| 11 | Mitigación de softmax (edge + compact) | Economía de contexto  |
| 12 | Prompt chaining                     | Economía de contexto     |
| 13 | Code review headless en CI          | Determinismo             |
| 14 | Few-shot para bordes                | Calidad pragmática       |
| 15 | Auto-corrección numérica            | Provenance               |
| 16 | Handoff a humano                    | Human-in-the-loop        |
| 17 | Procesamiento en batches            | Economía operacional     |
| 18 | Scratchpad persistente              | Memoria                  |
| 19 | Investigación adaptativa            | Memoria + Aislamiento    |
| 20 | Provenance de datos                 | Provenance               |

## Conexiones entre katas

- **Determinismo (1, 2, 6, 13)** — control por señal estructurada.
- **Schemas (5, 13, 15, 16, 20)** — contratos tipados que fallan cerrados.
- **Economía de contexto (3, 8, 9, 10, 11, 12)** — ¿dónde va cada token?
- **Memoria (8, 11, 18, 19)** — qué persiste, qué se compacta, qué se descarta.
- **Aislamiento (4, 12, 19)** — cada subagente ve lo mínimo.
- **Human-in-the-loop (7, 16, 15)** — cuándo el agente debe parar.
