"""Explora en la API de XM la capacidad efectiva neta de las plantas hidráulicas.

Imprime el listado de recursos hidráulicos (código, nombre, tipo de despacho) y su
capacidad efectiva neta más reciente, para mapearlos a config/cadenas.yaml.
"""

import datetime as dt

import pandas as pd
from pydataxm import pydataxm

pd.set_option("display.width", 250)
pd.set_option("display.max_rows", 400)
pd.set_option("display.max_columns", 30)

api = pydataxm.ReadDB()
hoy = dt.date.today()
hace = hoy - dt.timedelta(days=10)

inv = api.get_collections()
print(inv[inv["MetricId"].str.contains("CapEfec|ListadoRecursos", case=False)].to_string())

rec = api.request_data("ListadoRecursos", "Sistema", hace, hoy)
print("\nColumnas ListadoRecursos:", list(rec.columns))
rec = rec.drop_duplicates(subset=[c for c in rec.columns if c.lower().endswith("code")][:1] or None)
tipo = [c for c in rec.columns if "EnerSource" in c or "Source" in c]
if tipo:
    print(rec[tipo[0]].value_counts().to_string())
    hid = rec[rec[tipo[0]].astype(str).str.upper().str.contains("AGUA|HIDR")]
else:
    hid = rec
print(f"\nRecursos hidráulicos: {len(hid)}")
print(hid.to_string())

cap = api.request_data("CapEfecNeta", "Recurso", hace, hoy)
print(cap.head().to_string())
cap = cap.sort_values("Date").groupby("Code").tail(1)
m = hid.merge(cap[["Code", "Value", "Date"]], left_on="Values_Code", right_on="Code", how="left")
m["MW"] = pd.to_numeric(m["Value"], errors="coerce") / 1000
cols = ["Values_Code", "Values_Name", "Values_Disp", "Values_RecType", "Values_CompanyCode", "MW", "Date_y"]
print("\nHidráulicas con capacidad efectiva neta (MW):")
print(m[cols].sort_values("Values_Name").to_csv(index=False))
