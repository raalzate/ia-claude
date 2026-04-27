# Kata 02 — Guardarraíles Deterministas con `PreToolUse`

## Concepto

Un hook `PreToolUse` se ejecuta **antes** de que la herramienta corra. Puede
permitir, denegar o pedir aprobación humana basándose en el payload exacto del
`tool_use`. La política se aplica en código, no en el prompt.

## Por qué importa

Pedirle al modelo "no borres datos de producción" en el system prompt es una
sugerencia, no un control. Un `PreToolUse` que rechaza `DROP TABLE` o
`rm -rf /` es un control verificable. La diferencia define si el sistema es
auditable o sólo "casi seguro".

## Modelo mental

- El prompt **sugiere**; el hook **aplica**.
- Veredictos tipados: `allow | deny | ask_human`, siempre con razón.
- La política vive en archivo (JSON/YAML) recargable en caliente. El modelo no
  la ve para que no pueda persuadirla.
- Cada veredicto produce evento estructurado: herramienta, args, decisión, regla.

## Ejemplo mínimo

```python
def pretool_hook(tool_name, tool_input) -> Verdict:
    if tool_name == "shell" and re.search(r"\brm -rf\b", tool_input["cmd"]):
        return Verdict("deny", reason="POL-DELETE-001")
    if tool_name == "refund" and tool_input["amount"] > 1000:
        return Verdict("ask_human", reason="POL-REFUND-LIMIT")
    return Verdict("allow")
```

Si el hook deniega, el modelo recibe un `tool_result` con error tipado y puede
replanificar. La acción peligrosa nunca se ejecuta.

## Anti-patrón

"Defensa en prompt": párrafos en el system prompt rogando al modelo no hacer X.
Funciona el 95 % del tiempo y falla justo cuando importa: jailbreak, prompt
injection en datos del usuario, comportamiento emergente de un tool nuevo.

## Argumento de certificación

- Sé distinguir control suave (prompt) de control duro (hook).
- Sé describir los tres veredictos y cuándo emitir cada uno.
- Sé justificar por qué la política vive fuera del prompt y se recarga en caliente.

## Auto-evaluación

1. Si la política cambia mientras hay sesión activa, ¿cómo aseguro que el hook
   use la versión nueva sin reiniciar el agente?
2. ¿Cómo distingo "denegar y dejar continuar" de "denegar y escalar"?
3. ¿Qué prueba reintroduce el anti-patrón a propósito para verificar que el
   hook lo bloquea?
