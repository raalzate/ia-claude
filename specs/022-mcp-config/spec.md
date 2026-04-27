# Kata 22 — Configuración de MCP Servers

## Concepto

Los servidores MCP se declaran en archivos JSON con dos scopes:

- **Project** (`.mcp.json`): compartido por el equipo vía git, define los
  servers que todo el repo necesita.
- **User** (`~/.claude.json`): personal del dev, no se versiona.

Las credenciales NUNCA se hardcodean: se inyectan con expansión de
environment variables (`${GITHUB_TOKEN}`).

## Por qué importa

Hardcodear un token en `.mcp.json` versionado equivale a publicarlo. Y
poner reglas de equipo en `~/.claude.json` deja a los nuevos devs sin
acceso. La elección de scope es la diferencia entre "funciona en todas
las laptops del equipo" y "funciona sólo en la mía".

## Modelo mental

- Project scope viaja con el repo, se descubre automáticamente al
  conectar.
- User scope es para experimentos personales que no afectan al equipo.
- Múltiples servers se descubren simultáneamente; el agente ve la unión
  de todos sus tools.
- MCP **resources** (catálogos de contenido) reducen llamadas
  exploratorias — cuando aplica, expón resources antes que tools.

## Ejemplo mínimo

```jsonc
// .mcp.json (project, versionado)
{
  "mcpServers": {
    "github": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-github"],
      "env": {"GITHUB_TOKEN": "${GITHUB_TOKEN}"}
    },
    "internal-docs": {
      "command": "node",
      "args": ["./scripts/mcp-docs.js"]
    }
  }
}
```

```jsonc
// ~/.claude.json (user, personal)
{
  "mcpServers": {
    "my-experimental-server": {"command": "python3", "args": ["./local-mcp.py"]}
  }
}
```

## Anti-patrón

- Token hardcoded en `.mcp.json` versionado.
- Servers de equipo en `~/.claude.json` (no se replica al onboarding).
- Custom MCP server para algo que un built-in resuelve (Grep para buscar
  imports en el repo).

## Argumento de certificación

- Sé distinguir cuándo project scope vs user scope.
- Sé enunciar el patrón de env-var expansion para credenciales.
- Sé argumentar cuándo usar MCP vs un built-in tool.

## Auto-evaluación

1. ¿Qué pasa si dos servers exponen un tool con el mismo nombre?
2. ¿Cómo se manejan los secrets en CI cuando `.mcp.json` se ejecuta allí?
3. ¿Cuándo prefiero un MCP **resource** sobre un MCP tool?
