# Kata 13 — Code Review Headless en CI/CD

## Concepto

Claude Code corre en CI sin TTY (`claude -p ...`) y produce **JSON estructurado**
con anotaciones por línea. El pipeline parsea el JSON con un schema y publica
comentarios deterministas en el PR. No hay regex sobre prosa libre.

## Por qué importa

Un reviewer humano se cansa, falla, y no escala a 100 PRs/día. Un reviewer LLM
en CI encuentra issues consistentes (estilo, secrets, anti-patrones) en cada
PR. Pero sólo si su salida es **estructurada** — si no, el pipeline tendrá que
parsear prosa y romperá el primer día que el modelo cambie de redacción.

## Modelo mental

- `claude -p "prompt" --output-format=json` → JSON contra schema declarado.
- Schema: lista de `Annotation { file, line, severity, rule_id, message }`.
- El runner del CI valida con el schema; si falla, falla el job, no se "ajusta".
- Humano sigue siendo el gate final de merge.

## Ejemplo mínimo

```yaml
# .github/workflows/review.yml
- run: |
    claude -p "$REVIEW_PROMPT" \
           --output-format=json \
           --schema annotations.schema.json \
           > out.json
- run: python scripts/post_annotations.py out.json
```

`post_annotations.py` valida con el schema y crea comentarios de PR. Cero
parsing de texto.

## Anti-patrón

Pedir review en prosa y hacer `grep "ERROR"` sobre el output. Falla el día que
el modelo escriba "issue" o "warning" o cambie de idioma. Sin schema, el CI
está apostando.

## Argumento de certificación

- Sé describir el flag `--output-format=json` y la validación con schema.
- Sé conectar este kata con Kata 5 (extracción defensiva) y Kata 1 (control
  por señal, no por prosa).
- Sé justificar por qué el humano sigue siendo gate final.

## Auto-evaluación

1. ¿Qué hace el CI si el JSON no valida contra el schema?
2. ¿Cómo cacheo prompts caros en CI sin invalidar el caché por turno (Kata 10)?
3. ¿Qué reviews delego al modelo y cuáles dejo para humano?
