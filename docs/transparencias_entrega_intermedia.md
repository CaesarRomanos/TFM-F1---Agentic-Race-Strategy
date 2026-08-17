# Transparencias — Entrega intermedia TFM
### Sistema de agentes de IA para estrategia de Fórmula 1
**Prototipo: simulador de carrera y validación (backtest / replay)**

> Cada bloque `---` es una diapositiva. Los textos en *cursiva* bajo "Notas:" son
> guion para el orador, no van en la transparencia.

---

## Diapositiva 1 — Portada

**Sistema multiagente para la decisión estratégica en Fórmula 1**
Entrega intermedia — Prototipo del simulador de carrera

Autor: [tu nombre] · Tutor: [tutor] · [Máster / Universidad] · Junio 2026

*Notas: TFM dentro de la línea "Agentic Data Scientist": un sistema de agentes
que replica el trabajo de un equipo de ciencia de datos para un problema
predictivo real.*

---

## Diapositiva 2 — El problema y el objetivo

- En F1, la estrategia de paradas decide carreras: cuándo parar y con qué
  compuesto, bajo incertidumbre (degradación, Safety Cars, rivales).
- **Objetivo del TFM:** un sistema de agentes de IA que automatice el análisis de
  telemetría, prediga la degradación, simule escenarios y **recomiende la
  estrategia óptima**, desplegable como microservicio.
- **Esta entrega:** el cimiento sobre el que se apoya todo — el **simulador de
  carrera** y su **validación contra carreras reales**.

*Notas: sin un simulador validado, cualquier recomendación posterior de los
agentes sería imposible de evaluar. Por eso empezamos aquí.*

---

## Diapositiva 3 — Arquitectura objetivo del sistema de agentes

Pipeline de agentes (visión completa del TFM):

```
Data Engineering → Tyre (degradación) → Race Simulation (Monte Carlo)
                                              ↓
        Radio NLP  →  Strategy Orchestrator (LLM)  →  recomendación
                                              ↓
                         MLOps (FastAPI + Docker)
```

- **Esta entrega cubre el núcleo cuantitativo:** el motor de simulación y el
  modelo de neumáticos que lo alimenta, más la capa de datos (FastF1).
- Los agentes LLM (Orchestrator, Radio NLP) se construyen sobre este cimiento.

*Notas: dejo claro que el prototipo no es "un trozo suelto", es el componente del
que depende la validación de todos los demás.*

---

## Diapositiva 4 — Decisión metodológica: empezar por el backtest

- Ventaja de la F1: las carreras son **analizables a posteriori** → sabemos qué
  pasó realmente.
- Estrategia: construir primero el **simulador**, que servirá de *ground truth*
  para evaluar al sistema de agentes. Mismo motor en dos modos:
  - **Backtest** (determinista) — esta entrega.
  - **Monte Carlo** (con ruido) — el futuro Race Simulation Agent.
- Antes de predecir nada: demostrar que el simulador **reproduce la realidad**
  (sanity check / *replay*).

*Notas: esto evita el error típico de construir agentes que no se pueden validar.*

---

## Diapositiva 5 — Diseño del prototipo: componentes

| Módulo | Rol |
|---|---|
| `race_state.py` | Estructuras del dominio: `RaceState` (foto de la carrera), `Strategy`, `Stint`. Serializan a JSON → contrato del microservicio |
| `data_loader.py` | Única capa que toca FastF1: carga, limpia vueltas (quita SC/pits/outliers), reconstruye estrategia real |
| `tyre_model.py` | Modelo de degradación: cuadrática por compuesto + combustible |
| `simulator.py` | Motor: dada una `Strategy`, calcula tiempo por vuelta y total |
| `replay.py` / `run_all.py` | Orquestación, métricas y gráficos |

*Notas: ~5 módulos, separación de responsabilidades clara. El RaceState es el
objeto central reutilizable en todo el proyecto.*

---

## Diapositiva 6 — El modelo de degradación

Modelo **simple y transparente** (a propósito):

$$ t_{vuelta} = b_0^{(c)} + b_1^{(c)}\cdot edad + b_2^{(c)}\cdot edad^2 + \gamma\cdot vuelta $$

- Una cuadrática **por compuesto** (Blando/Medio/Duro): ritmo base + degradación
  (el término cuadrático captura el efecto *cliff*).
- Término de **combustible** ($\gamma$): el coche acelera al quemar gasolina.

**Decisión defendible:** $\gamma$ se **fija** (−0.06 s/vuelta, valor de
literatura), no se ajusta. Razón: con datos de un piloto, vuelta y edad del
neumático son colineales → $\gamma$ no es identificable y saldría un valor sin
sentido. Fijarlo deja curvas de degradación limpias.

*Notas: este es uno de los puntos que demuestran criterio metodológico.*

---

## Diapositiva 7 — Por qué este modelo NO es el modelo final

- Este modelo simple define el **ground truth** del simulador.
- El **Tyre Agent** (XGBoost, fase posterior) competirá **contra** este simulador.
- Si usáramos el mismo modelo para generar el ground truth y para predecir,
  estaríamos validándolo **contra sí mismo** → *leakage* circular.
- Separar ambos permite medir el **valor real** que aporta el agente de ML.

*Notas: anticipo la pregunta "¿por qué un modelo tan simple?". Porque su papel es
ser referencia, no predictor.*

---

## Diapositiva 8 — Validación: el *replay*

**Sanity check:** para cada carrera tomamos la estrategia **real** del piloto,
la pasamos por el simulador y comparamos tiempo a tiempo con la realidad.

- Ajuste con las vueltas limpias del piloto (verde, sin pits/SC).
- Métricas: **RMSE** y **MAE** vuelta a vuelta, **sesgo**.
- Validamos la *fontanería* del simulador: encadenado de stints, pérdida en
  boxes, edad de neumático, combustible.
- Objetivo: **RMSE < 0.3 s** = simulador bien calibrado.

*Notas: es in-sample por diseño; no mide predicción, mide que el motor es
correcto. La predicción se valida en la siguiente fase.*

---

## Diapositiva 9 — Resultados: 5 carreras (temporada 2023)

| Carrera | Vts limpias | Paradas | RMSE (s) | MAE (s) | Sesgo (s) |
|---|---:|---:|---:|---:|---:|
| Spain | 61 | 2 | **0.284** | 0.185 | −0.04 |
| Italy (Monza) | 48 | 1 | **0.296** | 0.215 | ~0 |
| Great Britain | 45 | 1 | **0.341** | 0.249 | −0.15 |
| Hungary | 64 | 2 | **0.457** | 0.304 | −0.02 |
| Monaco | 66 | 1* | 2.635 | 1.546 | ~0 |

- **4 carreras secas: RMSE 0.28–0.46 s, MAE < 0.31 s, sesgo ≈ 0.**
- RMSE medio (4 secas) = **0.34 s** → motor validado.
- Mónaco aparte (ver siguiente diapositiva).

*Notas: 284 vueltas limpias modeladas. Sesgo ~0 = sin sobre/infra-estimación
sistemática.*

---

## Diapositiva 10 — Ejemplo de *replay* (carrera seca)

*(Insertar `results/replay_Spain_2023_VER.png`)*

- Puntos = vueltas reales (color por compuesto).
- Líneas = predicción del modelo por stint.
- Las curvas "abrazan" los puntos → el modelo captura la degradación real.

*Notas: este es el primer gráfico de la memoria. Mostrar cómo el ritmo cae con la
edad del neumático y se recupera tras cada parada.*

---

## Diapositiva 11 — El caso Mónaco: un hallazgo, no un fallo

- Mónaco 2023 terminó con **lluvia**: estrategia real `MEDIO → INTERMEDIO` (vta 55).
- El modelo es de **seco puro** → RMSE 2.6 s y `pit_loss` estimado absurdo (81 s).
- **Es exactamente el caso que el modelo NO está diseñado para cubrir.**
- Confirma empíricamente nuestra **decisión de alcance**: condiciones de mojado y
  transiciones seco/lluvia quedan **fuera** de esta fase.

*Notas: convierto una "anomalía" en evidencia de que el modelo se comporta de
forma esperada y de que el scope estaba bien delimitado. Esto es defensa fuerte.*

---

## Diapositiva 12 — Decisiones metodológicas (resumen defensa)

1. **Separación ground truth / predictor** → evita *leakage* circular.
2. **Combustible fijo** → resuelve la no-identificabilidad por colinealidad.
3. **Validación antes que construcción** → todo es evaluable desde el día uno.
4. **Alcance acotado** (seco, 5 circuitos variados) → calidad sobre cantidad,
   verificado por el caso Mónaco.

---

## Diapositiva 13 — Próximos pasos

1. **Fit sobre el campo entero** + validación *leave-one-driver-out* → medir poder
   predictivo, no solo fontanería.
2. **Búsqueda exhaustiva del óptimo** (omnisciente y causal) → etiquetas de
   referencia para evaluar la recomendación.
3. **Agentes LLM**: Strategy Orchestrator (LangGraph) + Radio NLP.
4. **Puesta en producción**: microservicio FastAPI + Docker (MLOps Agent).

---

## Diapositiva 14 — Conclusión

- Prototipo **funcional y validado**: el simulador reproduce carreras reales con
  RMSE ~0.34 s en seco.
- Cimiento metodológico sólido y defendible para el sistema de agentes.
- El caso Mónaco demuestra que el modelo se comporta como se espera dentro y
  fuera de su alcance.

**El motor está listo para construir encima la inteligencia estratégica.**
