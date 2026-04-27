# Kata 24 — Slash Commands Custom y Skills

## Concepto

Claude Code permite extender la sesión con dos primitivas:

- **Slash commands** (`.claude/commands/X.md`): trigger explícito con `/X`.
- **Skills** (`.claude/skills/X/SKILL.md`): pieza on-demand con frontmatter
  que controla scope y tools.

Cada uno tiene scope project (compartido por git) y user (personal).

El frontmatter de SKILL.md acepta:

- `context: fork` — la skill corre en sub-agente aislado, no contamina la
  sesión principal.
- `allowed-tools: [...]` — lista whitelist; bloquea destructive si no se
  necesitan.
- `argument-hint: "..."` — texto que se le pide al dev cuando invoca sin
  args.

## Por qué importa

Comandos en `~/.claude/commands/` no se replican al equipo cuando hacen
`git pull`. Skills sin `context: fork` contaminan la sesión principal con
output verbose. Sin `allowed-tools` una skill exploratoria puede borrar
archivos por accidente.

## Modelo mental

| Necesidad                              | Mecanismo                           |
|----------------------------------------|-------------------------------------|
| `/review` para todo el equipo          | `.claude/commands/review.md`        |
| Macro personal                         | `~/.claude/commands/X.md`           |
| Análisis verboso aislado               | Skill con `context: fork`           |
| Skill sólo lectura                     | Skill con `allowed-tools` sin Write |
| Convenciones siempre cargadas          | CLAUDE.md, no skill                 |
| Workflow on-demand                     | Skill                               |

## Ejemplo mínimo

```markdown
<!-- .claude/skills/codebase-analysis/SKILL.md -->
---
name: codebase-analysis
description: Mapea estructura de un módulo y devuelve resumen.
context: fork
allowed-tools: ["Read", "Grep", "Glob"]
argument-hint: "<dir-or-feature>"
---
# Skill body
1. Glob `**/{argument}/**/*.{py,ts,tsx}`
2. Grep imports cruzados
3. Devuelve resumen tipado
```

```markdown
<!-- .claude/commands/review.md -->
Revisa el diff actual contra la guía de estilo del equipo.
Reporta findings en formato tipado.
```

## Anti-patrón

- Skill exploratoria sin `context: fork` → contamina contexto principal
  con miles de tokens de discovery output.
- `~/.claude/commands/` para comandos del equipo → nadie más los recibe.
- Embeber convenciones siempre-aplicables en una skill on-demand →
  pertenecen a CLAUDE.md.

## Argumento de certificación

- Sé escoger entre command vs skill por trigger y por scope.
- Sé enunciar para qué sirve cada frontmatter (`context`, `allowed-tools`,
  `argument-hint`).
- Sé conectar `context: fork` con la economía de contexto (Kata 11).

## Auto-evaluación

1. Quiero un `/test-coverage` disponible cuando clonen el repo. ¿Dónde?
2. Una skill exploratoria que devuelve 5000 tokens de discovery: ¿qué
   frontmatter aplica?
3. ¿Cuándo prefiero CLAUDE.md sobre una skill?
