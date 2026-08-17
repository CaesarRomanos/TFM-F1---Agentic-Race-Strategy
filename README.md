# TFM F1 — Agentic Race Strategy (entrega intermedia: prototipo del simulador)

Paso 1 del proyecto: **el simulador mínimo de carrera y su sanity check (replay)**.
Antes de montar el sistema de agentes, validamos el motor que servirá de *ground
truth* para todo el backtest posterior.

## Estructura

```
src/
  race_state.py   # RaceState, Strategy, Stint... el objeto central del sistema
  data_loader.py  # capa fina sobre FastF1 (embrión del Data Engineering Agent)
  tyre_model.py   # modelo de neumáticos del simulador (cuadrático + combustible)
  simulator.py    # motor de simulación determinista (futuro Race Simulation Agent)
scripts/
  replay.py       # replay de UNA carrera (sanity check + gráfico)
  run_all.py      # backtest sobre las 5 carreras de la entrega + tabla y CSV
results/          # PNGs y backtest_summary.csv (se generan al ejecutar)
cache/            # cache de FastF1 (se crea solo)
```

## Qué hace cada componente

- **race_state.py** — las estructuras de datos del dominio. `RaceState` es la
  foto de la carrera en una vuelta (circuito, vuelta, banderas, tu coche y
  rivales); `Strategy` es un plan completo (compuesto de salida + paradas) y sabe
  expandirse a `Stint`s y validar el reglamento de 2 compuestos. Todo serializa a
  JSON: es el contrato del futuro microservicio.
- **data_loader.py** — lo único que toca FastF1. Carga la carrera, limpia las
  vueltas (quita Safety Car, in/out-laps y outliers), reconstruye la estrategia
  real del piloto y estima el tiempo perdido en boxes.
- **tyre_model.py** — ajusta una cuadrática de degradación por compuesto con
  corrección de combustible fija. Es el modelo SIMPLE que define el ground truth
  (no es el Tyre Agent / XGBoost final).
- **simulator.py** — dada una `Strategy`, calcula el tiempo de cada vuelta y el
  total. Mismo motor que luego correrá en modo Monte Carlo.
- **replay.py / run_all.py** — orquestan todo y producen métricas y gráficos.

## Setup (importante: Python 3.11 / 3.12)

Python 3.14 rompe con FastF1 y el stack científico. Crea un entorno con 3.11/3.12:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

## Ejecutar el backtest de las 5 carreras (lo de la entrega)

```powershell
python scripts/run_all.py
```

Genera en `results/`: un PNG por carrera (modelo vs realidad) y
`backtest_summary.csv` con RMSE/MAE por carrera. La primera ejecución descarga
datos de FastF1 (lento); las siguientes leen de `cache/`.

Una sola carrera (para iterar rápido):

```powershell
python scripts/replay.py --year 2023 --gp Monaco --driver VER
```

## Qué mirar

- **RMSE vuelta a vuelta < ~0.3 s**: simulador bien calibrado.
- **El gráfico**: las líneas del modelo deben "abrazar" los puntos reales por
  stint. Si un stint se desvía, ahí hay física no capturada (track evolution,
  efecto cliff, tráfico).

## Siguientes pasos

1. Fit sobre el campo entero + validación leave-one-driver-out (mide poder
   predictivo, no solo fontanería).
2. Búsqueda exhaustiva del óptimo omnisciente (etiqueta por carrera).
3. Óptimo causal por vuelta con modelo probabilístico de Safety Car.
4. Métricas del Strategy Orchestrator contra esas etiquetas.
```
