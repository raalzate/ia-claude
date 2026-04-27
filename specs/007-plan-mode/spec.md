# Kata 07 — Exploración Segura con Plan Mode

## Concepto

Antes de modificar un repositorio desconocido, el agente entra en **Plan Mode**:
modo sólo-lectura. Explora, escribe un documento markdown con hallazgos y
arquitectura propuesta, y obtiene aprobación humana **antes** de transicionar a
ejecución directa (escritura).

## Por qué importa

Una refactorización masiva sin reconocimiento previo es destrucción
probabilística. Plan Mode separa "entender" de "modificar"; el humano firma el
plan, no cada edición.

## Modelo mental

- Dos modos: read-only (Plan) y write (Direct). La transición es explícita y
  registrada.
- En Plan Mode, las herramientas de escritura están deshabilitadas, no sólo
  desaconsejadas.
- El artefacto de aprobación es texto auditable, no un "ok" verbal.
- Aprobación = firma + plan congelado; cambios al plan re-piden aprobación.

## Ejemplo mínimo

```
1. /plan        # entra en read-only
2. agente lee, busca, mapea, redacta plan.md
3. humano revisa plan.md → "approve"
4. agente sale de Plan Mode → ejecuta sólo lo que el plan describe
```

Si el agente intenta escribir en Plan Mode, el hook `PreToolUse` lo deniega.

## Anti-patrón

Lanzar el agente con permisos de escritura en un repo desconocido y "ver qué
pasa". El primer error borra archivos clave o reescribe convenciones; recuperar
es caro.

## Argumento de certificación

- Sé describir qué herramientas están permitidas en cada modo.
- Sé justificar por qué la aprobación humana es sobre el plan, no sobre cada
  edición.
- Sé conectar Plan Mode con Kata 2 (los hooks aplican el modo) y Kata 16
  (escalación cuando el plan se invalida).

## Auto-evaluación

1. ¿Qué pasa si durante la ejecución el agente descubre que el plan era
   incorrecto?
2. ¿Cómo aseguro que Plan Mode bloquea TODA escritura, no sólo las "obvias"?
3. ¿Dónde se almacena la aprobación humana para que la auditoría la encuentre?
