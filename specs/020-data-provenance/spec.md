# Kata 20 — Preservación de Provenance

## Concepto

Cada afirmación factual extraída de fuentes mantiene un **mapeo tipado a su
origen**: `claim`, `source_id`, `source_name`, `publication_date`. Los conflictos
entre fuentes NO se resuelven en silencio: se marcan y se enrutan a humano.

## Por qué importa

Tras agregar contenido de muchas fuentes vía subagentes (Kata 4), perder el
hilo de "quién dijo qué" hace imposible auditar el resultado. Resúmenes en
prosa libre **se ven correctos** y aluciinan sin que se note. Provenance es la
única defensa.

## Modelo mental

- No hay claim sin source. Es un invariante de schema.
- Si dos fuentes contradicen, se registran ambas bajo `conflict: true`, no se
  promedia ni se elige.
- La fecha de publicación importa: fuente más reciente no siempre gana, pero
  el humano necesita verla.
- El reporte final preserva la lista de claims tipados; la prosa, si existe,
  se genera **a partir** de esa lista, no la sustituye.

## Ejemplo mínimo

```json
{
  "claim": "ARR Q3 2025 = 12M USD",
  "sources": [
    {"id": "doc-A", "name": "Annual Report 2025", "date": "2025-12-01"},
    {"id": "doc-B", "name": "Investor Deck", "date": "2025-09-15"}
  ],
  "conflict": false
}
```

Conflicto:

```json
{
  "claim": "Headcount end-2025",
  "sources": [
    {"id":"doc-A","name":"Report","date":"2025-12-01","value":"450"},
    {"id":"doc-C","name":"HR export","date":"2026-01-10","value":"462"}
  ],
  "conflict": true,
  "needs_human_review": true
}
```

## Anti-patrón

- Resumen agregado en prosa, sin citas, sin source_id. Imposible auditar.
- "Resolver" el conflicto eligiendo la fuente que parece más oficial.
- Asumir que la fuente más nueva siempre gana.

## Argumento de certificación

- Sé enunciar el invariante "no hay claim sin source".
- Sé describir la política de conflictos (registrar ambos, escalar).
- Sé conectar este kata con Kata 4 (agregación tras subagentes), Kata 15
  (verificación numérica) y Kata 16 (escalada humana).

## Auto-evaluación

1. ¿Qué hago si la fuente no tiene fecha?
2. ¿Cuándo dos sources con el mismo `value` cuentan como "una sola
   confirmación" y cuándo como dos?
3. ¿Qué prueba reintroduce el anti-patrón (prosa sin citas) y qué assert falla?
