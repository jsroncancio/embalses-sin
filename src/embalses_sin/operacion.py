"""Monitoreo diario del nivel de los embalses con datos de XM (desde 2025).

"Nivel" = volumen útil como % de la capacidad útil, tal como lo publica XM
(XM no publica la cota en m.s.n.m.). La referencia para leerlo es la banda
NEP–NPV del mes que declara cada embalse en PARATEC: por debajo del NEP el
embalse está en reserva; por encima del NPV, cerca de verter.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from .topologia import Cadena
from .xm import leer_crudo


def mapa_series(cadenas: list[Cadena]) -> pd.DataFrame:
    """Una fila por serie de XM: nombre XM, cadena y nodos que representa."""
    filas = {}
    for c in cadenas:
        for emb in c.embalses():
            attrs = c.grafo.nodes[emb]
            fila = filas.setdefault(attrs["xm"], {"serie_xm": attrs["xm"], "cadena_id": c.id, "nodos": [], "nombres": []})
            fila["nodos"].append(emb)
            fila["nombres"].append(attrs["nombre"])
    df = pd.DataFrame(filas.values())
    df["embalse"] = df["nombres"].map(" + ".join)
    df["nodos"] = df["nodos"].map(", ".join)
    return df.drop(columns="nombres")


def _metrica(raiz: Path, metrica: str, entidad: str, col: str, factor: float) -> pd.DataFrame:
    df = leer_crudo(raiz, metrica, entidad)
    df = df.rename(columns={"Name": "serie_xm", "Date": "fecha"})
    df[col] = df["Value"] * factor
    df["fecha"] = pd.to_datetime(df["fecha"])
    return df[["serie_xm", "fecha", col]]


def serie_embalses(raiz: Path) -> pd.DataFrame:
    pct = _metrica(raiz, "PorcVoluUtilDiar", "Embalse", "pct_util", 100)
    ener = _metrica(raiz, "VoluUtilDiarEner", "Embalse", "energia_gwh", 1e-6)
    cap = _metrica(raiz, "CapaUtilDiarEner", "Embalse", "capacidad_gwh", 1e-6)
    if pct.empty:
        return pd.DataFrame()
    return pct.merge(ener, how="outer").merge(cap, how="outer").sort_values(["serie_xm", "fecha"]).reset_index(drop=True)


def serie_sistema(raiz: Path) -> pd.DataFrame:
    pct = _metrica(raiz, "PorcVoluUtilDiar", "Sistema", "pct_util", 100)
    ener = _metrica(raiz, "VoluUtilDiarEner", "Sistema", "energia_gwh", 1e-6)
    df = pct.merge(ener, how="outer").drop(columns="serie_xm").sort_values("fecha")
    df["capacidad_gwh"] = df["energia_gwh"] / (df["pct_util"] / 100)
    return df.reset_index(drop=True)


def serie_cadenas(diaria: pd.DataFrame, series: pd.DataFrame) -> pd.DataFrame:
    """% de la cadena = energía almacenada / capacidad útil, ambas sumadas en GWh."""
    d = diaria.merge(series[["serie_xm", "cadena_id"]], on="serie_xm")
    g = d.groupby(["cadena_id", "fecha"])[["energia_gwh", "capacidad_gwh"]].sum()
    g["pct_util"] = g["energia_gwh"] / g["capacidad_gwh"].replace(0, np.nan) * 100
    return g.reset_index()


def referencia_nep_npv(nep: pd.DataFrame, series: pd.DataFrame) -> pd.DataFrame:
    """NEP y NPV mensuales (en %) por serie XM, por cadena y para el SIN.

    Para un grupo de embalses se promedian ponderando por la energía útil de
    PARATEC. Los embalses sin NEP/NPV declarados (Ituango) no entran.
    """
    nodo_a_serie = series.assign(nodo_id=series["nodos"].str.split(", ")).explode("nodo_id")[["nodo_id", "serie_xm"]]
    d = nep.merge(nodo_a_serie, on="nodo_id").dropna(subset=["nep", "npv"])
    d = d.assign(w_nep=d["nep"] * d["energia_util_gwh"], w_npv=d["npv"] * d["energia_util_gwh"])

    def agrupar(por, tipo):
        g = d.groupby([*por, "mes"])[["w_nep", "w_npv", "energia_util_gwh"]].sum().reset_index()
        g["nep_pct"] = g["w_nep"] / g["energia_util_gwh"] * 100
        g["npv_pct"] = g["w_npv"] / g["energia_util_gwh"] * 100
        g["tipo"] = tipo
        g["id"] = g[por[0]] if por else "SIN"
        return g[["tipo", "id", "mes", "nep_pct", "npv_pct"]]

    return pd.concat([agrupar(["serie_xm"], "embalse"), agrupar(["cadena_id"], "cadena"), agrupar([], "sistema")], ignore_index=True)


def tablas_operacion(raiz: Path, cadenas: list[Cadena], nep: pd.DataFrame) -> dict[str, pd.DataFrame]:
    diaria = serie_embalses(raiz)
    if diaria.empty:
        return {}
    series = mapa_series(cadenas)
    info = series[["serie_xm", "cadena_id", "embalse"]]
    ultimo = diaria.sort_values("fecha").groupby("serie_xm").tail(1).merge(info, on="serie_xm", how="left")
    return {
        "xm_embalses_diario.csv": diaria.merge(info, on="serie_xm", how="left"),
        "xm_embalses_ultimo.csv": ultimo,
        "xm_cadenas_diario.csv": serie_cadenas(diaria, series),
        "xm_sistema_diario.csv": serie_sistema(raiz),
        "xm_referencia_nep_npv.csv": referencia_nep_npv(nep, series),
        "xm_series.csv": series,
        "_diaria_completa": diaria,
    }
