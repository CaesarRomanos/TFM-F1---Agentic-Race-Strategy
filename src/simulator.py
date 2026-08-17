"""
simulator.py
============
El motor central. Mismo motor, dos modos (clave metodológica del TFM):

  - MODO BACKTEST  : simula una estrategia concreta de forma determinista.
  - MODO MONTECARLO: (futuro Race Simulation Agent) samplea ruido sobre las
                     predicciones para devolver una distribución de resultados.

Esta primera versión implementa el modo determinista, que es lo que necesita
el replay (sanity check) y la búsqueda exhaustiva del óptimo.
"""

from __future__ import annotations

from dataclasses import dataclass
import numpy as np

from race_state import Strategy, CircuitModel
from tyre_model import TyreModel


@dataclass
class SimResult:
    """Resultado de simular una estrategia."""
    total_time: float            # tiempo total de carrera (s), sin distorsión SC
    lap_times: np.ndarray        # tiempo de cada vuelta (s)
    n_stops: int

    @property
    def total_with_pits(self) -> float:
        return self.total_time


class RaceSimulator:
    """
    Simula una carrera completa dada una estrategia.

    Convención de edad: la primera vuelta de un stint con neumático nuevo tiene
    age = 1 (igual que TyreLife en FastF1), para ser coherente con el ajuste.
    """

    def __init__(self, tyre_model: TyreModel, circuit: CircuitModel):
        self.model = tyre_model
        self.circuit = circuit

    def simulate(self, strategy: Strategy) -> SimResult:
        stints = strategy.to_stints(self.circuit.total_laps)
        lap_times = np.empty(self.circuit.total_laps, dtype=float)

        for stint in stints:
            for offset, lap in enumerate(range(stint.start_lap, stint.end_lap + 1)):
                age = offset + 1                      # 1 en la primera vuelta del stint
                lap_times[lap - 1] = self.model.predict(stint.compound, age, lap)

        total = float(lap_times.sum()) + strategy.n_stops * self.circuit.pit_loss
        return SimResult(total_time=total, lap_times=lap_times,
                         n_stops=strategy.n_stops)

    def predicted_lap_time(self, compound, age: int, lap: int) -> float:
        """Acceso directo al modelo, útil para superponer curvas en los plots."""
        return self.model.predict(compound, age, lap)
