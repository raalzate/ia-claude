# Kata 12 — Prompt Chaining Multi-Pass

## Concepto

Cuando una tarea no cabe cognitivamente (auditar 50 archivos, resumir 200
páginas), se descompone en **pases secuenciales**: pase local por unidad
(archivo, página) y luego pase de integración que sólo ve los resúmenes.

## Por qué importa

Pedirle al modelo "audita estos 50 archivos" en un solo prompt satura su
atención: se pierde detalles, alucina entre archivos, y produce un resumen
genérico. Encadenar prompts mantiene cada pase enfocado y barato.

## Modelo mental

- Pase 1 (paralelo): por unidad, salida tipada y compacta.
- Pase 2 (integración): sólo ve los outputs del pase 1, no las unidades crudas.
- Cada pase tiene un schema de salida; el siguiente pase consume esos schemas.
- El modelo nunca ve la totalidad cruda.

## Ejemplo mínimo

```python
# Pase 1 (por archivo)
local = [analyze_file(f, schema=FileFindings) for f in files]

# Pase 2 (integración)
report = integrate(local, schema=AuditReport)
```

`local[i]` ya está condensado: el pase 2 cabe holgadamente.

## Anti-patrón

Concatenar todos los archivos en un solo prompt y pedir el reporte final.
Resultado: respuesta superficial, alucinaciones cruzadas entre archivos, costo
máximo, calidad mínima.

## Argumento de certificación

- Sé identificar tareas candidatas para chaining vs single-pass.
- Sé diseñar schemas de transición entre pases.
- Sé conectar este kata con Kata 4 (subagentes para paralelizar el pase 1) y
  Kata 11 (cada pase respeta el límite de contexto).

## Auto-evaluación

1. ¿Cuándo NO conviene chaining (overhead > beneficio)?
2. ¿Qué pasa si un pase 1 falla en una unidad? ¿se aborta, se omite, se
   reintenta?
3. ¿Cómo evito que el pase 2 "rellene" lo que el pase 1 dejó vacío?
