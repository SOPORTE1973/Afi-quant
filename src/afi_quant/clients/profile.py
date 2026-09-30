"""
Perfil de cliente y metas (Motor de Cliente/Goal).

Un cliente se modela por sus METAS: cada una tiene un monto objetivo, una
fecha (o ninguna, si es una reserva permanente) y una prioridad. El
horizonte de riesgo de cada meta sale de los meses que faltan para su
fecha, con los cortes del Parameter Registry — no de una etiqueta fija:
a medida que la fecha se acerca, la meta cambia de horizonte y su cartera
se reconstruye (glide path).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

SHORT, MEDIUM, LONG = "corto", "medio", "largo"


def months_between(a: date, b: date) -> int:
    return (b.year - a.year) * 12 + (b.month - a.month)


@dataclass(frozen=True)
class Goal:
    key: str
    nombre: str
    prioridad: str               # "esencial" | "importante" | "aspiracional"
    monto_objetivo: float        # CLP nominales
    fecha: date | None           # None = reserva permanente (liquidez inmediata)
    capital_inicial: float       # CLP asignados a la meta al onboarding
    aporte_mensual: float        # CLP que el cliente aporta cada mes a esta meta

    def horizon(self, as_of: date, short_max_months: int, medium_max_months: int) -> str:
        if self.fecha is None:
            return SHORT
        months = months_between(as_of, self.fecha)
        if months <= short_max_months:
            return SHORT
        if months <= medium_max_months:
            return MEDIUM
        return LONG


@dataclass
class ClientProfile:
    client_id: str
    nombre: str
    fecha_nacimiento: date
    perfil_riesgo: str
    puntaje_cuestionario: int
    gasto_mensual: float
    goals: list[Goal] = field(default_factory=list)
    sintetico: bool = True
    nota: str = ""

    def age(self, as_of: date) -> int:
        years = as_of.year - self.fecha_nacimiento.year
        if (as_of.month, as_of.day) < (self.fecha_nacimiento.month, self.fecha_nacimiento.day):
            years -= 1
        return years

    def goal(self, key: str) -> Goal:
        return next(g for g in self.goals if g.key == key)
