# Kata 16 — Protocolo de Handoff a Humano

## Concepto

Cuando el agente toca una política que no puede resolver (límite operativo
excedido, decisión irreversible, conflicto de datos), invoca la herramienta
`escalate_to_human`, **suspende generación de prosa** y emite un payload JSON
estricto: `customer_id`, `issue_summary`, `actions_taken`, `escalation_reason`.

## Por qué importa

Pasar al humano un transcript crudo de la conversación es desastre operacional:
el operador tiene que leer todo, adivinar contexto, y decidir bajo presión. Un
payload tipado le da un paquete autocontenido y accionable.

## Modelo mental

- Detectar precondición → llamar tool `escalate_to_human`.
- El tool corta la generación de texto y obliga a salida tipada.
- El payload es **autocontenido**: el humano no debería tener que leer nada
  más.
- Es un end-state del bucle, no una pausa: el agente no continúa hasta que el
  humano decide.

## Ejemplo mínimo

```json
{
  "customer_id": "C-1287",
  "issue_summary": "Refund $1500 requested, exceeds tier-2 limit ($1000)",
  "actions_taken": ["validated_identity", "fetched_order_history"],
  "escalation_reason": "policy_limit_refund",
  "recommended_action": "human_approval_for_full_refund"
}
```

## Anti-patrón

- Dejar que el modelo "negocie" en prosa con el cliente cuando ya superó la
  política.
- Pasar al humano `messages[]` crudo y que se las arregle.
- Resumen libre sin schema; el humano interpreta como puede.

## Argumento de certificación

- Sé enumerar precondiciones de escalada típicas.
- Sé describir por qué la salida del handoff es tipada y autocontenida.
- Sé conectar este kata con Kata 2 (hook puede forzar `ask_human`) y Kata 15
  (mismatch numérico → handoff).

## Auto-evaluación

1. ¿Qué hago si el modelo intenta seguir generando prosa después del tool call?
2. ¿Cómo aseguro que `actions_taken` refleja realmente lo ejecutado y no
   alucinación?
3. ¿Cuándo es legítimo no escalar y simplemente abortar?
