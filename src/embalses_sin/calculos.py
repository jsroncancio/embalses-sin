"""Cálculos por embalse y por cadena a partir de PARATEC y la topología.

Convenciones:
- Energía en GWh, volumen en Mm³, potencia en MW.
- El factor de conversión de PARATEC es ACUMULADO: ya incluye todas las
  plantas aguas abajo (ver validacion.factor_acumulado). Por eso la energía
  útil de una cadena es la suma simple de la energía útil de sus embalses,
  sin volver a sumar factores.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .paratec import MESES
from .topologia import Cadena, disposicion


def _regimen(dias: float) -> str:
    if np.isnan(dias):
        return ""
    if dias >= 60:
        return "Multianual"
    if dias >= 10:
        return "Estacional"
    return "Semanal o diario"


def tabla_embalses(cadenas: list[Cadena], basica: pd.DataFrame, tecnica: pd.DataFrame, potencias: dict) -> pd.DataFrame:
    filas = []
    for c in cadenas:
        for nodo in c.embalses():
            attrs = c.grafo.nodes[nodo]
            plantas = c.plantas_aguas_abajo(nodo)
            p_mw = sum(potencias.get(p, 0) for p in plantas)
            filas.append(
                {
                    "cadena_id": c.id,
                    "nodo_id": nodo,
                    "embalse": attrs["nombre"],
                    "embalse_paratec": attrs["paratec"],
                    "plantas_aguas_abajo": ", ".join(c.grafo.nodes[p]["nombre"] for p in plantas),
                    "potencia_aguas_abajo_mw": p_mw,
                }
            )
    df = pd.DataFrame(filas)
    df = df.merge(basica, on="embalse_paratec", how="left").merge(tecnica, on="embalse_paratec", how="left")
    df["energia_control_gwh"] = df["vol_util_mm3"] * df["factor_gwh_mm3"]
    df["diferencia_control_pct"] = (df["energia_control_gwh"] / df["energia_util_gwh"] - 1) * 100
    df["horas_a_potencia"] = df["energia_util_gwh"] * 1000 / df["potencia_aguas_abajo_mw"].replace(0, np.nan)
    df["dias_a_potencia"] = df["horas_a_potencia"] / 24
    df["regimen"] = df["dias_a_potencia"].map(_regimen)
    return df


def tabla_nep_npv(embalses: pd.DataFrame, nep_npv: pd.DataFrame) -> pd.DataFrame:
    base = embalses[["cadena_id", "nodo_id", "embalse", "embalse_paratec", "energia_util_gwh"]]
    meses = pd.DataFrame({"mes": range(1, 13), "mes_nombre": MESES})
    df = base.merge(meses, how="cross").merge(nep_npv, on=["embalse_paratec", "mes"], how="left")
    e = df["energia_util_gwh"]
    df["energia_bajo_nep_gwh"] = df["nep"] * e
    df["banda_nep_npv_gwh"] = (df["npv"] - df["nep"]) * e
    df["energia_sobre_npv_gwh"] = (1 - df["npv"]) * e
    return df


def tabla_curvas_guia(embalses: pd.DataFrame, curvas: pd.DataFrame) -> pd.DataFrame:
    base = embalses[["cadena_id", "nodo_id", "embalse", "embalse_paratec"]]
    return base.merge(curvas, on="embalse_paratec", how="inner")


def tabla_cadenas_mensual(nep: pd.DataFrame) -> pd.DataFrame:
    agg = (
        nep.groupby(["cadena_id", "mes", "mes_nombre"])
        .agg(
            energia_bajo_nep_gwh=("energia_bajo_nep_gwh", lambda s: s.sum(min_count=1)),
            banda_nep_npv_gwh=("banda_nep_npv_gwh", lambda s: s.sum(min_count=1)),
            energia_sobre_npv_gwh=("energia_sobre_npv_gwh", lambda s: s.sum(min_count=1)),
            embalses_sin_nep=("nep", lambda s: int(s.isna().sum())),
        )
        .reset_index()
    )
    return agg


def tabla_cadenas(cadenas: list[Cadena], embalses: pd.DataFrame, mensual: pd.DataFrame, potencias: dict) -> pd.DataFrame:
    filas = []
    total_energia = embalses["energia_util_gwh"].sum()
    for c in cadenas:
        e = embalses[embalses["cadena_id"] == c.id]
        m = mensual[mensual["cadena_id"] == c.id]
        plantas_reguladas = sorted({p for emb in c.embalses() for p in c.plantas_aguas_abajo(emb)})
        p_mw = sum(potencias.get(p, 0) for p in plantas_reguladas)
        energia = e["energia_util_gwh"].sum()
        imin = m["banda_nep_npv_gwh"].idxmin()
        imax = m["banda_nep_npv_gwh"].idxmax()
        filas.append(
            {
                "cadena_id": c.id,
                "cadena": c.nombre,
                "tipo": c.tipo,
                "region": c.region,
                "rios": ", ".join(c.rios),
                "n_embalses": len(c.embalses()),
                "n_plantas": len(c.plantas()),
                "vol_util_mm3": e["vol_util_mm3"].sum(),
                "energia_util_gwh": energia,
                "pct_energia_sin": energia / total_energia * 100,
                "potencia_regulada_mw": p_mw,
                "horas_a_potencia": energia * 1000 / p_mw if p_mw else np.nan,
                "banda_min_gwh": m.loc[imin, "banda_nep_npv_gwh"],
                "mes_banda_min": m.loc[imin, "mes_nombre"],
                "banda_max_gwh": m.loc[imax, "banda_nep_npv_gwh"],
                "mes_banda_max": m.loc[imax, "mes_nombre"],
                "nep_incompleto": bool(m["embalses_sin_nep"].gt(0).any()),
                "diagrama_fuente": c.diagrama,
            }
        )
    return pd.DataFrame(filas)


def topologia_json(cadenas: list[Cadena], embalses: pd.DataFrame, potencias: dict) -> list[dict]:
    datos_emb = embalses.set_index("nodo_id")
    salida = []
    for c in cadenas:
        pos = disposicion(c)
        nodos = []
        for n, attrs in c.grafo.nodes(data=True):
            nodo = {"id": n, "nombre": attrs["nombre"], "tipo": attrs["tipo"], "capa": pos[n][0], "fila": pos[n][1]}
            if attrs.get("filo_de_agua"):
                nodo["filo_de_agua"] = True
            if attrs["tipo"] == "planta" and n in potencias:
                nodo["potencia_mw"] = potencias[n]
            if attrs["tipo"] == "embalse" and n in datos_emb.index:
                fila = datos_emb.loc[n]
                nodo["vol_util_mm3"] = round(float(fila["vol_util_mm3"]), 2)
                nodo["energia_util_gwh"] = round(float(fila["energia_util_gwh"]), 2)
                nodo["factor_gwh_mm3"] = round(float(fila["factor_gwh_mm3"]), 4)
            nodos.append(nodo)
        salida.append(
            {
                "id": c.id,
                "nombre": c.nombre,
                "tipo": c.tipo,
                "notas": c.notas,
                "nodos": nodos,
                "aristas": [{"de": a, "a": b} for a, b in c.grafo.edges],
            }
        )
    return salida
