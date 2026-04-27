# Kata 09 — Reglas Condicionales por Ruta

## Concepto

Reglas heurísticas (estilo, lints, convenciones específicas) se cargan **sólo
cuando el agente edita archivos que coinciden con un patrón**. No siempre.

## Por qué importa

Un `CLAUDE.md` que carga 2000 líneas para todos los archivos paga el costo en
todas las sesiones, incluso cuando el agente sólo está editando un README.
Cargar reglas Python sólo al tocar `*.py` libera contexto para el resto.

## Modelo mental

- La regla declara su `glob` de activación: `src/**/*.py`, `*.tf`, etc.
- El agente carga la regla al entrar al archivo, la descarta al salir.
- Reglas grandes (heurísticas de lenguaje) → condicionales.
- Reglas universales (políticas de seguridad) → siempre cargadas.

## Ejemplo mínimo

```markdown
# CLAUDE.md (raíz)
@rules/security.md          # siempre

## When editing src/**/*.py
@rules/python-style.md
@rules/python-testing.md

## When editing infra/**/*.tf
@rules/terraform.md
```

`python-style.md` no se carga al editar `README.md` — no consume tokens.

## Anti-patrón

Un único `CLAUDE.md` enorme con todas las heurísticas mezcladas. Cuesta tokens
en cada turno, dispersa atención (ver Kata 11), y hace que cambiar una regla
afecte sesiones que nada tienen que ver.

## Argumento de certificación

- Sé clasificar qué reglas son condicionales y cuáles son universales.
- Sé estimar el ahorro de tokens al condicionar por ruta.
- Sé conectar este kata con Kata 8 (jerarquía) y Kata 10 (caché).

## Auto-evaluación

1. ¿La regla "no commits sin tests" es condicional o universal?
2. ¿Qué pasa si dos reglas condicionales se aplican al mismo archivo?
3. ¿Cómo verifico que la regla NO se cargó cuando no debía?
