# Kata 04 — Aislamiento Estricto de Subagentes (Hub-and-Spoke)

## Concepto

Un coordinador descompone una tarea grande y lanza subagentes. Cada subagente
recibe **sólo** el prompt mínimo que necesita y devuelve **sólo** un JSON
tipado. Cero memoria compartida, cero historial heredado.

## Por qué importa

Heredar el historial completo del coordinador parece "ayudar al subagente a
entender el contexto". En la práctica diluye su atención, filtra políticas
sensibles, y hace los fallos imposibles de bisecar (¿de qué turno ancestral
viene este sesgo?).

## Modelo mental

- Coordinador = hub. Subagentes = spokes. No hay aristas spoke↔spoke.
- Contrato de entrada del subagente: prompt + payload tipado, nada más.
- Contrato de salida: schema JSON. Si no encaja, error de boundary, no "casi".
- El coordinador es el único que agrega resultados.

## Ejemplo mínimo

```python
def coordinator(task):
    chunks = split(task)
    results = [run_subagent(prompt=focused_prompt(c), schema=ChunkResult)
               for c in chunks]
    return aggregate(results)            # JSONs tipados, no prosa
```

`run_subagent` arranca sesión nueva, sin pasar `coordinator.history`.

## Anti-patrón

"Telepatía compartida": pasar todo el historial del coordinador al subagente
"por si acaso". Resultado: contexto diluido, atención degradada, política
filtrada a un agente que no tenía por qué verla.

## Argumento de certificación

- Sé dibujar el diagrama hub-and-spoke y explicar por qué no hay aristas
  laterales.
- Sé enumerar qué se pasa al subagente y qué no.
- Sé argumentar por qué la salida tipada es preferible a "resúmen en prosa".

## Auto-evaluación

1. ¿Cómo demuestro que el subagente NO recibió historial del coordinador?
2. ¿Qué hago si dos subagentes producen JSONs en conflicto?
3. ¿Cuándo está justificado romper el aislamiento? (pista: casi nunca)
