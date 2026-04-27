# Kata 03 — Normalización con `PostToolUse`

## Concepto

Un hook `PostToolUse` corre **después** de la herramienta y **antes** de que el
resultado llegue al contexto del modelo. Limpia, traduce códigos arcanos y
proyecta el payload a un JSON mínimo y predecible.

## Por qué importa

Si la herramienta devuelve XML legacy de 5 KB con códigos `0xA7`, el modelo
gasta tokens para parsearlo cada turno y, peor, alucina cuando el formato cambia.
Normalizar una vez, en un sitio determinista, ahorra contexto y elimina
ambigüedad.

## Modelo mental

- El modelo no debería ver formatos crudos jamás. Sólo JSON canónico.
- Los códigos numéricos/legacy se mapean a strings legibles (`0xA7` → `"timeout"`).
- El hook es puro: misma entrada → mismo JSON. Probable de testear sin LLM.
- Mide en tokens: el run normalizado debe ser estrictamente más barato que el crudo.

## Ejemplo mínimo

```python
def posttool_hook(tool_name, raw) -> dict:
    if tool_name != "legacy_lookup":
        return raw
    return {
        "id": raw["@id"],
        "status": STATUS_CODE_MAP.get(raw["s"], "unknown"),
        "amount": float(raw["amt"]),
    }
```

El historial almacena el JSON limpio; el XML original se descarta del contexto.

## Anti-patrón

Inyectar el payload crudo y "que el modelo se las arregle". Cada turno re-paga
los tokens del parseo y la primera vez que el proveedor cambia el formato (o
añade un código) el agente alucina o falla en silencio.

## Argumento de certificación

- Sé describir cuándo `PostToolUse` aplica vs `PreToolUse`.
- Sé enunciar la regla "el modelo nunca ve datos crudos heterogéneos".
- Sé medir el ahorro de tokens y tasa de mala interpretación con/sin hook.

## Auto-evaluación

1. ¿Qué pasa si el hook recibe un código que no está en el mapa? ¿Falla, traduce
   a `unknown`, escala?
2. ¿Cómo pruebo el hook sin levantar el modelo?
3. ¿Qué métrica concreta demuestra que el hook redujo "carga cognitiva"?
