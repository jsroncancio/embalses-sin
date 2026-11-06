"""Descarga incremental de la API pública de XM (servapibi.xm.com.co) con pydataxm.

Los datos crudos se guardan tal como llegan, particionados por año:
    data/raw/xm/<Métrica>_<Entidad>/<año>.parquet
con columnas Name (si aplica), Value, Date y `descargado` (UTC).

Cada corrida vuelve a pedir los últimos `REVISION_DIAS` días, porque XM
corrige datos recientes, y reemplaza esas filas.
"""

from __future__ import annotations

import datetime as dt
from pathlib import Path

import pandas as pd

# (métrica, entidad, unidad original). Nombres verificados contra el inventario
# `ListadoMetricas` de la API (corrida "Explorar API XM", 2026-11-06).
METRICAS = [
    ("PorcVoluUtilDiar", "Embalse", "fracción"),
    ("VoluUtilDiarEner", "Embalse", "kWh"),
    ("VoluUtilDiarMasa", "Embalse", "m3"),
    ("CapaUtilDiarEner", "Embalse", "kWh"),
    ("VertEner", "Embalse", "kWh"),
    ("PorcVoluUtilDiar", "Sistema", "fracción"),
    ("VoluUtilDiarEner", "Sistema", "kWh"),
    ("CapaUtilDiarEner", "Sistema", "kWh"),
]

INICIO_HISTORICO = dt.date(2000, 1, 1)
REVISION_DIAS = 7


def _carpeta(raiz: Path, metrica: str, entidad: str) -> Path:
    return raiz / "data/raw/xm" / f"{metrica}_{entidad}"


def leer_crudo(raiz: Path, metrica: str, entidad: str) -> pd.DataFrame:
    archivos = sorted(_carpeta(raiz, metrica, entidad).glob("*.parquet"))
    if not archivos:
        return pd.DataFrame(columns=["Name", "Value", "Date", "descargado"])
    df = pd.concat([pd.read_parquet(a) for a in archivos], ignore_index=True)
    df["Date"] = pd.to_datetime(df["Date"]).dt.date
    return df


def ultima_fecha(raiz: Path, metrica: str, entidad: str) -> dt.date | None:
    df = leer_crudo(raiz, metrica, entidad)
    return None if df.empty else max(df["Date"])


def _normalizar(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    if "Name" not in df.columns:
        df["Name"] = "SIN"
    df = df[["Name", "Value", "Date"]]
    df["Name"] = df["Name"].astype(str).str.strip()
    df["Value"] = pd.to_numeric(df["Value"], errors="coerce")
    df["Date"] = pd.to_datetime(df["Date"]).dt.date
    return df.dropna(subset=["Value"])


def guardar_crudo(raiz: Path, metrica: str, entidad: str, nuevo: pd.DataFrame) -> int:
    """Une `nuevo` con lo existente (lo nuevo gana) y reescribe los años tocados."""
    if nuevo.empty:
        return 0
    nuevo = _normalizar(nuevo)
    nuevo["descargado"] = dt.datetime.now(dt.UTC).isoformat(timespec="seconds")
    carpeta = _carpeta(raiz, metrica, entidad)
    carpeta.mkdir(parents=True, exist_ok=True)
    anios = sorted({d.year for d in nuevo["Date"]})
    for anio in anios:
        ruta = carpeta / f"{anio}.parquet"
        parte = nuevo[[d.year == anio for d in nuevo["Date"]]]
        if ruta.exists():
            viejo = pd.read_parquet(ruta)
            viejo["Date"] = pd.to_datetime(viejo["Date"]).dt.date
            parte = pd.concat([viejo, parte]).drop_duplicates(subset=["Name", "Date"], keep="last")
        parte = parte.sort_values(["Date", "Name"]).reset_index(drop=True)
        parte.to_parquet(ruta, index=False)
    return len(nuevo)


def actualizar(raiz: Path, api=None, desde: dt.date | None = None, hasta: dt.date | None = None) -> dict[str, int]:
    """Descarga lo que falta de cada métrica. `api` es un pydataxm.ReadDB (inyectable en pruebas)."""
    if api is None:
        from pydataxm import pydataxm

        api = pydataxm.ReadDB()
    hasta = hasta or dt.date.today()
    resumen = {}
    for metrica, entidad, _ in METRICAS:
        inicio = desde
        if inicio is None:
            ultima = ultima_fecha(raiz, metrica, entidad)
            inicio = INICIO_HISTORICO if ultima is None else ultima - dt.timedelta(days=REVISION_DIAS)
        n = 0
        # Por años, para no lanzar cientos de peticiones simultáneas a XM.
        for a, b in _tramos_anuales(inicio, hasta):
            print(f"{metrica}/{entidad}: {a} a {b}", flush=True)
            df = api.request_data(metrica, entidad, a, b)
            n += guardar_crudo(raiz, metrica, entidad, df if df is not None else pd.DataFrame())
        resumen[f"{metrica}_{entidad}"] = n
        print(f"  {n} filas", flush=True)
    return resumen


def _tramos_anuales(inicio: dt.date, fin: dt.date) -> list[tuple[dt.date, dt.date]]:
    tramos = []
    a = inicio
    while a <= fin:
        b = min(dt.date(a.year, 12, 31), fin)
        tramos.append((a, b))
        a = b + dt.timedelta(days=1)
    return tramos
