"""
race_state.py
=============
Núcleo del proyecto: la representación canónica del estado de carrera.

Estas estructuras son el objeto central que viajará entre TODOS los agentes
(Data Engineering -> Tyre -> Race Simulation -> Orchestrator). Diséñalas bien
una vez y las reutilizas en el backtest, en el simulador y en el microservicio.

Decisiones de diseño:
- Todo es serializable a JSON sin esfuerzo (enums como str, dataclasses planas).
  Esto es lo que entra/sale del endpoint POST /strategy del MLOps Agent.
- `RaceState` describe UN instante (vuelta N). Una `Strategy` describe un PLAN
  completo de carrera. No los mezcles: el Orchestrator recibe un RaceState y
  emite/elige una Strategy.
- Separamos el coche objetivo (`target`) de los rivales (`rivals`) porque la
  decisión estratégica siempre se toma desde la perspectiva de un piloto.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Optional
import json


# ---------------------------------------------------------------------------
# Enumeraciones
# ---------------------------------------------------------------------------
class Compound(str, Enum):
    """Compuestos Pirelli. Hereda de str => serializa directo a JSON."""
    SOFT = "SOFT"
    MEDIUM = "MEDIUM"
    HARD = "HARD"
    INTERMEDIATE = "INTERMEDIATE"
    WET = "WET"

    @property
    def is_slick(self) -> bool:
        return self in (Compound.SOFT, Compound.MEDIUM, Compound.HARD)


class FlagState(str, Enum):
    """Estado de pista. Mapea (de forma simplificada) los TrackStatus de FastF1."""
    GREEN = "GREEN"
    YELLOW = "YELLOW"
    VSC = "VSC"          # Virtual Safety Car
    SC = "SC"            # Safety Car desplegado
    RED = "RED"


# ---------------------------------------------------------------------------
# Piezas de una estrategia
# ---------------------------------------------------------------------------
@dataclass
class PitStop:
    """Una parada: la vuelta en la que se entra a boxes y el compuesto montado."""
    lap: int                      # vuelta en la que el coche entra al pit lane
    compound_fitted: Compound     # compuesto que se monta para el siguiente stint


@dataclass
class Stint:
    """Un tramo entre dos paradas (o entre salida/parada o parada/meta)."""
    compound: Compound
    start_lap: int                # primera vuelta de carrera de este stint (inclusive)
    end_lap: int                  # última vuelta de este stint (inclusive)

    @property
    def length(self) -> int:
        return self.end_lap - self.start_lap + 1


@dataclass
class Strategy:
    """
    Un plan COMPLETO de carrera: compuesto de salida + secuencia de paradas.

    Ejemplo (1 parada): Strategy(SOFT, [PitStop(20, MEDIUM)])
    Ejemplo (2 paradas): Strategy(MEDIUM, [PitStop(18, MEDIUM), PitStop(40, HARD)])
    """
    start_compound: Compound
    stops: list[PitStop] = field(default_factory=list)

    @property
    def n_stops(self) -> int:
        return len(self.stops)

    @property
    def compounds_used(self) -> set[Compound]:
        return {self.start_compound, *(s.compound_fitted for s in self.stops)}

    def is_legal_dry(self) -> bool:
        """Reglamento seco: hay que usar >=2 compuestos slick distintos."""
        slicks = {c for c in self.compounds_used if c.is_slick}
        return len(slicks) >= 2

    def to_stints(self, total_laps: int) -> list[Stint]:
        """Expande el plan a la lista de stints concretos sobre `total_laps`."""
        stints: list[Stint] = []
        current = self.start_compound
        start = 1
        for stop in sorted(self.stops, key=lambda s: s.lap):
            stints.append(Stint(current, start, stop.lap))
            start = stop.lap + 1          # el nuevo stint arranca la vuelta siguiente
            current = stop.compound_fitted
        stints.append(Stint(current, start, total_laps))
        return stints

    def __repr__(self) -> str:
        seq = self.start_compound.value
        for s in sorted(self.stops, key=lambda s: s.lap):
            seq += f" -[L{s.lap}]-> {s.compound_fitted.value}"
        return f"Strategy({seq})"


# ---------------------------------------------------------------------------
# Estado puntual de carrera (instante = vuelta N)
# ---------------------------------------------------------------------------
@dataclass
class CircuitModel:
    """Parámetros fijos del circuito necesarios para simular."""
    name: str
    total_laps: int
    pit_loss: float               # segundos perdidos por una parada (delta pit lane)


@dataclass
class DriverState:
    """Estado de un coche concreto en la vuelta actual."""
    driver: str                   # código de 3 letras: 'VER', 'HAM', ...
    position: int
    compound: Compound
    tyre_age: int                 # vueltas sobre el set actual
    completed_stops: int
    gap_ahead: Optional[float] = None    # segundos al coche de delante (None si lidera)
    gap_behind: Optional[float] = None   # segundos al de detrás (None si es último)
    used_compounds: list[Compound] = field(default_factory=list)


@dataclass
class RaceState:
    """
    Fotografía completa de la carrera en la vuelta `current_lap`.

    Este es el objeto que el Strategy Orchestrator recibe como contexto y el
    que el endpoint REST acepta como input. Todo lo que un ingeniero de
    estrategia necesitaría para decidir 'parar / no parar' debe estar aquí.
    """
    circuit: CircuitModel
    current_lap: int
    flag: FlagState
    target: DriverState
    rivals: list[DriverState] = field(default_factory=list)
    air_temp: Optional[float] = None
    track_temp: Optional[float] = None

    @property
    def laps_remaining(self) -> int:
        return self.circuit.total_laps - self.current_lap

    # --- (de)serialización JSON: el contrato con el microservicio -----------
    def to_json(self, **kwargs) -> str:
        return json.dumps(asdict(self), default=str, **kwargs)

    @classmethod
    def from_dict(cls, d: dict) -> "RaceState":
        return cls(
            circuit=CircuitModel(**d["circuit"]),
            current_lap=d["current_lap"],
            flag=FlagState(d["flag"]),
            target=_driver_from_dict(d["target"]),
            rivals=[_driver_from_dict(r) for r in d.get("rivals", [])],
            air_temp=d.get("air_temp"),
            track_temp=d.get("track_temp"),
        )


def _driver_from_dict(d: dict) -> DriverState:
    """Reconstruye un DriverState desde un dict, convirtiendo los compuestos a enum."""
    return DriverState(**{**d,
                          "compound": Compound(d["compound"]),
                          "used_compounds": [Compound(c) for c in d.get("used_compounds", [])]})
