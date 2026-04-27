# Kata 23 — Selección de Built-in Tools

## Concepto

Claude Code/Agent SDK provee tools built-in para operaciones de
filesystem y shell:

- **Grep**: buscar contenido (regex sobre archivos).
- **Glob**: buscar paths (patrones de nombre, `**/*.test.tsx`).
- **Read**: cargar archivo completo.
- **Edit**: modificación dirigida con anchor único.
- **Write**: sobrescribir; fallback cuando Edit no encuentra anchor.
- **Bash**: comandos shell.

Cada uno tiene un **uso primario** y un **failure mode** específico.

## Por qué importa

Usar `Read` cuando quería `Grep` carga miles de tokens innecesarios.
Usar `Edit` con un anchor no-único hace que la operación falle. Saber
qué tool aplica a qué situación es mecánica básica que el examen prueba.

## Modelo mental

| Quiero…                               | Tool         |
|---------------------------------------|--------------|
| Hallar dónde se llama `processRefund` | Grep         |
| Listar todos los `*.test.tsx`         | Glob         |
| Cargar un archivo completo            | Read         |
| Cambiar una línea específica          | Edit         |
| Reescribir todo o si Edit falla       | Write        |
| Ejecutar `npm test`                   | Bash         |

Estrategia incremental: **Grep primero** para hallar entry points →
**Read** para seguir imports → **Edit/Write** puntual. Nunca "leer todo
el repo" upfront.

## Ejemplo mínimo

```python
# Buscar dónde se llama una función
grep(pattern="processRefund\\(", glob="**/*.py")

# Cargar un archivo de los hallados
read(path="src/billing/refund.py")

# Modificación dirigida (Edit)
edit(
  path="src/billing/refund.py",
  old_text="if amount > 1000:",
  new_text="if amount > MAX_REFUND:",
)
# Si old_text no es único o no existe → Edit falla
# Fallback: Read entero + Write completo
```

## Anti-patrón

- Read sobre todos los archivos del repo "por si acaso".
- Edit con anchor genérico que matchea varias líneas.
- Bash para algo que Grep/Glob hace nativamente.

## Argumento de certificación

- Sé escoger el tool correcto en una decisión rápida.
- Sé describir el failure mode de Edit y el fallback Read+Write.
- Sé defender una estrategia incremental (Grep → Read → Edit).

## Auto-evaluación

1. ¿Qué hago cuando Edit falla por anchor no único?
2. ¿Cómo investigo un repo desconocido sin leer todos los archivos?
3. ¿Bash es la respuesta correcta para "buscar todos los TODOs"?
