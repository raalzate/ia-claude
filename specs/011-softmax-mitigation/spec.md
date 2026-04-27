# Kata 11 — Mitigación de Dilución Softmax (Edge Placement + Compactación)

## Concepto

La curva de atención del transformer tiene forma de U: lo del inicio y el final
del contexto se atiende fuerte; lo del medio se diluye ("lost in the middle").
Por eso las reglas duras se colocan en los **bordes** del prompt, y cuando el
contexto pasa ~50 %, se **compacta** antes de que se pierdan.

## Por qué importa

Un agente puede estar siguiendo una política perfectamente al turno 5 y
violarla al turno 30 sin "olvidarla" — sólo dejó de atenderla porque quedó en
el medio. La pérdida es silenciosa y no aparece en logs.

## Modelo mental

- Bordes = atención alta. Centro = baja.
- Reglas críticas (seguridad, compliance) → al inicio Y se repiten al final
  como `<reminder>`.
- Detalles ricos (datos, código) → centro.
- Contexto > 50 % → compactar: resumen estructurado + scratchpad (Kata 18).
- "Compactar" no es "borrar"; es "reescribir en forma densa preservando
  invariantes".

## Ejemplo mínimo

```
[SYSTEM]   reglas críticas duras                     ← borde
[CONTEXT]  archivos, datos, conversación pasada      ← centro
[USER]     pregunta actual
[REMINDER] mismas reglas críticas, reformuladas      ← borde
```

Política de compactación:

```python
if usage_fraction(history) > 0.55:
    history = compact(history, preserve=["rules","decisions","escalations"])
```

## Anti-patrón

Poner la regla más importante una sola vez, en medio de un system prompt
gigante. El día que el contexto crece, la regla queda en el valle de la U y
deja de aplicarse — sin error visible.

## Argumento de certificación

- Sé describir la curva U y nombrar el efecto "lost in the middle".
- Sé enunciar la regla "bordes para reglas, centro para datos".
- Sé fijar un umbral concreto de compactación (50–60 %) y justificarlo.

## Auto-evaluación

1. ¿Por qué repetir la misma regla al inicio y al final no es redundancia?
2. ¿Qué se compacta primero: turnos antiguos del usuario o tool_results
   intermedios?
3. ¿Cómo pruebo que una regla "olvidada" se sigue aplicando tras compactar?
