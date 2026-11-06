"""Lectura del reporte "Detalle de Embalse" de PARATEC (XM).

El Excel guarda los números como texto en formato colombiano
("1.206,26" = 1206.26) y usa "-" para valores vacíos. Este módulo
convierte cada hoja en una tabla limpia y tipada.
"""

from __future__ import annotations

import re
from pathlib import Path

import numpy as np
import pandas as pd

MESES = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]

_COLUMNAS_TECNICA = {
    "Nombre del embalse": "embalse_paratec",
    "Nivel mínimo físico [m.s.n.m]": "nivel_min_fisico_msnm",
    "Nivel mínimo técnico [m.s.n.m]": "nivel_min_tecnico_msnm",
    "Nivel máximo físico [m.s.n.m]": "nivel_max_fisico_msnm",
    "Volumen muerto [Mm3]": "vol_muerto_mm3",
    "Volumen mínimo técnico [Mm3]": "vol_min_tecnico_mm3",
    "Volumen máximo técnico [Mm3]": "vol_max_tecnico_mm3",
    "Volumen útil [Mm3]": "vol_util_mm3",
    "Volumen mínimo técnico [GWh]": "energia_min_tecnico_gwh",
    "Volumen máximo técnico [GWh]": "energia_max_tecnico_gwh",
    "Volumen útil [GWh]": "energia_util_gwh",
    "Volumen total del embalse [Mm3]": "vol_total_mm3",
    "Factor de conversión hidráulico [GWh/Mm3]": "factor_gwh_mm3",
}

_COLUMNAS_BASICA = {
    "Nombre del embalse": "embalse_paratec",
    "Operador": "operador",
    "Embalse agregado(SI/NO)": "agregado",
    "Embalses que componen el agregado": "componentes",
    "Región hidrológica": "region_hidrologica",
    "Latitud [°]": "latitud",
    "Longitud [°]": "longitud",
    "Estación hidrológica": "estaciones",
}


def numero_co(valor) -> float:
    """Convierte un número en formato colombiano a float. "-" o vacío -> NaN."""
    if valor is None:
        return np.nan
    if isinstance(valor, (int, float)):
        return float(valor)
    texto = str(valor).strip()
    if texto in {"", "-", "—"}:
        return np.nan
    texto = texto.replace(".", "").replace(",", ".")
    return float(texto)


def _normalizar(texto) -> str:
    return re.sub(r"\s+", " ", str(texto)).strip()


def _leer_hoja(ruta: Path, hoja: str, fila_encabezado: int) -> pd.DataFrame:
    crudo = pd.read_excel(ruta, sheet_name=hoja, header=None, dtype=object)
    encabezado = [_normalizar(c) for c in crudo.iloc[fila_encabezado]]
    df = crudo.iloc[fila_encabezado + 1 :].copy()
    df.columns = encabezado
    df = df.loc[:, [c for c in df.columns if c and c != "nan"]]
    df = df[df.iloc[:, 0].notna()]
    return df.reset_index(drop=True)


def leer_informacion_basica(ruta: Path) -> pd.DataFrame:
    df = _leer_hoja(ruta, "Información_Básica", 5).rename(columns=_COLUMNAS_BASICA)
    df = df[list(_COLUMNAS_BASICA.values())]
    df["agregado"] = df["agregado"].str.strip().str.lower().eq("si")
    for col in ["latitud", "longitud"]:
        df[col] = df[col].map(numero_co)
    for col in ["componentes", "estaciones"]:
        df[col] = df[col].map(lambda s: "; ".join(x.strip() for x in str(s).splitlines() if x.strip() and x.strip() != "-"))
    df["embalse_paratec"] = df["embalse_paratec"].str.strip()
    return df


def leer_informacion_tecnica(ruta: Path) -> pd.DataFrame:
    df = _leer_hoja(ruta, "Información_Técnica", 5).rename(columns=_COLUMNAS_TECNICA)
    df = df[list(_COLUMNAS_TECNICA.values())]
    for col in df.columns[1:]:
        df[col] = df[col].map(numero_co)
    df["embalse_paratec"] = df["embalse_paratec"].str.strip()
    return df


def _leer_mensual(ruta: Path, hoja: str, col_variable: str) -> pd.DataFrame:
    df = _leer_hoja(ruta, hoja, 7)
    meses_orig = df.columns[4:16]
    df = df.rename(columns=dict(zip(meses_orig, MESES)))
    df = df.rename(columns={"Nombre del embalse": "embalse_paratec", col_variable: "variable"})
    largo = df.melt(id_vars=["embalse_paratec", "variable"], value_vars=MESES, var_name="mes_nombre", value_name="valor")
    largo["mes"] = largo["mes_nombre"].map({m: i + 1 for i, m in enumerate(MESES)})
    largo["valor"] = largo["valor"].map(numero_co)
    largo["embalse_paratec"] = largo["embalse_paratec"].str.strip()
    largo["variable"] = largo["variable"].str.strip()
    return largo[["embalse_paratec", "variable", "mes", "valor"]]


def leer_nep_npv(ruta: Path) -> pd.DataFrame:
    """NEP y NPV mensuales como fracción del volumen útil (0 a 1)."""
    largo = _leer_mensual(ruta, "NEP-NPV", "Variable")
    ancho = largo.pivot_table(index=["embalse_paratec", "mes"], columns="variable", values="valor").reset_index()
    ancho.columns.name = None
    ancho = ancho.rename(columns={"NEP": "nep", "NPV": "npv"})
    # Un NPV de 0 todo el año (embalse siempre "vertiendo") no tiene sentido físico:
    # PARATEC lo usa cuando el agente no ha declarado curvas (caso Ituango).
    no_declarado = ancho.groupby("embalse_paratec")["npv"].transform("max").eq(0)
    ancho.loc[no_declarado, ["nep", "npv"]] = np.nan
    return ancho


def leer_curvas_guia(ruta: Path) -> pd.DataFrame:
    """Curvas guía máxima y mínima mensuales en Mm³ (referidas al nivel mínimo físico)."""
    largo = _leer_mensual(ruta, "Curvas_Operación", "Curva de Operación [Mm3]")
    largo["variable"] = largo["variable"].map({"Curva guía máxima": "curva_guia_max_mm3", "Curva guía mínima": "curva_guia_min_mm3"})
    ancho = largo.pivot_table(index=["embalse_paratec", "mes"], columns="variable", values="valor").reset_index()
    ancho.columns.name = None
    return ancho


def fecha_reporte(ruta: Path) -> str:
    """Fecha de generación del reporte, tomada del nombre del archivo (dd-mm-aaaa)."""
    m = re.search(r"(\d{2})-(\d{2})-(\d{4})", ruta.name)
    if not m:
        raise ValueError(f"No se encontró la fecha en el nombre {ruta.name}")
    d, mth, y = m.groups()
    return f"{y}-{mth}-{d}"
