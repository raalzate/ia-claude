# Kata 01 — Bucle Agéntico Determinista

## Concepto

Un agente Claude no termina cuando "dice" que terminó: termina cuando la API
devuelve un `stop_reason` terminal. El bucle agéntico es un `while` controlado
por metadatos estructurados (`stop_reason`), no por el contenido del texto que
genera el modelo.

Tres ramas posibles por turno:

- `tool_use` → ejecutar la herramienta, anexar el resultado al historial, iterar.
- `end_turn` → detener el bucle, devolver respuesta final.
- cualquier otro (`max_tokens`, ausente, desconocido) → detener con motivo
  explícito; nunca seguir adivinando.

## Por qué importa

El primer error de un sistema agéntico es decidir terminación con `if "done" in
text`. El día que el modelo escribe "we are done" en mitad de una cadena de
herramientas, el agente corta antes de tiempo y el negocio paga la diferencia.
La certificación exige que el control de flujo sea **observable y reproducible**;
sólo `stop_reason` cumple eso.

## Modelo mental

- El texto del modelo es **carga útil**, no señal de control.
- El bucle es un autómata: estado = historial; transición = `stop_reason`.
- Cada iteración deja una entrada en un log estructurado (índice, señal, rama,
  herramienta, motivo de fin) suficiente para reproducir la traza sin re-ejecutar.

## Ejemplo mínimo

```python
while True:
    resp = client.messages.create(messages=history, tools=tools, ...)
    if resp.stop_reason == "tool_use":
        result = run_tool(resp.content)            # determinista
        history.append(result)
        continue
    if resp.stop_reason == "end_turn":
        return resp                                # éxito
    raise UnhandledStop(resp.stop_reason)          # nunca silencioso
```

Ningún `re.search`, ningún `"done" in text`. Sólo metadatos.

## Anti-patrón

Decidir terminación, despacho de herramientas o reintentos a partir del texto
generado (regex, `in`, `contains`). Falla silenciosamente cuando el modelo
parafrasea, idioma cambia, o el usuario inyecta la frase trampa. Es la forma
más común de "agente que casi funciona en demo y se rompe en producción".

## Argumento de certificación

- Sé explicar por qué `stop_reason` es la única fuente legítima de control.
- Sé enumerar los `stop_reason` posibles y la respuesta correcta para cada uno.
- Sé describir el log mínimo que hace una corrida auditable y reproducible.

## Auto-evaluación

1. ¿Qué ocurre si el modelo devuelve `stop_reason=max_tokens`? ¿Continúo, abortó,
   reintento?
2. Si una herramienta lanza excepción, ¿cómo lo veo en el historial sin romper
   el invariante "control por señal"?
3. ¿Qué información mínima debe registrar el log para reconstruir la traza
   completa sin volver a llamar al modelo?
