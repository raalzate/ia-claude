# Kata 17 — Procesamiento Masivo con Message Batches API

## Concepto

Para cargas que **no son interactivas** (auditorías, backfills, evaluaciones),
la Message Batches API procesa miles de requests offline a ~50 % del costo. Cada
request lleva un `custom_id` que correlaciona request↔response y aísla fallos.

## Por qué importa

Pagar tarifa real-time por trabajo offline es desperdicio. Y procesar 10 000
prompts uno por uno con un `for` rompe rate limits, no maneja fallos parciales,
y tarda horas. Batch es el patrón correcto.

## Modelo mental

- Batch = colección de requests independientes con `custom_id` único.
- El batch puede acabar `ended` con éxitos parciales: cada request tiene su
  propio status.
- Se procesa en background, se polea, se descarga el resultado.
- Para fallos masivos, fragmentar el batch (sub-batches) y reintentar
  selectivamente.

## Ejemplo mínimo

```python
batch = client.messages.batches.create(requests=[
    {"custom_id": f"audit-{i}", "params": {...}}
    for i, _ in enumerate(items)
])
# poll
while batch.processing_status != "ended":
    sleep(30); batch = client.messages.batches.retrieve(batch.id)
# correlate
for r in client.messages.batches.results(batch.id):
    save(r.custom_id, r.result)
```

## Anti-patrón

- Bucle síncrono `for item in 10_000: client.messages.create(...)`: tarifa
  full, rate limit, sin recuperación de fallos.
- Batch sin `custom_id` o con `custom_id` no único: pierdes correlación.
- Re-procesar todo el batch cuando sólo el 1 % falló.

## Argumento de certificación

- Sé identificar cargas elegibles para Batch (offline, latency-tolerant).
- Sé describir el ciclo create → poll → results.
- Sé justificar la importancia del `custom_id` y la fragmentación selectiva.

## Auto-evaluación

1. ¿Cuál es el ahorro económico esperado vs API real-time?
2. ¿Cómo recupero un batch interrumpido sin re-pagar el 99 % exitoso?
3. ¿Qué hago si dos requests del batch tienen el mismo `custom_id` por error?
