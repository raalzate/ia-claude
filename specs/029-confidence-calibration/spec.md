# Kata 29 — Confidence Calibration y Stratified Sampling

## Concepto

Para extracciones masivas (auditorías, batch processing), el modelo emite
**field-level confidence scores** junto con cada valor. Esos scores se
**calibran** contra un **labeled validation set**: la confianza
self-reported sin calibrar está sesgada (suele ser sobreestimada).

Calibrado, los scores enrutan trabajo:

- **High confidence** → automatización + **stratified random sampling**
  para detectar patrones nuevos de error.
- **Low confidence** → revisión humana.

Y **siempre** medir accuracy por `document_type` y `field`, no agregada
— el 97 % global puede ocultar 60 % en un segmento.

## Por qué importa

Reportar "97 % accuracy global" y automatizar todo lo high-confidence
suena seguro hasta que un tipo específico de doc falla en silencio.
Stratified sampling sobre high-confidence es la red que detecta los
nuevos modos de error que validation set viejo no captura.

## Modelo mental

- Confidence raw del modelo ≠ probabilidad real de correctitud.
- Calibración: comparar score vs accuracy en validation set
  etiquetado por categorías de score.
- Stratified sampling: muestreo proporcional por document_type y por
  rango de score.
- Reportar accuracy desglosada; un agregado mente.

## Ejemplo mínimo

```python
EXTRACT_WITH_CONF = {
    "name": "extract_with_confidence",
    "input_schema": {
        "type": "object",
        "properties": {
            "value": {"type": ["string", "null"]},
            "field_confidence": {"type": "number", "minimum": 0, "maximum": 1},
        },
        "required": ["value", "field_confidence"],
    },
}

def calibrate(predictions, labeled_set):
    \"\"\"Devuelve mapping confidence_bucket -> empirical_accuracy.\"\"\"
    buckets = {0.5: [], 0.7: [], 0.9: []}
    for pred, truth in zip(predictions, labeled_set):
        for thresh in buckets:
            if pred["field_confidence"] >= thresh:
                buckets[thresh].append(pred["value"] == truth)
    return {t: sum(b) / len(b) if b else None for t, b in buckets.items()}

def stratified_sample(extractions, n_per_type=10):
    by_type = group_by(extractions, lambda e: e["doc_type"])
    sample = []
    for doc_type, items in by_type.items():
        high_conf = [i for i in items if i["confidence"] >= 0.9]
        sample += random.sample(high_conf, min(n_per_type, len(high_conf)))
    return sample
```

## Anti-patrón

- Tomar `field_confidence` raw como probabilidad real sin calibrar.
- Reportar agregate accuracy como métrica única.
- Muestreo aleatorio simple (sin stratificar) — under-representa
  segmentos minoritarios donde el modelo puede fallar.

## Argumento de certificación

- Sé enunciar la diferencia entre confianza raw y calibrada.
- Sé describir stratified sampling y por qué supera al simple random.
- Sé identificar cuándo un agregado de accuracy es engañoso.

## Auto-evaluación

1. Mi modelo dice `confidence: 0.95` en una extracción. ¿Puedo
   automatizar?
2. ¿Cómo construyo un labeled validation set sin pagar mucho a humanos?
3. ¿Por qué 97 % global puede ocultar problemas reales?
