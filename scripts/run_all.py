"""
run_all.py  --  Backtest sobre las 5 carreras de la entrega intermedia.
=======================================================================
Corre el replay (scripts/replay.py) sobre 5 Grandes Premios elegidos por su
VARIEDAD de degradación, genera un PNG por carrera en results/ y una tabla
resumen + CSV con las métricas. Es el entregable reproducible del prototipo.

Uso:
    python scripts/run_all.py

Las 5 carreras (todas 2023, ganadas por VER => datos completos y limpios):
    Monaco        -> degradación baja, track position
    Spain         -> degradación alta
    Great Britain -> mixto
    Hungary       -> degradación alta, calor
    Italy (Monza) -> degradación baja, 1 parada
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path

# scripts/ ya está en sys.path al ejecutar este fichero, así que importamos replay.
from replay import run_replay

RACES = [
    (2023, "Monaco", "VER"),
    (2023, "Spain", "VER"),
    (2023, "Great Britain", "VER"),
    (2023, "Hungary", "VER"),
    (2023, "Italy", "VER"),
]


def main():
    results = []
    for year, gp, driver in RACES:
        try:
            results.append(run_replay(year, gp, driver, make_plot=True, verbose=True))
        except Exception as exc:                    # una carrera mala no tumba el resto
            print(f"\n[ERROR] {gp} {year} {driver}: {exc}")

    if not results:
        print("\nNinguna carrera se procesó correctamente.")
        return

    # Tabla resumen en consola.
    print("\n" + "=" * 78)
    print("RESUMEN DEL BACKTEST")
    print("=" * 78)
    header = f"{'Carrera':<20}{'Pil':<5}{'Vts':>5}{'Paradas':>9}{'RMSE':>8}{'MAE':>8}{'Sesgo':>8}"
    print(header)
    print("-" * 78)
    for r in results:
        print(f"{r['race']:<20}{r['driver']:<5}{r['n_clean']:>5}{r['n_stops']:>9}"
              f"{r['rmse']:>8.3f}{r['mae']:>8.3f}{r['bias']:>+8.3f}")
    print("-" * 78)
    mean_rmse = sum(r["rmse"] for r in results) / len(results)
    print(f"RMSE medio sobre {len(results)} carreras: {mean_rmse:.3f}s  "
          f"(objetivo < 0.3s = simulador bien calibrado)")

    # CSV para la memoria.
    out_dir = Path(__file__).resolve().parent.parent / "results"
    out_dir.mkdir(exist_ok=True)
    csv_path = out_dir / "backtest_summary.csv"
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(results[0].keys()))
        writer.writeheader()
        writer.writerows(results)
    print(f"\nCSV guardado en: {csv_path}")
    print(f"PNGs (uno por carrera) en: {out_dir}")


if __name__ == "__main__":
    main()
