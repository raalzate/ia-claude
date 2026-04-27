# Kata 28 — Propagación de Errores Multi-Agente

## Concepto

En sistemas hub-and-spoke, los errores deben propagarse al coordinador
con **contexto estructurado**: `failure_type`, `attempted_query`,
`partial_results`, `suggested_alternatives`. El coordinador decide si
reintenta con otra query, sigue con resultados parciales, o aborta.

Cuatro reglas:

1. **Local recovery primero** — el subagente reintenta transients
   localmente; sólo propaga lo que no resuelve.
2. **Distinguir** access failure (timeout, permisos) de **valid empty
   result** (búsqueda exitosa, cero matches).
3. **Coverage gap annotation** en el output del synthesis.
4. **Nunca enmascarar** un error como success vacío.

## Por qué importa

Devolver `{"results": []}` cuando un timeout impidió la búsqueda hace
que el coordinador asuma "no había información" — y produzca un report
confiado con un hueco silencioso. Generic `"search unavailable"` priva
al coordinador del contexto para decidir alternativas.

## Modelo mental

| Subagente devuelve…                            | Coordinador hace…                  |
|------------------------------------------------|------------------------------------|
| `{success: true, results: [...]}`              | Procesa normalmente                |
| `{success: true, results: [], empty_valid: true}` | Marca topic como "sin matches"  |
| `{failure_type: "timeout", attempted_query, partial_results, alternatives}` | Reintenta con alternative o sigue |
| `{failure_type: "permission", retryable: false}` | Aborta o escala                |

## Ejemplo mínimo

```python
def web_search_subagent(query):
    try:
        results = http_search(query, timeout=10)
        if not results:
            return {"success": True, "results": [], "empty_valid": True, "query": query}
        return {"success": True, "results": results, "query": query}
    except TimeoutError:
        # Local recovery
        try:
            results = http_search(broaden(query), timeout=20)
            return {"success": True, "results": results, "query": broaden(query),
                    "note": "broadened after timeout"}
        except TimeoutError:
            return {
                "success": False,
                "failure_type": "timeout",
                "attempted_query": query,
                "partial_results": [],
                "suggested_alternatives": [broaden(query), simpler(query)],
            }
    except PermissionError as e:
        return {
            "success": False, "failure_type": "permission",
            "retryable": False, "explanation": str(e),
        }

def coordinator(topic):
    res = web_search_subagent(topic)
    if not res["success"] and res["failure_type"] == "timeout":
        # Reintenta con suggested_alternatives
        for alt in res["suggested_alternatives"]:
            r2 = web_search_subagent(alt)
            if r2["success"]: return r2
    return res
```

## Anti-patrón

- Retornar `{"results": []}` en error de acceso (success vacío
  enmascarado).
- Generic `"search unavailable"` sin failure_type ni partial.
- Terminar el workflow al primer error de un subagente.
- Reintentar en el coordinador sin que el subagente intente local
  recovery.

## Argumento de certificación

- Sé distinguir access failure de valid empty.
- Sé enunciar local recovery + structured propagation.
- Sé conectar con Kata 06 (estructura del error) y Kata 20 (coverage
  gap reporting).

## Auto-evaluación

1. ¿Cómo distingue el coordinador "no había info" vs "no pudimos buscar"?
2. ¿Quién intenta el primer retry: el subagente o el coordinador?
3. ¿Qué información mínima necesita el coordinador para decidir
   alternative recovery?
