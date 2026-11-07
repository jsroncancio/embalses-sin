"""Exploración de la API de XM: qué métricas de embalses existen y cómo vienen.

Se ejecuta en GitHub Actions (el dominio de XM no es accesible desde todos los entornos).
"""

import datetime as dt

import pandas as pd
from pydataxm import pydataxm

pd.set_option("display.width", 250)
pd.set_option("display.max_columns", 30)
pd.set_option("display.max_colwidth", 80)

api = pydataxm.ReadDB()
inv = api.inventario_metricas
print("COLUMNAS INVENTARIO:", list(inv.columns))
patron = "Volu|Embal|Capa|Apor|Vert|Nivel|Turb|Reser"
mask = inv["MetricId"].str.contains(patron, case=False) | inv["MetricName"].str.contains(patron, case=False)
print(inv[mask].to_string())

hoy = dt.date.today()
ini = hoy - dt.timedelta(days=5)
for metrica, entidad in [
    ("ListadoEmbalses", "Sistema"),
    ("VoluUtilDiarEner", "Embalse"),
    ("VoluUtilDiarMasa", "Embalse"),
    ("CapaUtilDiarEner", "Embalse"),
    ("PorcVoluUtilDiar", "Embalse"),
    ("VoluUtilDiarEner", "Sistema"),
]:
    print(f"\n===== {metrica} / {entidad}")
    try:
        df = api.request_data(metrica, entidad, ini, hoy)
        print(df.shape)
        print(df.head(8).to_string())
        if "Name" in df.columns:
            print("NOMBRES:", sorted(df["Name"].dropna().unique().tolist()))
        print("FECHAS:", sorted(df["Date"].astype(str).unique().tolist()) if "Date" in df.columns else "-")
    except Exception as e:  # noqa: BLE001
        print("ERROR", type(e).__name__, e)

print("\n===== Primer día disponible de VoluUtilDiarEner/Embalse (prueba 2000-01-01)")
try:
    df = api.request_data("VoluUtilDiarEner", "Embalse", dt.date(2000, 1, 1), dt.date(2000, 1, 3))
    print(df.shape, df.head(3).to_string())
except Exception as e:  # noqa: BLE001
    print("ERROR", type(e).__name__, e)
