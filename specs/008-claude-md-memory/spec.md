# Kata 08 — Memoria Jerárquica con `CLAUDE.md`

## Concepto

`CLAUDE.md` es la memoria persistente del agente en un proyecto. Vive en tres
niveles que se cargan en cascada:

- `~/.claude/CLAUDE.md` — preferencias del usuario.
- `<repo>/CLAUDE.md` — convenciones del equipo.
- `<repo>/<subpath>/CLAUDE.md` — reglas específicas de un módulo.

Y se compone modularmente con `@path/to/file.md`.

## Por qué importa

Repetir convenciones en cada prompt cuesta tokens y diverge entre miembros del
equipo. `CLAUDE.md` centraliza una sola fuente de verdad por nivel; el agente
la carga automáticamente y la usa como contexto estable (caché-friendly,
ver Kata 10).

## Modelo mental

- Más específico gana. `repo/src/CLAUDE.md` sobreescribe `repo/CLAUDE.md`.
- Lo personal (estilo del usuario) NO va en el repo.
- Lo del equipo NO va en el home del usuario.
- `@imports` mantienen el archivo principal corto y permiten reutilización.

## Ejemplo mínimo

```markdown
# Project rules

## Style
@docs/style-guide.md

## Testing
@docs/testing.md

## Forbidden
- never run `pip install` without venv
```

Y en `~/.claude/CLAUDE.md`:

```markdown
# My preferences
- prefer ruff over black
- terse commits
```

Ambos cargan; el del proyecto domina en conflictos sobre el proyecto.

## Anti-patrón

- Meter preferencias personales en el `CLAUDE.md` del repo (contamina al equipo).
- Duplicar reglas en system prompt y CLAUDE.md (drift garantizado).
- Un `CLAUDE.md` monolítico de 2000 líneas (degrada caché y atención).

## Argumento de certificación

- Sé describir el orden de precedencia entre los tres niveles.
- Sé justificar el uso de `@imports` para modularidad y caché.
- Sé enunciar qué pertenece a cada nivel y qué no.

## Auto-evaluación

1. ¿Dónde guardo "este equipo usa pytest, no unittest"?
2. ¿Dónde guardo "yo prefiero respuestas concisas"?
3. ¿Qué ocurre si el archivo del usuario y el del proyecto se contradicen?
