# Kata 21 — Calidad de Descripciones de Tools

## Concepto

La descripción de un tool es **el único** mecanismo que el modelo usa para
decidir cuál llamar. Una descripción mínima ("Analyzes content") deja al
modelo adivinar entre tools similares. Una buena descripción incluye:
input format, query examples, edge cases y la **frontera** explícita
("usa esto en lugar de X cuando…").

## Por qué importa

El día que tienes `analyze_content` y `analyze_document` con descripciones
genéricas, el modelo escoge mal en 20-30 % de los turnos. Y como el
síntoma es "respuesta razonable pero del tool incorrecto", la falla no se
ve en logs hasta que un downstream rompe.

## Modelo mental

- Descripción = contrato de uso. Si dos tools tienen contratos solapados,
  son ambiguos por diseño.
- Renombrar es preferible a "explicar más" cuando los nombres son
  confusos (`analyze_content` → `extract_web_results`).
- Splitting beats overloading: una herramienta con 5 propósitos confunde;
  cinco con un propósito cada una son claras.
- El system prompt **interactúa** con la descripción: keywords del prompt
  pueden sesgar el routing.

## Ejemplo mínimo

```python
# Malo
{"name": "analyze_content", "description": "Analyzes content"}
{"name": "analyze_document", "description": "Analyzes documents"}

# Bueno
{
  "name": "extract_web_results",
  "description": (
    "Parses HTML pages from a search query into a list of "
    "{title, url, snippet} items. Use this when the input is a URL or "
    "raw HTML; for PDF/DOCX use parse_document instead."
  ),
}
```

## Anti-patrón

Descripciones de una línea genéricas, nombres solapados, o un único tool
"hacelo todo" que recibe un parámetro `mode`. Cualquiera de las tres
fuerza al modelo a adivinar.

## Argumento de certificación

- Sé enunciar la regla: descripciones son el árbitro de selección.
- Sé identificar tools ambiguos por contrato y proponer split o rename.
- Sé revisar el system prompt para detectar keywords que sesgan.

## Auto-evaluación

1. Si dos tools quedan solapados, ¿prefiero renombrar o "explicar más"?
2. ¿Cómo mido empíricamente la tasa de tool misrouting?
3. ¿Qué hago si el system prompt usa una keyword que el modelo asocia con
   el tool incorrecto?
