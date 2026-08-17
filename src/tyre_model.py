"""
tyre_model.py
=============
El modelo de neumáticos DEL SIMULADOR (no el Tyre Agent final).

IMPORTANTE (metodología, esto te lo preguntarán en la defensa):
Es deliberadamente un modelo SIMPLE y transparente: una cuadrática en la edad
del neumático, por compuesto, más una corrección lineal de combustible. Su único
trabajo es definir un "ground truth" creíble para el simulador. El Tyre Agent
(XGBoost) competirá CONTRA este simulador; si usaras el mismo modelo para generar
el ground truth y para predecir, validarías el modelo contra sí mismo (leakage).

Modelo:
    lap_time = b0[c] + b1[c]*age + b2[c]*age^2 + fuel_coeff*lap_number

- b0/b1/b2 por compuesto c: ritmo base + degradación (el término cuadrático
  captura parcialmente el efecto "cliff" al final de la vida del neumático).
- fuel_coeff (combustible): el coche va más rápido al quemar gasolina, luego el
  tiempo baja al avanzar la carrera. Lo FIJAMOS a un valor de literatura.

¿Por qué fijar el combustible y no ajustarlo? (punto fuerte para la defensa)
Dentro de un stint, lap_number y age son casi colineales (lap ≈ age + cte). Con
los datos de un solo piloto, cada compuesto aparece en un único stint y el
coeficiente de combustible no es identificable: sale un valor sin sentido aunque
el RMSE sea bajo. Fijarlo elimina esa ambigüedad y deja curvas de degradación
limpias. (Ajustarlo SÍ tendría sentido sobre el campo entero — trabajo futuro.)
"""

from __future__ import annotations

from dataclasses import dataclass, field
import numpy as np
import pandas as pd

from race_state import Compound

# Combustible: el coche gana ~0.3 s por cada 10 kg menos y quema ~1.6-1.8 kg/vuelta
# => ~ -0.06 s por vuelta de carrera.
DEFAULT_FUEL_COEFF = -0.06


@dataclass
class TyreModel:
    """Modelo ajustado. `predict` es lo único que consume el simulador."""
    betas: dict[Compound, np.ndarray]   # compound -> [b0, b1, b2]
    fuel_coeff: float                   # s/vuelta (efecto combustible, fijo)
    fit_rmse: float = field(default=float("nan"))

    def predict(self, compound: Compound, age: int, lap_number: int) -> float:
        """Tiempo de vuelta (s) de `compound` con `age` vueltas en la vuelta `lap_number`."""
        if compound not in self.betas:
            raise KeyError(f"Compuesto {compound} no ajustado. Disponibles: {list(self.betas)}")
        b0, b1, b2 = self.betas[compound]
        return b0 + b1 * age + b2 * age * age + self.fuel_coeff * lap_number


def fit_tyre_model(laps: pd.DataFrame,
                   fuel_coeff: float = DEFAULT_FUEL_COEFF) -> TyreModel:
    """
    Ajusta una cuadrática de degradación por compuesto.

    Espera columnas: LapTimeSec, Compound, TyreLife, LapNumber
    (las que produce data_loader.get_clean_laps).

    Pasos: (1) corrige el tiempo por combustible, (2) ajusta lap_time~age con
    np.polyfit por compuesto, (3) calcula el RMSE global del ajuste.
    """
    # 1) Corrección de combustible (fija): aísla la degradación pura.
    fuel_corrected = laps["LapTimeSec"] - fuel_coeff * laps["LapNumber"]

    betas: dict[Compound, np.ndarray] = {}
    residuals: list[np.ndarray] = []

    # 2) Una cuadrática por compuesto.
    for compound, idx in laps.groupby("Compound").groups.items():
        age = laps.loc[idx, "TyreLife"].to_numpy(float)
        y = fuel_corrected.loc[idx].to_numpy(float)

        deg = 2 if len(age) >= 3 else 1          # evita sobreajuste con pocos puntos
        coeffs = np.polyfit(age, y, deg)[::-1]   # polyfit da mayor->menor; invertimos
        b = np.zeros(3)
        b[:len(coeffs)] = coeffs                 # [b0, b1, b2]
        betas[compound] = b

        residuals.append(y - (b[0] + b[1] * age + b[2] * age * age))

    # 3) RMSE del ajuste (in-sample).
    rmse = float(np.sqrt(np.mean(np.concatenate(residuals) ** 2)))
    return TyreModel(betas=betas, fuel_coeff=fuel_coeff, fit_rmse=rmse)
