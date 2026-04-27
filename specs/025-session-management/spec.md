# Kata 25 — Gestión de Sesiones (Resume y Fork)

## Concepto

Tres patrones para preservar contexto entre llamadas:

- **`--resume <name>`** — continúa una sesión nombrada. Útil cuando el
  contexto previo sigue válido.
- **`fork_session`** — crea rama paralela desde una baseline para explorar
  enfoques divergentes (e.g., dos refactorizaciones distintas).
- **Sesión nueva con summary inyectado** — preferible cuando los tool
  results previos pueden estar stale (archivos modificados, datos
  cambiados).

## Por qué importa

Resumir una sesión vieja con tool results stale lleva al modelo a
referenciar archivos que ya no son lo que cree. Fresh + summary
estructurado es **más confiable** que `--resume` cuando el mundo cambió.

## Modelo mental

- **Resume**: contexto válido, conversación continúa lógicamente.
- **Fork**: dos caminos a explorar desde una misma baseline; cero
  interferencia entre ramas.
- **Summary nuevo**: tool results envejecieron; arrancar limpio inyectando
  los hallazgos clave en el system prompt.

## Ejemplo mínimo

```bash
# Resume: misma investigación, sigue donde la dejé
claude --resume codebase-audit-2025-04

# Fork: exploro dos enfoques en paralelo
claude --fork codebase-audit-2025-04 --new-name approach-A
claude --fork codebase-audit-2025-04 --new-name approach-B

# Summary fresh: el repo cambió, no quiero stale tool results
SUMMARY=$(cat investigation-scratchpad.md)
claude -p "Continuamos la investigación. Hallazgos previos: $SUMMARY"
```

## Anti-patrón

- `--resume` después de una refactorización masiva: el modelo recuerda
  archivos como eran antes.
- Crear forks que después se mezclan asumiendo que tienen contexto
  compatible.
- Inyectar el transcript completo viejo en una sesión nueva en lugar de
  un summary tipado.

## Argumento de certificación

- Sé decidir resume vs fork vs new-with-summary en escenario.
- Sé identificar cuándo los tool results están stale.
- Sé conectar este kata con Kata 18 (scratchpad como source of summary).

## Auto-evaluación

1. Mi compañero modificó 30 archivos de la rama. ¿Resume o fresh?
2. Quiero comparar dos refactorizaciones desde la misma baseline. ¿Qué uso?
3. ¿Cuándo `--resume` falla silenciosamente y por qué?
