# A/B de coders: mismo trabajo, tres configuraciones

*En curso. Cada tanda ejecuta el mismo prompt sobre el mismo tablero, una detrás de otra.*

## Qué se compara

| tanda | coder | sampling | thinking |
|---|---|---|---|
| **A** | `qwen-coder` (Qwen3.8-27B) | temp **0.6**, top_p 0.95, top_k 20 | activado |
| **B** | `deepseek-coder` (DeepSeek-V4-Flash) | temp **0.3**, top_p 0.95 *(los actuales)* | activado |
| **C** | `qwen-coder` (Qwen3.8-27B) | temp 0.6 | **desactivado** |

El revisor es DeepSeek en las tres, así que la revisión no favorece a ninguna.

> Ninguna de las tres usa el sampling que recomienda el fabricante (Qwen: 1.0 en modo thinking;
> DeepSeek: 1.0 para uso agéntico). Es deliberado: comparamos **lo que realmente corremos**. La tanda
> con los valores recomendados queda pendiente.

### Cómo se configura cada tanda

```yaml
# A — tal cual está hoy
providers: {spark31: {extra_body: {temperature: 0.6, chat_template_kwargs: {enable_thinking: true}}}}

# B — cambiar el assignee por defecto, sin tocar perfiles
# ~/.hermes/config.yaml
kanban: {default_assignee: deepseek-coder}

# C — apagar el razonamiento de Qwen. Hacen falta las DOS cosas: si solo se apaga en la
# plantilla, Hermes sigue mandando extra_body.reasoning {enabled:true} y se contradicen.
providers:
  spark31:
    models:
      RadixArk/Qwen3.8-27B-NVFP4:
        supports_reasoning: false        # Hermes deja de mandar el bloque reasoning
    extra_body:
      chat_template_kwargs: {enable_thinking: false}
```

## Qué se mide

**Objetivo**, con `tools/arm-stats.py --title "<proyecto>"`:

- reloj de pared del proyecto y tiempo de worker sumado,
- tokens de entrada y salida, número de llamadas y tokens por llamada,
- tokens de salida por minuto — el caudal real de trabajo,
- cards completadas, reintentos y ejecuciones perdidas.

**Subjetivo**, apreciación del autor del encargo, escrita antes de ver los números de la siguiente
tanda: ¿funciona a la primera?, ¿hay que rescatarlo?, ¿el resultado se parece a lo pedido?, ¿el código
es mantenible?

**Del revisor**: defectos encontrados y veredicto de su card de revisión.

## Resultados

### Tanda A · Qwen @ 0.6, thinking activado

*Proyecto: Weather Intelligence Map. En curso — 2 de 5 cards.*

| card | estado | tiempo | entrada | salida | llamadas | tok/llamada |
|---|---|---|---|---|---|---|
| 6ff67ff6 scaffold | done | 48,5 m | 2.787.056 | 86.114 | 48 | 1.794 |
| ce2b0da3 mapa y capas | running | 265,8 m | 26.288.460 | 180.914 | 227 | 797 |
| 6251159e UI | done | 254,3 m | 13.334.119 | 84.992 | 131 | 649 |
| b0561281 QA | todo | — | — | — | — | — |
| 6a5ee17d revisión | todo | — | — | — | — | — |

```
cards 2/5 · reloj de pared 4,43 h · tiempo de worker 9,48 h
tokens entrada 42.409.635 · salida 352.020 · llamadas 406 · 867 tok/llamada · 619 tok/min
```

Incidencias: una ejecución de **135 minutos perdida** por un HTTP 400 (`Unexpected reasoning effort
none`) al intentar continuar tras chocar con el tope de salida; dos cards volvieron a la cola solas al
descubrir que dependían del scaffold (10k tokens gastados en ese descubrimiento).

**Apreciación subjetiva:** *(pendiente)*

### Tanda B · DeepSeek @ 0.3

*(pendiente)*

### Tanda C · Qwen sin thinking

*(pendiente)*

## Conclusiones

*(al cerrar las tres)*
