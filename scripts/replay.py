"""
replay.py  --  PASO 4 del backtest: el sanity check del simulador.
==================================================================
Antes de hacer NADA predictivo, demostramos que el simulador reproduce una
carrera real. Para un piloto: ajustamos el modelo de neumáticos con sus vueltas
limpias, le metemos al simulador su estrategia REAL y comparamos vuelta a vuelta.

Salidas:
  1. Métricas: RMSE / MAE vuelta a vuelta, sesgo, parámetros del ajuste.
  2. Un PNG en results/: vueltas reales (puntos) vs curva del modelo (líneas),
     coloreado por compuesto. Este es el PRIMER gráfico de tu memoria.

Uso (una carrera):
    python scripts/replay.py --year 2023 --gp Monaco --driver VER

Para correr las 5 carreras de la entrega de golpe, usa scripts/run_all.py.

Nota: el ajuste usa las propias vueltas del piloto, así que es IN-SAMPLE por
diseño. No mide poder predictivo (eso vendrá con el fit sobre el campo y
validación leave-one-driver-out): aquí validamos la FONTANERÍA del simulador
(stitching de stints, pit loss, edad, combustible).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use("Agg")               # backend sin ventana, para guardar PNG
import matplotlib.pyplot as plt

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from race_state import CircuitModel, Compound          # noqa: E402
from data_loader import (load_race, get_clean_laps,     # noqa: E402
                         reconstruct_real_strategy, estimate_pit_loss)
from tyre_model import fit_tyre_model                    # noqa: E402
from simulator import RaceSimulator                      # noqa: E402

COMPOUND_COLORS = {
    Compound.SOFT: "#e10600", Compound.MEDIUM: "#f5c518", Compound.HARD: "#cfcfcf",
    Compound.INTERMEDIATE: "#43b02a", Compound.WET: "#0067ad",
}


def run_replay(year: int, gp: str, driver: str,
               make_plot: bool = True, verbose: bool = True) -> dict:
    """Ejecuta el replay de una carrera y devuelve un dict de métricas."""
    session = load_race(year, gp)
    clean = get_clean_laps(session, driver)
    if len(clean) < 8:
        raise ValueError(f"{gp} {year} {driver}: solo {len(clean)} vueltas limpias.")

    # 1) Ajuste del modelo + estrategia real + circuito.
    model = fit_tyre_model(clean)
    strategy, total_laps = reconstruct_real_strategy(session, driver)
    pit_loss = estimate_pit_loss(session, driver)
    circuit = CircuitModel(f"{gp} {year}", total_laps, pit_loss)

    # 2) Simulación de la estrategia real y comparación en las vueltas limpias.
    result = RaceSimulator(model, circuit).simulate(strategy)
    real_laps = clean["LapNumber"].to_numpy(int)
    real_times = clean["LapTimeSec"].to_numpy(float)
    sim_times = result.lap_times[real_laps - 1]          # vuelta N -> índice N-1
    resid = sim_times - real_times

    metrics = {
        "race": f"{gp} {year}", "driver": driver, "n_clean": len(clean),
        "rmse": float(np.sqrt(np.mean(resid ** 2))),
        "mae": float(np.mean(np.abs(resid))),
        "bias": float(resid.mean()),
        "fit_rmse": model.fit_rmse, "n_stops": strategy.n_stops,
        "total_laps": total_laps, "pit_loss": pit_loss, "strategy": str(strategy),
    }

    if verbose:
        print(f"\n=== Replay: {gp} {year} — {driver} ===")
        print(f"Vueltas limpias: {metrics['n_clean']} | RMSE ajuste: {model.fit_rmse:.3f}s "
              f"| combustible: {model.fuel_coeff:+.3f}s/vuelta (fijo)")
        for c, b in model.betas.items():
            print(f"  {c.value:6s} base={b[0]:7.3f} lin={b[1]:+.4f} quad={b[2]:+.5f}")
        print(f"Estrategia real: {strategy}")
        print(f"RMSE={metrics['rmse']:.3f}s  MAE={metrics['mae']:.3f}s  "
              f"sesgo={metrics['bias']:+.3f}s  (objetivo RMSE < 0.3s)")

    if make_plot:
        _plot(clean, RaceSimulator(model, circuit), total_laps, strategy,
              year, gp, driver, metrics["rmse"])
    return metrics


def _plot(clean, sim, total_laps, strategy, year, gp, driver, rmse):
    fig, ax = plt.subplots(figsize=(12, 6))

    for compound in clean["Compound"].unique():
        sub = clean[clean["Compound"] == compound]
        ax.scatter(sub["LapNumber"], sub["LapTimeSec"], s=28,
                   color=COMPOUND_COLORS.get(compound, "#888"),
                   edgecolor="black", linewidth=0.4, zorder=3,
                   label=f"Real {compound.value}")

    for stint in strategy.to_stints(total_laps):
        laps_x = list(range(stint.start_lap, stint.end_lap + 1))
        ys = [sim.predicted_lap_time(stint.compound, a, l)
              for a, l in enumerate(laps_x, start=1)]
        ax.plot(laps_x, ys, color=COMPOUND_COLORS.get(stint.compound, "#888"),
                linewidth=2.2, zorder=2)

    for stop in strategy.stops:
        ax.axvline(stop.lap + 0.5, color="gray", linestyle="--", alpha=0.5)

    ax.set_xlabel("Vuelta"); ax.set_ylabel("Tiempo de vuelta (s)")
    ax.set_title(f"Replay {gp} {year} — {driver} | modelo vs realidad (RMSE={rmse:.3f}s)")
    ax.legend(loc="upper right", fontsize=8); ax.grid(True, alpha=0.25)
    fig.tight_layout()

    out_dir = Path(__file__).resolve().parent.parent / "results"
    out_dir.mkdir(exist_ok=True)
    out_path = out_dir / f"replay_{gp}_{year}_{driver}.png"
    fig.savefig(out_path, dpi=130); plt.close(fig)
    print(f"Gráfico guardado en: {out_path}")


def main():
    p = argparse.ArgumentParser(description="Replay / sanity check del simulador F1.")
    p.add_argument("--year", type=int, default=2023)
    p.add_argument("--gp", type=str, default="Monaco")
    p.add_argument("--driver", type=str, default="VER")
    args = p.parse_args()
    run_replay(args.year, args.gp, args.driver)


if __name__ == "__main__":
    main()
