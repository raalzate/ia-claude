# Kata 05 — Extracción Estructurada Defensiva con JSON Schema

## Concepto

Para extraer datos de texto no estructurado, se fuerza al modelo a usar un
**tool call con JSON Schema**. El schema declara: campos obligatorios reales,
campos opcionales con uniones nullable, y enums con válvula de escape (`other`,
`unclear`) acompañada de un campo `details`.

## Por qué importa

Pedirle al modelo "devuélveme JSON" en prosa libre garantiza alucinación
silenciosa: inventará campos faltantes, llenará vacíos con `""`, o forzará
valores fuera de dominio. El schema es el único contrato que falla cerrado.

## Modelo mental

- "Required" significa "siempre presente en la fuente"; si no lo es, márcalo
  nullable union.
- Default `""` es alucinación: si no sabe, debe ser `null` o `unclear`.
- Enums sin escape obligan al modelo a mentir cuando el valor no encaja.
- `tool_choice` forzado evita que devuelva texto y haga "best-effort prosa".

## Ejemplo mínimo

```json
{
  "name": "extract_invoice",
  "input_schema": {
    "type": "object",
    "required": ["invoice_id", "currency", "status"],
    "properties": {
      "invoice_id": {"type": "string"},
      "currency": {"type": "string", "enum": ["USD","EUR","COP","other"]},
      "currency_other_details": {"type": ["string","null"]},
      "status": {"type": "string", "enum": ["paid","pending","unclear"]},
      "due_date": {"type": ["string","null"], "format": "date"}
    }
  }
}
```

El cliente valida el resultado y rechaza si no encaja; nunca "ajusta" la salida.

## Anti-patrón

JSON pedido en prosa, sin schema, con todos los campos `required` y sin enums
con escape. Garantiza fabricación silenciosa: el modelo prefiere inventar a
admitir incertidumbre.

## Argumento de certificación

- Sé justificar `tool_choice` forzado vs prompt-only.
- Sé explicar la diferencia entre `nullable` y `optional` y por qué importa.
- Sé diseñar enums que admitan ambigüedad sin romper el contrato.

## Auto-evaluación

1. Si el dato no aparece en la fuente, ¿qué valor debe poner el modelo?
2. ¿Por qué `currency_other_details` es necesario al lado del enum?
3. ¿Qué prueba demuestra que el schema bloquea fabricación cuando reintroduzco
   `required` excesivos?
