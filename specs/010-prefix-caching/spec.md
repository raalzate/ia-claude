# Kata 10 — Optimización Económica con Prefix Caching

## Concepto

La API de Claude reusa el caché KV cuando el **prefijo** del prompt es idéntico
turno a turno. Si organizamos el contexto como **estático primero, dinámico al
final**, el primer ~90 % del prompt entra en caché y se factura ~10 % del costo.

## Por qué importa

Insertar la fecha actual o el `user_id` al inicio del prompt invalida el caché
en cada llamada. Mismo contenido, 10× más caro. El orden importa más que el
volumen.

## Modelo mental

- Estático = system prompt, CLAUDE.md, definiciones de tools, contexto pesado
  del repo.
- Dinámico = input del usuario, timestamps, estado efímero.
- Regla: estático arriba, dinámico abajo. El borde dinámico se aísla con tags
  XML (`<reminder>`) para no ensuciar el prefijo.
- Métrica: `cache_creation_input_tokens` vs `cache_read_input_tokens`.

## Ejemplo mínimo

```python
messages = [
    {"role": "system", "content": SYSTEM_PROMPT_BIG_AND_STABLE},   # estático
    {"role": "user", "content": REPO_CONTEXT_BIG},                  # estático
    *prior_turns,                                                   # estático
    {"role": "user", "content": f"<reminder>now: {now}</reminder>\n{user_input}"},
]
```

Mismo system + mismo repo entre llamadas → cache hit.

## Anti-patrón

```python
content = f"Today is {today}. {SYSTEM_PROMPT}"   # ❌ rompe caché
```

Cualquier valor que cambie por turno al inicio invalida todo lo que sigue.

## Argumento de certificación

- Sé enunciar la regla "static-prefix-first, dynamic-suffix-last".
- Sé interpretar las métricas `cache_creation` vs `cache_read`.
- Sé estimar el ahorro económico esperado (orden de magnitud ≈ 10×).

## Auto-evaluación

1. ¿Dónde meto la fecha actual sin romper el caché?
2. Si el system prompt cambia un carácter, ¿qué pasa con el caché?
3. ¿Cómo demuestro empíricamente el ahorro? (qué métrica, qué fixture)
