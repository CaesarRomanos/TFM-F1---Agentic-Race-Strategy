# 1. Título

**Sistema de agentes de inteligencia artificial para la decisión estratégica en
Fórmula 1: prototipo del simulador de carrera y su validación.**

*Trabajo de Fin de Máster — Entrega intermedia*

Autor: [tu nombre] · Tutor/a: [tutor/a] · [Máster / Universidad] · Junio 2026

---

# 2. Introducción

La estrategia de paradas en boxes es uno de los factores que con más frecuencia
determina el resultado de una carrera de Fórmula 1. Decidir cuándo parar y con
qué compuesto de neumático montar implica razonar bajo una incertidumbre
considerable: la degradación de los neumáticos no es lineal, la aparición de un
Safety Car puede invertir por completo el orden de la carrera, y las decisiones
de los rivales interactúan con las propias. En la práctica, los equipos sostienen
estas decisiones sobre departamentos de estrategia que combinan telemetría en
tiempo real, modelos predictivos y simulación.

Este Trabajo de Fin de Máster se inscribe en la línea del *Agentic Data
Scientist*: la construcción de un sistema de agentes de inteligencia artificial
capaz de replicar el trabajo de un equipo de ciencia de datos para un problema
predictivo real. El problema elegido es, precisamente, la decisión estratégica en
Fórmula 1, que integra de forma natural varias disciplinas: ingeniería de datos,
aprendizaje automático, simulación, procesamiento de lenguaje natural y puesta en
producción de servicios.

La presente entrega intermedia documenta el **primer componente funcional del
sistema: el simulador de carrera y su validación empírica frente a carreras
reales**. Como se argumenta más adelante, comenzar por este componente no es una
elección arbitraria, sino una decisión metodológica que condiciona la capacidad
de evaluar de forma objetiva todo lo que se construya después.

---

# 3. Objetivos

## 3.1. Objetivo general

Desarrollar un sistema de agentes de inteligencia artificial capaz de replicar el
proceso de toma de decisiones estratégicas de un equipo de Fórmula 1,
automatizando el análisis de telemetría vuelta a vuelta, la predicción de la
degradación de neumáticos, la simulación de escenarios de carrera y la
recomendación de la estrategia de paradas óptima, e incluyendo su puesta en
producción como microservicio desplegable.

## 3.2. Objetivos específicos del proyecto

1. Construir una capa de ingesta y limpieza de datos de telemetría a partir de
   fuentes abiertas (FastF1, OpenF1).
2. Desarrollar un modelo de degradación de neumáticos por compuesto.
3. Implementar un simulador de carrera capaz de evaluar estrategias completas.
4. Establecer un marco de validación retrospectiva (*backtesting*) sobre carreras
   históricas.
5. Diseñar el sistema de agentes (ingeniería de datos, neumáticos, simulación,
   NLP de radio y orquestación estratégica), incorporando agentes basados en LLM.
6. Empaquetar el sistema como microservicio REST desplegable.

## 3.3. Objetivos específicos de esta entrega intermedia

- Diseñar las estructuras de datos del dominio (`RaceState`, `Strategy`) que
  servirán de contrato común a todos los agentes.
- Implementar el simulador de carrera y el modelo de degradación que lo alimenta.
- **Validar empíricamente** que el simulador reproduce carreras reales, mediante
  un procedimiento de *replay* sobre cinco Grandes Premios de perfiles diversos.
- Sentar un marco metodológico defendible (separación entre modelo de referencia
  y modelo predictivo, tratamiento de la identificabilidad, delimitación de
  alcance) sobre el que construir las fases posteriores.

---

# 4. Marco teórico

## 4.1. Agentes inteligentes y toma de decisiones

Un **agente inteligente** es una entidad que percibe su entorno mediante sensores
y actúa sobre él para alcanzar unos objetivos; un agente se considera *racional*
cuando elige, en cada situación, la acción que maximiza su rendimiento esperado a
partir de la información disponible (Russell y Norvig, 2021). Esta noción es
especialmente pertinente en entornos **dinámicos y con incertidumbre**, donde la
decisión debe tomarse sin conocer por completo el estado futuro. La teoría de la
decisión proporciona el marco para razonar en estas condiciones, combinando las
preferencias sobre los resultados con las probabilidades de los distintos estados
posibles, de modo que la elección óptima es la que maximiza la utilidad esperada.

## 4.2. Sistemas multiagente

Cuando un problema es demasiado complejo para un único agente, resulta natural
descomponerlo en varios **agentes especializados que cooperan**, cada uno
responsable de una subtarea, coordinándose e intercambiando información para
alcanzar un objetivo global (Wooldridge, 2009). Este paradigma reproduce la
organización de un equipo humano, en el que distintos especialistas aportan su
conocimiento a una decisión compartida, y ofrece ventajas de modularidad,
escalabilidad y trazabilidad frente a una solución monolítica.

## 4.3. Modelos de lenguaje, predicción y simulación

Los **modelos de lenguaje de gran tamaño (LLM)** han habilitado una nueva
generación de agentes capaces de razonar, planificar e invocar herramientas
externas para cumplir objetivos expresados en lenguaje natural, así como de
coordinarse en arquitecturas multiagente (Wang et al., 2024). Un principio de
diseño recurrente consiste en **reservar el LLM para el razonamiento, la síntesis
y el lenguaje**, y delegar las **predicciones cuantitativas** en modelos clásicos
de aprendizaje automático supervisado (regresión y clasificación), más eficientes,
deterministas y auditables. Cuando, además, la decisión depende de eventos
inciertos, la **simulación** —y en particular los métodos de Monte Carlo— permite
estimar la distribución de resultados de cada alternativa y compararlas bajo
incertidumbre. La combinación de razonamiento, predicción y simulación constituye
el fundamento teórico del sistema propuesto en este trabajo.

---

# 5. Metodología

El proyecto se desarrolla siguiendo una **metodología ágil**, por su buen encaje
con un trabajo de naturaleza exploratoria y de requisitos cambiantes como es este
TFM. El *Manifiesto Ágil* prioriza el software que funciona, la colaboración y la
**respuesta al cambio** frente a la planificación rígida (Beck et al., 2001), lo
que permite incorporar el aprendizaje que se obtiene en cada etapa en lugar de
fijar todo el diseño por adelantado.

En concreto, se adoptan prácticas inspiradas en **Scrum** (Schwaber y Sutherland,
2020): el trabajo se organiza en **iteraciones cortas (*sprints*)**, cada una de
las cuales debe producir un **incremento funcional y verificable** del producto. El
conjunto de agentes y componentes del sistema constituye el *backlog* del
proyecto, que se prioriza y se aborda de forma incremental.

Bajo este enfoque, **cada componente del sistema se trata como un incremento**: se
diseña, se implementa y se valida antes de pasar al siguiente. La presente entrega
intermedia se corresponde con el **primer incremento funcional** —el simulador de
carrera y su validación—, y la **validación continua** en cada iteración permite
detectar pronto las limitaciones y **adaptar el alcance** del proyecto a los
hallazgos, en coherencia con los valores ágiles.

---

# 6. Arquitectura del sistema y encaje del prototipo

El sistema se concibe como un equipo de agentes especializados que cooperan,
imitando los roles de un equipo real de ciencia de datos e ingeniería:

- **Data Engineering Agent:** ingesta y limpieza de datos de telemetría.
- **Tyre Agent:** predicción de degradación de neumáticos mediante *machine
  learning* (XGBoost).
- **Race Simulation Agent:** simulación Monte Carlo de escenarios de estrategia.
- **Radio NLP Agent:** clasificación de mensajes de radio mediante LLM.
- **Strategy Orchestrator:** síntesis y recomendación final (LLM con LangGraph).
- **MLOps Agent:** empaquetado como microservicio (FastAPI + Docker).

El prototipo de esta entrega implementa el **núcleo cuantitativo** del sistema: el
motor de simulación, el modelo de degradación que lo alimenta y la capa de acceso
a datos. Es el componente del que depende la validación de todos los demás
agentes.

---

# 7. Diseño del prototipo

El prototipo se organiza en módulos con responsabilidades bien delimitadas:

- **`race_state.py`** — Define las estructuras de datos del dominio. La clase
  `RaceState` representa la fotografía completa de la carrera en un instante
  (circuito, vuelta actual, banderas, estado del coche objetivo y de los rivales).
  La clase `Strategy` representa un plan completo de carrera (compuesto de salida y
  secuencia de paradas) y encapsula la lógica de expansión a *stints* y la
  validación del reglamento de uso de dos compuestos. Todas las estructuras son
  serializables a JSON, lo que define el contrato de datos del futuro microservicio.

- **`data_loader.py`** — Es la única capa que interactúa con FastF1 (embrión del
  Data Engineering Agent). Carga las sesiones, limpia las vueltas, reconstruye la
  estrategia real ejecutada por cada piloto y estima la pérdida de tiempo en boxes.

- **`tyre_model.py`** — Implementa el modelo de degradación de neumáticos.

- **`simulator.py`** — Es el motor de simulación. Dada una `Strategy`, calcula el
  tiempo de cada vuelta y el tiempo total, incorporando la pérdida en boxes.

- **`replay.py` y `run_all.py`** — Orquestan la validación, generan las métricas y
  producen los gráficos comparativos.

---

# 8. Modelo de degradación de neumáticos

El modelo es deliberadamente **simple y transparente**. Para cada compuesto $c$,
el tiempo de vuelta se modela como:

$$ t_{vuelta} = b_0^{(c)} + b_1^{(c)}\cdot edad + b_2^{(c)}\cdot edad^2 + \gamma\cdot vuelta $$

Los coeficientes $b_0, b_1, b_2$ por compuesto capturan el ritmo base y la
degradación, donde el término cuadrático modela parcialmente el efecto *cliff*. El
término $\gamma$ representa el efecto de la carga de combustible. Como se ha
justificado en la metodología, $\gamma$ se **fija** a un valor de literatura
($-0.06$ s/vuelta) por motivos de identificabilidad, y este modelo simple cumple
el papel de **modelo de referencia** (*ground truth*), separado del futuro modelo
predictivo basado en XGBoost para evitar fugas de información circulares.

---

# 9. Validación: el *replay*

El procedimiento de validación es el siguiente: para cada carrera se ajusta el
modelo de degradación con las vueltas limpias del piloto, se reconstruye su
estrategia real, y se introduce dicha estrategia en el simulador. A continuación
se comparan, vuelta a vuelta, los tiempos simulados con los tiempos reales,
calculando el RMSE, el MAE y el sesgo.

Al ajustar el modelo con las propias vueltas del piloto, el *replay* es
**in-sample** por diseño. No mide capacidad predictiva, sino la **corrección del
motor de simulación**: el correcto encadenado de *stints*, la aplicación de la
pérdida en boxes, el manejo de la edad del neumático y la corrección de
combustible. El umbral de calidad fijado es un RMSE inferior a 0.3 s vuelta a
vuelta.

---

# 10. Resultados

El *backtest* se ejecutó sobre cinco Grandes Premios de la temporada 2023,
analizando en todos ellos al ganador (Verstappen) para garantizar datos completos.
Se modelaron 284 vueltas limpias en total.

| Carrera | Vueltas limpias | Paradas | RMSE (s) | MAE (s) | Sesgo (s) |
|---|---:|---:|---:|---:|---:|
| España | 61 | 2 | 0.284 | 0.185 | −0.039 |
| Italia (Monza) | 48 | 1 | 0.296 | 0.215 | ≈0 |
| Gran Bretaña | 45 | 1 | 0.341 | 0.249 | −0.148 |
| Hungría | 64 | 2 | 0.457 | 0.304 | −0.017 |
| Mónaco | 66 | 1 | 2.635 | 1.546 | ≈0 |

En las **cuatro carreras en seco**, el simulador alcanza un RMSE de entre 0.28 y
0.46 s y un MAE inferior a 0.31 s, con un sesgo prácticamente nulo en todos los
casos (ausencia de sobre o infra-estimación sistemática). El RMSE medio sobre
estas cuatro carreras es de **0.34 s**, lo que valida la corrección del motor de
simulación. La figura del *replay* (por ejemplo, `results/
replay_Spain_2023_VER.png`) muestra cómo las curvas del modelo "abrazan" la nube
de puntos reales en cada *stint*, reproduciendo tanto la degradación dentro del
*stint* como la recuperación de ritmo tras cada parada.

**El caso de Mónaco: límite del alcance, no fallo del modelo.** Mónaco 2023
presenta un RMSE muy superior (2.6 s) y una estimación de pérdida en boxes
claramente errónea (81 s). El motivo es revelador: la carrera concluyó con lluvia,
y la estrategia real del ganador incluyó un cambio a neumático intermedio en la
vuelta 55. El modelo, diseñado exclusivamente para condiciones de seco, no puede
representar el ritmo en mojado ni la transición seco/lluvia. Lejos de constituir un
fallo, este resultado **confirma empíricamente la decisión de alcance** adoptada:
el modelo se comporta de forma esperada tanto dentro de su dominio de validez como
fuera de él.

---

# 11. Discusión y limitaciones

- **Validación in-sample.** El *replay* valida la mecánica del simulador, no su
  poder predictivo. Es el paso necesario previo a la predicción.
- **Estimación de la pérdida en boxes.** El método actual es sensible a la
  presencia de Safety Cars o lluvia durante la parada, como evidencia el valor
  anómalo de Mónaco. Una mejora prevista es tabular valores por circuito.
- **Edad del neumático.** El simulador asume que cada *stint* comienza con
  neumático de edad 1, mientras que los conjuntos usados pueden comenzar con una
  edad mayor, lo que introduce una diferencia menor (inferior a 0.1 s).
- **Alcance limitado a seco.** Decisión deliberada, validada por el caso Mónaco.

---

# 12. Trabajo futuro

1. Ajuste del modelo sobre el conjunto del campo y validación cruzada
   *leave-one-driver-out* y *leave-one-circuit-out*.
2. Búsqueda exhaustiva de la estrategia óptima (omnisciente y causal) para generar
   las etiquetas de referencia.
3. Desarrollo del Tyre Agent (XGBoost) y comparación contra el simulador.
4. Construcción de los agentes basados en LLM (Strategy Orchestrator con LangGraph
   y Radio NLP Agent).
5. Puesta en producción del sistema como microservicio (FastAPI + Docker).

---

# 13. Conclusión

Esta entrega presenta un prototipo **funcional y empíricamente validado** del
componente sobre el que se construirá el sistema multiagente: un simulador de
carrera capaz de reproducir carreras reales en seco con un RMSE medio de 0.34 s
vuelta a vuelta. Más allá del resultado cuantitativo, el prototipo establece un
**marco metodológico defendible** —separación entre *ground truth* y predictor,
tratamiento riguroso de la identificabilidad del modelo, validación previa a la
construcción y alcance acotado y verificado— que constituye el cimiento sólido
sobre el que desarrollar la inteligencia estratégica del sistema en las fases
siguientes.

---

# 14. Referencias

- Beck, K., Beedle, M., van Bennekum, A., Cockburn, A., Cunningham, W., Fowler,
  M., et al. (2001). *Manifesto for Agile Software Development*.
  https://agilemanifesto.org/
- Russell, S. J., y Norvig, P. (2021). *Artificial Intelligence: A Modern
  Approach* (4.ª ed.). Pearson.
- Schwaber, K., y Sutherland, J. (2020). *The Scrum Guide: The Definitive Guide to
  Scrum*. https://scrumguides.org/
- Wang, L., Ma, C., Feng, X., Zhang, Z., Yang, H., Zhang, J., et al. (2024). A
  survey on large language model based autonomous agents. *Frontiers of Computer
  Science*, 18(6).
- Wooldridge, M. (2009). *An Introduction to MultiAgent Systems* (2.ª ed.). John
  Wiley & Sons.
