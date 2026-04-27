# Kata 30 — Criterios Explícitos para Reducir Falsos Positivos

## Concepto

Instrucciones vagas ("be conservative", "only report high-confidence
findings") fallan en producción: el modelo interpreta "conservative"
distinto cada vez. Los criterios explícitos categóricos
(con concretos ejemplos por nivel de severidad) producen clasificación
consistente.

Y un punto operativo crucial: **un alto false positive rate en una sola
categoría destruye la confianza del usuario en TODAS las categorías**.
A veces conviene **deshabilitar** temporalmente la categoría problemática
mientras se afina.

## Por qué importa

Si el reviewer agente reporta "potential security issue" en código
seguro 1 de cada 5 veces, los devs empiezan a ignorar todos los flags
de seguridad — incluyendo los reales. La precisión es prerequisito de
la utilidad.

## Modelo mental

- "Confidence" como filtro NO funciona — el modelo está mal calibrado
  (Kata 29).
- Criterios deben ser **categóricos y concretos**: "report only when
  comments claim X but the actual code does Y", no "report inconsistent
  comments".
- Por categoría, definir **severidad con ejemplos de código** del nivel.
- Si una categoría arrastra falsos positivos → quitar/disable mientras
  se mejora; mantener las categorías de alta precisión activas.

## Ejemplo mínimo

```python
# Vago — falla a producir resultados consistentes
SYSTEM_VAGUE = (
  "Eres reviewer. Reporta findings de alta confianza. "
  "Sé conservador con los flags."
)

# Explícito — criterios categóricos con ejemplos
SYSTEM_EXPLICIT = """
Eres reviewer. Reporta findings sólo si cumplen UNO de estos criterios:

- security.hardcoded_secret: literal API key en el código.
  Ejemplo positivo: `OPENAI_KEY = "sk-abcdef..."`
  Ejemplo negativo: `OPENAI_KEY = os.environ["OPENAI_KEY"]`
- bug.null_deref: dereferencia un value sin chequeo cuando puede ser None.
  Ejemplo positivo: `user.name` con `user = db.find_one()` (puede None).
  Ejemplo negativo: `user.name` con previo `assert user is not None`.

NO reportes:
- Estilo (espacios, naming) — fuera de scope.
- Patterns "que podrían ser problemáticos" — sólo certezas.

Severidad: error (rompe runtime), warning (degrada en edge case), info (estilo). Reporta sólo error y warning.
"""
```

## Anti-patrón

- "Be conservative" o "only report high-confidence" en el system prompt.
- Mezclar todas las categorías sin medir falsos positivos por categoría.
- Mantener una categoría que produce false positives "porque a veces
  acierta" — destruye confianza en las demás.

## Argumento de certificación

- Sé reescribir un prompt vago en explícito categórico.
- Sé argumentar por qué medir falsos positivos por categoría (no
  agregada).
- Sé proponer disable temporal como estrategia de calibración.

## Auto-evaluación

1. "Be conservative" — ¿por qué falla y qué lo reemplaza?
2. Mi reviewer reporta security findings con 35 % FP rate y bug findings
   con 5 %. ¿Qué hago primero?
3. ¿Por qué severity-with-examples supera a "use your judgment"?
