# Kata 06 — Errores Estructurados en MCP

## Concepto

Un servidor MCP que falla NO devuelve un string genérico de error. Devuelve un
payload tipado: `isError: true`, `errorCategory`, `isRetryable`, y `explanation`.
El agente decide reintento, escalada o aborto a partir de esos campos, no del
texto del error.

## Por qué importa

`"something went wrong"` obliga al modelo a adivinar qué hacer: reintenta para
siempre, abandona, o escala mal. Un error tipado convierte fallos en transiciones
deterministas del bucle agéntico (Kata 1).

## Modelo mental

- Tres ejes: ¿es error? ¿es reintentable? ¿qué categoría (auth, rate_limit,
  not_found, validation, transient)?
- El agente lee los flags, no la prosa.
- `explanation` es para el humano que audita el log, no para el modelo.
- Las políticas de retry (backoff, n máximo) se ejecutan en el cliente.

## Ejemplo mínimo

```json
{
  "isError": true,
  "errorCategory": "rate_limit",
  "isRetryable": true,
  "retryAfterSeconds": 30,
  "explanation": "API quota exceeded for tenant X"
}
```

Cliente:

```python
if result.isError and result.isRetryable:
    sleep(result.retryAfterSeconds); continue
if result.isError and result.errorCategory == "auth":
    return escalate(result)
```

## Anti-patrón

Devolver `raise Exception("failed")` o un string `"Error: ..."` y dejar que el
modelo "razone" qué hacer. El agente entrará en bucle, abandonará, o escalará
casos que sólo necesitaban backoff.

## Argumento de certificación

- Sé enumerar las categorías de error MCP típicas y la respuesta correcta para
  cada una.
- Sé justificar por qué la decisión de retry vive en el cliente, no en el
  modelo.
- Sé describir cómo este kata se apoya en Kata 1 (control por señal) y
  prepara Kata 16 (escalada humana).

## Auto-evaluación

1. ¿Cómo trato un error que llega sin `errorCategory`?
2. ¿Cuál es la diferencia entre `transient` y `rate_limit` en política de retry?
3. ¿Qué prueba reintroduce el anti-patrón (string genérico) y qué assert falla?
