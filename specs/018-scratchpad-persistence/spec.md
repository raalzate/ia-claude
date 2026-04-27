# Kata 18 — Scratchpad Persistente

## Concepto

Un archivo (`investigation-scratchpad.md`) externo a la conversación donde el
agente vuelca **descubrimientos durables**: hipótesis confirmadas, decisiones,
hallazgos de archivos. Sobrevive a `/compact` y a reinicios de sesión.

## Por qué importa

Cuando el contexto se compacta (Kata 11), se pierde detalle. Si un descubrimiento
crítico vivía sólo en el historial conversacional, desaparece. El scratchpad es
memoria persistente curada por el propio agente.

## Modelo mental

- Conversación = memoria volátil (puede compactarse o resetearse).
- Scratchpad = memoria persistente (archivo en disco).
- El agente escribe sólo conclusiones validadas, no monólogo.
- Estructurado en secciones: Hipótesis, Decisiones, Hallazgos, Pendientes.
- Al inicio de cada sesión nueva, el agente lee el scratchpad como contexto.

## Ejemplo mínimo

```markdown
# Investigation Scratchpad

## Decisiones
- 2026-04-25: usar pydantic v2 (T-19 confirmó compatibilidad).

## Hallazgos
- `src/legacy/parser.py` tiene un bug de offset (línea 142). Replicado.

## Pendientes
- Revisar si `--strict` rompe tests integration-*.
```

Tool de escritura:

```python
def append_scratchpad(section: str, entry: str): ...
```

## Anti-patrón

- "Mantener todo en la conversación, ya recordará". Falla al primer `/compact`.
- Escribir el scratchpad en prosa libre y largo: pierde su función de memoria
  densa.
- Re-leer todo el scratchpad cada turno (rompe caché, ver Kata 10): leer al
  inicio y referenciar después.

## Argumento de certificación

- Sé describir la diferencia entre memoria conversacional y memoria persistente.
- Sé enunciar qué se escribe en el scratchpad y qué no.
- Sé conectar este kata con Kata 11 (compactación) y Kata 19 (investigación
  adaptativa).

## Auto-evaluación

1. ¿Qué pasa si el scratchpad y la conversación se contradicen?
2. ¿Cuándo el agente debe **borrar** entradas del scratchpad?
3. ¿Cómo verifico que un hallazgo sobrevivió a `/compact`?
