"""
data_loader.py
==============
Capa fina sobre FastF1. (Embrión del futuro Data Engineering Agent.)

Aquí SOLO cargamos y limpiamos. Nada de modelado. La idea es que el resto del
proyecto nunca toque FastF1 directamente: pide datos limpios a estas funciones.

Limpieza mínima para el backtest:
- Convertimos LapTime (timedelta) a segundos (float).
- Nos quedamos con vueltas "verdes" (TrackStatus == '1') y "exactas"
  (IsAccurate) para no contaminar el modelo de neumáticos con vueltas bajo
  Safety Car, in/out-laps o errores de cronometraje.
"""

from __future__ import annotations

from pathlib import Path
import pandas as pd
import fastf1

from race_state import Compound


# Cache local de FastF1: imprescindible. La primera carga baja datos de la API;
# las siguientes leen de disco. Sin esto, cada ejecución re-descarga todo.
_CACHE_DIR = Path(__file__).resolve().parent.parent / "cache"
_CACHE_DIR.mkdir(exist_ok=True)
fastf1.Cache.enable_cache(str(_CACHE_DIR))


def load_race(year: int, gp: str):
    """Carga una sesión de carrera. `gp` puede ser 'Spain', 'Monaco', etc."""
    session = fastf1.get_session(year, gp, "R")
    session.load(telemetry=False, weather=True, messages=True)
    return session


def get_clean_laps(session, driver: str) -> pd.DataFrame:
    """
    Vueltas verdes y exactas de un piloto, con columnas normalizadas.

    Devuelve un DataFrame con: LapNumber, LapTimeSec, Compound, TyreLife, Stint.
    Estas son las vueltas que alimentan el fit del modelo de neumáticos.
    """
    laps = session.laps.pick_drivers(driver).copy()

    # TrackStatus puede venir concatenado ('14', '46'...). '1' puro = verde.
    green = laps["TrackStatus"].astype(str) == "1"
    accurate = laps["IsAccurate"] if "IsAccurate" in laps else True
    # Fuera in/out laps (tienen PitInTime/PitOutTime no nulos en esa vuelta).
    not_pit = laps["PitInTime"].isna() & laps["PitOutTime"].isna()

    clean = laps[green & accurate & not_pit].copy()
    clean["LapTimeSec"] = clean["LapTime"].dt.total_seconds()
    clean = clean.dropna(subset=["LapTimeSec", "Compound", "TyreLife"])

    # Compuesto a nuestro enum (FastF1 ya usa 'SOFT'/'MEDIUM'/'HARD').
    clean["Compound"] = clean["Compound"].map(lambda c: Compound(c))

    cols = ["LapNumber", "LapTimeSec", "Compound", "TyreLife", "Stint"]
    return clean[cols].reset_index(drop=True)


def reconstruct_real_strategy(session, driver: str):
    """
    Reconstruye la estrategia REAL que ejecutó el piloto, a partir de sus stints.

    Devuelve (Strategy, total_laps_del_piloto). Se usa en el replay para meter
    al simulador exactamente lo que hizo el equipo y comparar con la realidad.
    """
    from race_state import Strategy, PitStop

    laps = session.laps.pick_drivers(driver).copy()
    laps = laps.dropna(subset=["Stint", "Compound"])

    # Resumen por stint: compuesto y primera/última vuelta.
    stint_info = (laps.groupby("Stint")
                       .agg(compound=("Compound", "first"),
                            first_lap=("LapNumber", "min"),
                            last_lap=("LapNumber", "max"))
                       .sort_values("first_lap")
                       .reset_index())

    start_compound = Compound(stint_info.iloc[0]["compound"])
    stops = []
    for i in range(1, len(stint_info)):
        prev_last = int(stint_info.iloc[i - 1]["last_lap"])
        new_compound = Compound(stint_info.iloc[i]["compound"])
        stops.append(PitStop(lap=prev_last, compound_fitted=new_compound))

    total_laps = int(laps["LapNumber"].max())
    return Strategy(start_compound=start_compound, stops=stops), total_laps


def estimate_pit_loss(session, driver: str, default: float = 21.0) -> float:
    """
    Estima el tiempo perdido en una parada comparando la in-lap+out-lap con el
    ritmo verde adyacente. Si no hay datos suficientes, devuelve `default`.

    Aproximación honesta y suficiente para el simulador mínimo. Para la versión
    final conviene un valor por circuito tabulado o medido con telemetría.
    """
    laps = session.laps.pick_drivers(driver).copy()
    laps["LapTimeSec"] = laps["LapTime"].dt.total_seconds()
    in_laps = laps[laps["PitInTime"].notna()]
    if in_laps.empty:
        return default

    deltas = []
    green = laps[(laps["TrackStatus"].astype(str) == "1")
                 & laps["PitInTime"].isna() & laps["PitOutTime"].isna()]
    if green.empty:
        return default
    baseline = green["LapTimeSec"].median()

    for _, row in in_laps.iterrows():
        ln = row["LapNumber"]
        out = laps[laps["LapNumber"] == ln + 1]
        if out.empty:
            continue
        in_time = row["LapTimeSec"]
        out_time = out.iloc[0]["LapTimeSec"]
        if pd.notna(in_time) and pd.notna(out_time):
            deltas.append((in_time - baseline) + (out_time - baseline))

    if not deltas:
        return default
    # Mediana para robustez frente a SC durante la parada.
    return float(pd.Series(deltas).median())
