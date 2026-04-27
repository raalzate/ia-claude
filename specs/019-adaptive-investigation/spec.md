# Kata 19 — Investigación Adaptativa (Descomposición Dinámica)

## Concepto

En un dominio desconocido, no se planifica al detalle de antemano: el agente
**mapea topología** primero (búsqueda por nombre y por contenido), genera un
plan priorizado, y **re-adapta** cuando un hallazgo invalida el plan vigente.
Todo dentro de un presupuesto de exploración acotado.

## Por qué importa

Un plan rígido en territorio desconocido garantiza desperdicio: el agente sigue
explorando ramas muertas porque "estaba en el plan". Adaptar dinámicamente
prioriza atención sobre lo que la realidad muestra, no lo que la hipótesis
inicial asumía.

## Modelo mental

- Fase 1: mapeo barato (glob de nombres, regex de imports/símbolos).
- Fase 2: priorización (¿qué módulos son centro? ¿cuáles huérfanos?).
- Fase 3: investigación profunda sólo sobre los priorizados.
- Si una hipótesis se rompe, **emitir nuevo plan** y volver a priorizar.
- Presupuesto: número máximo de archivos a leer / queries / minutos.

## Ejemplo mínimo

```python
topology = scan_repo(globs=["src/**/*.py"])
plan = prioritize(topology)               # heurística declarada
budget = Budget(files=50, queries=20)

while plan and budget.remaining():
    target = plan.pop()
    finding = deep_dive(target, budget)
    if finding.invalidates(plan):
        plan = re_plan(topology, finding)
```

Persistir en scratchpad (Kata 18) cada `finding` y `re_plan`.

## Anti-patrón

- Hacer plan completo al minuto 0 y seguirlo aunque la realidad lo contradiga.
- "Read all files" sin presupuesto: se acaba el contexto antes de aprender algo.
- Re-planificar en cada turno por reflejo (no converge nunca).

## Argumento de certificación

- Sé definir presupuesto de exploración y justificar el límite.
- Sé enunciar el criterio de re-planificación (qué disparara un re-plan, qué
  no).
- Sé conectar este kata con Kata 4 (subagentes para deep-dive) y Kata 18
  (scratchpad como memoria del proceso).

## Auto-evaluación

1. ¿Cómo decido si un hallazgo invalida el plan o sólo lo refina?
2. ¿Qué hago cuando se acaba el presupuesto sin conclusión clara?
3. ¿Cómo evito loops de re-planificación?
