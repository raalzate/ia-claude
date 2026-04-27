# Kata 14 — Few-Shot para Calibrar Bordes

## Concepto

Cuando la tarea es subjetiva (tono, formato no estándar, juicio estético), una
descripción zero-shot deja al modelo en su default genérico. **2–4 ejemplos
input/output** desplazan su distribución hacia el formato deseado más rápido y
más barato que un párrafo de instrucciones.

## Por qué importa

Decir "responde en estilo casual chileno" no produce el resultado; mostrar 3
ejemplos de cómo se ve, sí. Few-shot es la forma más eficiente de comunicar
"ground truth" para casos sin definición rígida.

## Modelo mental

- Los ejemplos son del **mismo schema** que la salida esperada.
- Cubren los **bordes** del dominio, no el caso fácil.
- 2–4 suelen ser suficientes; >5 satura sin mejorar.
- Few-shot complementa (no reemplaza) al schema (Kata 5).

## Ejemplo mínimo

```python
prompt = """
Clasifica el ticket. Ejemplos:

ticket: "no me llega la factura desde hace 3 meses"
clase: "billing", urgencia: "high"

ticket: "tengo una sugerencia de mejora para la app"
clase: "feedback", urgencia: "low"

ticket: "no puedo entrar, me dice token expirado"
clase: "auth", urgencia: "high"

ahora clasifica:
ticket: "{user_text}"
"""
```

## Anti-patrón

- Ejemplos triviales que no representan los bordes (todos casos fáciles).
- Llenar el prompt con 20 ejemplos "por si acaso": dispersa atención (Kata 11),
  rompe caché (Kata 10), no mejora.
- Mezclar formatos entre ejemplos.

## Argumento de certificación

- Sé identificar cuándo few-shot supera a instrucciones en prosa.
- Sé diseñar ejemplos que cubran bordes, no centro.
- Sé combinar few-shot + schema (Kata 5) para tareas subjetivas con formato
  estricto.

## Auto-evaluación

1. ¿Cuándo añadir un ejemplo más empeora el resultado?
2. ¿Por qué los ejemplos van al inicio (estático) y no al final?
3. Si los ejemplos contradicen el schema, ¿quién gana?
