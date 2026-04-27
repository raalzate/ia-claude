# Kata 26 — Validación y Retry con Error Feedback

## Concepto

Cuando una extracción tipada falla validación (Pydantic / JSON Schema),
no se la acepta como está ni se la repite ciega. Se hace **retry-with-
error-feedback**: nueva llamada incluyendo el documento original, la
extracción fallida, y el error específico de validación. El modelo
auto-corrige.

Distinguir dos clases de fallo:

- **Recuperable** — error de formato/structure (fecha en `MM/DD/YYYY`
  cuando se pedía `YYYY-MM-DD`). Retry con feedback funciona.
- **No recuperable** — la información simplemente no está en la fuente.
  Retry sólo aluciinará.

## Por qué importa

Reintentar sin feedback es ruido: el modelo no sabe qué cambiar.
Aceptar la salida fallida silenciosamente rompe contratos downstream.
Reintentar cuando el dato no existe garantiza fabricación.

## Modelo mental

- Loop: extracción → validación → si error: extracción + error feedback →
  validación. Máximo 2-3 intentos.
- Cada intento añade **el error específico** del intento anterior, no
  un mensaje genérico "intenta de nuevo".
- Si tras N intentos no resuelve: marcar `needs_human_review` con la
  cadena de errores.
- Track `detected_pattern`: ¿cuál construct disparó el problema? Permite
  análisis sistemático cuando muchos extracts dismiss findings.

## Ejemplo mínimo

```python
def extract_with_retry(client, doc, schema, max_retries=2):
    last_error = None
    extraction = None
    for attempt in range(max_retries + 1):
        feedback = ""
        if last_error:
            feedback = (
                f"\n\nIntento previo falló: {last_error}\n"
                f"Output previo: {extraction}\n"
                f"Corrige sólo lo que el error señala."
            )
        resp = client.messages.create(
            tools=[schema],
            tool_choice={"type": "tool", "name": schema["name"]},
            messages=[{"role": "user", "content": doc + feedback}],
        )
        extraction = next(b.input for b in resp.content if b.type == "tool_use")
        try:
            validate(extraction, schema)
            return {"extraction": extraction, "attempts": attempt + 1}
        except ValidationError as e:
            last_error = str(e)
    return {
        "extraction": extraction,
        "validation_error": last_error,
        "needs_human_review": True,
    }
```

## Anti-patrón

- Retry con la misma prompt — el modelo no aprende qué cambiar.
- Aceptar la salida fallida.
- Reintentar indefinidamente cuando el dato no existe (alucinación
  garantizada).

## Argumento de certificación

- Sé distinguir error recuperable de no recuperable.
- Sé describir el loop con feedback específico, no genérico.
- Sé conectar con Kata 15 (auto-corrección numérica) y Kata 16 (handoff).

## Auto-evaluación

1. ¿Cuándo retry NO ayudará por más feedback que dé?
2. ¿Por qué el feedback debe ser **específico** y no "intenta de nuevo"?
3. ¿Qué pasa si tras 3 intentos sigue fallando?
