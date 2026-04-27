# Kata 27 — Multi-Pass Review e Independent Reviewer

## Concepto

El modelo que **generó** código retiene el contexto de su propio
razonamiento; eso lo hace mal revisor de su propio output. Una **instancia
independiente** (sesión nueva, sin la cadena de generación) detecta más
issues. Para PRs grandes, **multi-pass**: per-file analysis + cross-file
integration pass.

## Por qué importa

Pedirle al mismo agente que generó código que lo revise produce reviews
superficiales o auto-justificantes. Y revisar 14 archivos en un solo
pass dispersa atención: feedback inconsistente, bugs obvios omitidos.

## Modelo mental

- **Self-review** ⊂ misma sesión. Limitada por contexto sesgado.
- **Independent reviewer** = sesión limpia que sólo ve el código
  resultante, no el razonamiento.
- **Multi-pass para PRs grandes**:
  - Pass A — per-file: profundidad local archivo por archivo.
  - Pass B — cross-file: integra los outputs de A para detectar
    interacciones.
- Ejecutar 3 pasadas independientes y "consensuar 2 de 3" suena bien
  pero **suprime issues raros legítimos**. No es solución.

## Ejemplo mínimo

```python
def review_pr(client, files: dict[str, str]):
    # Pass A: cada archivo, sesión nueva por archivo
    per_file = []
    for path, content in files.items():
        per_file.append(review_file_independent(client, path, content))

    # Pass B: integra los hallazgos sin ver código crudo
    summary = json.dumps(per_file, ensure_ascii=False)
    return client.messages.create(
        system="Detecta interacciones cross-file y duplicados de findings.",
        messages=[{"role": "user", "content": summary}],
    )

def review_file_independent(client, path, content):
    # SESIÓN NUEVA: el reviewer no vio la generación
    return client.messages.create(
        system="Eres reviewer de seguridad y estilo. Devuelve findings tipados.",
        messages=[{"role": "user", "content": f"```python\n# {path}\n{content}```"}],
    )
```

## Anti-patrón

- Generar código + pedirle al mismo agente que lo revise en el siguiente
  turno.
- Single-pass review sobre 14+ archivos.
- "Quórum 2-de-3 entre reviews" como filtro de calidad.

## Argumento de certificación

- Sé enunciar por qué self-review es subóptimo.
- Sé separar per-file pass de cross-file integration pass.
- Sé argumentar contra el "quorum de N reviews" como solución.

## Auto-evaluación

1. ¿Por qué el quorum de N reviews independientes hace daño?
2. ¿Cómo aseguro que el reviewer no tiene la cadena de razonamiento del
   generador?
3. ¿Cuándo el cross-file pass detecta algo que el per-file no?
