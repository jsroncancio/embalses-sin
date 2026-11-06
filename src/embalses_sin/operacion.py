"""Series diarias de operación (datos de XM) por embalse, cadena y SIN.

Unidades de salida: GWh, Mm³ y porcentaje del volumen útil (0 a 100).
El "nivel" que publica XM es el volumen útil como porcentaje de la capacidad
útil (por encima del nivel mínimo técnico); XM no publica la cota en m.s.n.m.
"""

from __future__ import annotations

import datetime as dt
from pathlib import Path

import numpy as np
import pandas as pd

from .topologia import Cadena
from .xm import leer_crudo

DIAS_RECIENTES = 400  # algo más de un año, para comparar con el mismo mes del año anterior


def mapa_series(cadenas: list[Cadena]) -> pd.DataFrame:
    """Una fila por serie de XM: nombre XM, cadena y nodos que representa."""
    filas = {}
    for c in cadenas:
        for emb in c.embalses():
            attrs = c.grafo.nodes[emb]
            xm = attrs["xm"]
            fila = filas.setdefault(xm, {"serie_xm": xm, "cadena_id": c.id, "nodos": [], "nombres": []})
            fila["nodos"].append(emb)
            fila["nombres"].append(attrs["nombre"])
    df = pd.DataFrame(filas.values())
    df["embalse"] = df["nombres"].map(lambda n: n[0] if len(n) == 1 else " + ".join(n))
    df["nodos"] = df["nodos"].map(", ".join)
    return df.drop(columns="nombres")


def serie_embalses(raiz: Path) -> pd.DataFrame:
    """Tabla diaria por embalse (nombre XM) con todas las métricas en columnas."""
    partes = {
        "pct_util_xm": ("PorcVoluUtilDiar", 100),
        "energia_gwh": ("VoluUtilDiarEner", 1e-6),
        "vol_util_mm3": ("VoluUtilDiarMasa", 1e-6),
        "capacidad_gwh": ("CapaUtilDiarEner", 1e-6),
        "vertimiento_gwh": ("VertEner", 1e-6),
    }
    tablas = []
    for col, (metrica, factor) in partes.items():
        df = leer_crudo(raiz, metrica, "Embalse")
        if df.empty:
            continue
        df = df.rename(columns={"Name": "serie_xm", "Date": "fecha"})
        df[col] = df["Value"] * factor
        tablas.append(df[["serie_xm", "fecha", col]].set_index(["serie_xm", "fecha"]))
    if not tablas:
        return pd.DataFrame()
    out = pd.concat(tablas, axis=1).reset_index()
    out["fecha"] = pd.to_datetime(out["fecha"])
    return out.sort_values(["serie_xm", "fecha"]).reset_index(drop=True)


def serie_sistema(raiz: Path) -> pd.DataFrame:
    partes = {
        "pct_util_xm": ("PorcVoluUtilDiar", 100),
        "energia_gwh": ("VoluUtilDiarEner", 1e-6),
        "capacidad_gwh": ("CapaUtilDiarEner", 1e-6),
    }
    tablas = []
    for col, (metrica, factor) in partes.items():
        df = leer_crudo(raiz, metrica, "Sistema")
        if df.empty:
            continue
        df[col] = df["Value"] * factor
        tablas.append(df.rename(columns={"Date": "fecha"}).set_index("fecha")[[col]])
    if not tablas:
        return pd.DataFrame()
    out = pd.concat(tablas, axis=1).reset_index()
    out["fecha"] = pd.to_datetime(out["fecha"])
    return out.sort_values("fecha").reset_index(drop=True)


def serie_cadenas(diaria: pd.DataFrame, series: pd.DataFrame) -> pd.DataFrame:
    """Suma por cadena. El % de la cadena = energía almacenada / capacidad útil (en GWh)."""
    d = diaria.merge(series[["serie_xm", "cadena_id"]], on="serie_xm", how="inner")
    g = d.groupby(["cadena_id", "fecha"]).agg(
        energia_gwh=("energia_gwh", "sum"),
        capacidad_gwh=("capacidad_gwh", "sum"),
        vol_util_mm3=("vol_util_mm3", "sum"),
        vertimiento_gwh=("vertimiento_gwh", "sum"),
        n_series=("serie_xm", "nunique"),
    )
    g["pct_util"] = g["energia_gwh"] / g["capacidad_gwh"].replace(0, np.nan) * 100
    return g.reset_index()


def rango_historico(df: pd.DataFrame, clave: str, valor: str, excluir_desde: pd.Timestamp) -> pd.DataFrame:
    """Percentiles por día del año (1 a 366) con los años anteriores a `excluir_desde`."""
    h = df[df["fecha"] < excluir_desde].dropna(subset=[valor]).copy()
    columnas = [clave, "dia_anio", "minimo", "p10", "p50", "p90", "maximo", "anios"]
    if h.empty:
        return pd.DataFrame(columns=columnas)
    h["dia_anio"] = h["fecha"].dt.dayofyear
    q = h.groupby([clave, "dia_anio"])[valor]
    out = pd.DataFrame(
        {
            "minimo": q.min(),
            "p10": q.quantile(0.10),
            "p50": q.quantile(0.50),
            "p90": q.quantile(0.90),
            "maximo": q.max(),
            "anios": h.groupby([clave, "dia_anio"])["fecha"].apply(lambda s: s.dt.year.nunique()),
        }
    ).reset_index()
    # Suaviza con una ventana móvil de 15 días (circular) para que la banda no sea ruidosa.
    suav = []
    for k, grupo in out.groupby(clave):
        grupo = grupo.set_index("dia_anio").reindex(range(1, 367))
        ext = pd.concat([grupo.iloc[-7:], grupo, grupo.iloc[:7]])
        cols = ["minimo", "p10", "p50", "p90", "maximo"]
        ext[cols] = ext[cols].rolling(15, center=True, min_periods=1).mean()
        grupo = ext.iloc[7:-7].copy()
        grupo[clave] = k
        suav.append(grupo.reset_index())
    return pd.concat(suav, ignore_index=True)[columnas]


def tablas_operacion(raiz: Path, cadenas: list[Cadena]) -> dict[str, pd.DataFrame]:
    diaria = serie_embalses(raiz)
    if diaria.empty:
        return {}
    series = mapa_series(cadenas)
    sistema = serie_sistema(raiz)
    cad = serie_cadenas(diaria, series)

    ultima = diaria["fecha"].max()
    corte_reciente = ultima - pd.Timedelta(days=DIAS_RECIENTES)
    # La banda histórica excluye el último año para que "hoy" se compare con el pasado.
    corte_hist = pd.Timestamp(dt.date(ultima.year, 1, 1)) if ultima.dayofyear > 60 else ultima - pd.Timedelta(days=365)

    reciente = diaria[diaria["fecha"] > corte_reciente].merge(series[["serie_xm", "cadena_id", "embalse"]], on="serie_xm", how="left")
    ultimo = (
        diaria.sort_values("fecha")
        .groupby("serie_xm")
        .tail(1)
        .merge(series[["serie_xm", "cadena_id", "embalse"]], on="serie_xm", how="left")
    )
    return {
        "xm_embalses_diario_reciente.csv": reciente,
        "xm_embalses_rango_historico.csv": rango_historico(diaria, "serie_xm", "pct_util_xm", corte_hist),
        "xm_embalses_ultimo.csv": ultimo,
        "xm_cadenas_diario_reciente.csv": cad[cad["fecha"] > corte_reciente],
        "xm_cadenas_rango_historico.csv": rango_historico(cad, "cadena_id", "pct_util", corte_hist),
        "xm_sistema_diario.csv": sistema,
        "xm_sistema_rango_historico.csv": rango_historico(sistema.assign(sistema="SIN"), "sistema", "pct_util_xm", corte_hist),
        "xm_series.csv": series,
        "_diaria_completa": diaria,
    }
