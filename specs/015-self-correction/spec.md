# Kata 15 — Evaluación Crítica y Auto-Corrección

## Concepto

Cuando el modelo extrae números (totales, sumas, fechas calculadas), debe
**cruzar lo que calculó vs lo que la fuente declara**. Si discrepan, no decide
arbitrariamente: emite un flag de conflicto y enruta a revisión humana.

## Por qué importa

Un total de factura calculado por el modelo puede coincidir con el declarado…
o no. Sin verificación cruzada, el sistema confía silenciosamente en la
alucinación más plausible. En facturación o contabilidad, eso es un incidente.

## Modelo mental

- Dos fuentes de verdad: lo declarado en el documento y lo calculado por el
  agente. Deben coincidir.
- Si difieren más allá de un epsilon, marcar `mismatch=true` con ambos valores.
- Nunca "elegir el más razonable". Escalar (Kata 16).
- Aplica a: totales numéricos, sumas, conteos, fechas derivadas.

## Ejemplo mínimo

```json
{
  "stated_total": 1234.56,
  "computed_total": 1230.00,
  "mismatch": true,
  "delta": 4.56,
  "needs_human_review": true
}
```

Cliente:

```python
if abs(stated - computed) > epsilon:
    flag_for_review(invoice, stated, computed)
```

## Anti-patrón

Tomar `stated_total` directo o, peor, "corregirlo" silenciosamente al
`computed_total` sin avisar. Puede ocultar fraude, errores de OCR, o
alucinación del propio modelo.

## Argumento de certificación

- Sé identificar campos numéricos sujetos a verificación cruzada.
- Sé definir el epsilon de tolerancia (cero para enteros, ε pequeño para
  monedas) y justificarlo.
- Sé conectar este kata con Kata 16 (escalada humana) y Kata 20 (provenance).

## Auto-evaluación

1. ¿Qué pasa si el documento no declara total (sólo línea por línea)?
2. ¿Cómo distingo "error de OCR" de "fraude" en el flag?
3. ¿Qué prueba reintroduce el anti-patrón (auto-corrección silenciosa) y qué
   assert falla?
