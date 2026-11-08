"""Capacidad efectiva neta de las plantas (XM, métrica CapEfecNeta por recurso).

Cada planta de config/cadenas.yaml declara sus códigos de recurso XM en
`xm_recursos`; su potencia es la suma de la capacidad efectiva neta más reciente
de esos recursos. Si XM publica varias plantas como un recurso (p. ej. GUATRON),
la capacidad va a la primera y las demás llevan `xm_en`. Una planta sin dato de
XM conserva la potencia aproximada de config/supuestos.yaml y queda marcada.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from . import xm
from .topologia import Cadena


def tabla_capacidad(raiz: Path, cadenas: list[Cadena], supuestas: dict) -> pd.DataFrame:
    crudo = xm.leer_crudo(raiz, "CapEfecNeta", "Recurso")
    ultimo = pd.DataFrame(columns=["Name", "Value", "Date"])
    if not crudo.empty:
        ultimo = crudo.sort_values("Date").groupby("Name").tail(1)
    por_codigo = ultimo.set_index("Name")
    filas = []
    for c in cadenas:
        for n, attrs in c.grafo.nodes(data=True):
            if attrs["tipo"] != "planta":
                continue
            codigos = [str(x) for x in attrs.get("xm_recursos", [])]
            con_dato = [k for k in codigos if k in por_codigo.index]
            fila = {
                "cadena_id": c.id,
                "planta_id": n,
                "planta": attrs["nombre"],
                "recursos_xm": ", ".join(codigos),
                "incluida_en": attrs.get("xm_en", ""),
                "potencia_mw": None,
                "fecha_xm": None,
                "fuente": "",
            }
            if attrs.get("xm_en"):
                fila.update(potencia_mw=0.0, fuente="incluida en otra planta")
            elif codigos and len(con_dato) == len(codigos):
                fila.update(
                    potencia_mw=float(por_codigo.loc[con_dato, "Value"].sum()) / 1000,
                    fecha_xm=max(por_codigo.loc[con_dato, "Date"]),
                    fuente="XM",
                )
            elif n in supuestas:
                fila.update(potencia_mw=float(supuestas[n]), fuente="supuesto")
            filas.append(fila)
    return pd.DataFrame(filas)


def potencias(tabla: pd.DataFrame) -> dict[str, float]:
    t = tabla.dropna(subset=["potencia_mw"])
    return dict(zip(t["planta_id"], t["potencia_mw"], strict=True))
