"""Validación de datos: esquemas (pandera) y reglas físicas.

Cada regla devuelve hallazgos con severidad:
- "error": el dato es imposible o falta algo obligatorio. Detiene el pipeline.
- "advertencia": inconsistencia en la fuente. Se publica, señalada en el sitio.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

import networkx as nx
import pandas as pd
import pandera.pandas as pa

from .topologia import Cadena


@dataclass
class Hallazgo:
    regla: str
    severidad: str
    objeto: str
    detalle: str


ESQUEMA_EMBALSES = pa.DataFrameSchema(
    {
        "cadena_id": pa.Column(str),
        "nodo_id": pa.Column(str, unique=True),
        "embalse_paratec": pa.Column(str, unique=True),
        "vol_util_mm3": pa.Column(float, pa.Check.gt(0)),
        "vol_max_tecnico_mm3": pa.Column(float, pa.Check.gt(0)),
        "vol_min_tecnico_mm3": pa.Column(float, pa.Check.ge(0)),
        "energia_util_gwh": pa.Column(float, pa.Check.gt(0)),
        "factor_gwh_mm3": pa.Column(float, pa.Check.in_range(0, 10)),
        "latitud": pa.Column(float, pa.Check.in_range(-5, 14)),
        "longitud": pa.Column(float, pa.Check.in_range(-82, -66)),
    },
    strict=False,
)

ESQUEMA_NEP = pa.DataFrameSchema(
    {
        "mes": pa.Column(int, pa.Check.in_range(1, 12)),
        "nep": pa.Column(float, pa.Check.in_range(0, 1), nullable=True),
        "npv": pa.Column(float, pa.Check.in_range(0, 1), nullable=True),
    },
    strict=False,
)


def validar_esquemas(embalses: pd.DataFrame, nep: pd.DataFrame) -> list[Hallazgo]:
    hallazgos = []
    for nombre, esquema, df in [("embalses", ESQUEMA_EMBALSES, embalses), ("nep_npv", ESQUEMA_NEP, nep)]:
        try:
            esquema.validate(df, lazy=True)
        except pa.errors.SchemaErrors as e:
            for _, f in e.failure_cases.iterrows():
                hallazgos.append(Hallazgo("esquema", "error", nombre, f"{f['column']}: {f['check']} (valor {f['failure_case']})"))
    return hallazgos


def validar_topologia(cadenas: list[Cadena], embalses_paratec: set[str]) -> list[Hallazgo]:
    hallazgos = []
    vistos: set[str] = set()
    for c in cadenas:
        if not nx.is_directed_acyclic_graph(c.grafo):
            hallazgos.append(Hallazgo("topologia_ciclo", "error", c.id, "La cadena tiene un ciclo no declarado"))
        for n in c.grafo.nodes:
            if n in vistos:
                hallazgos.append(Hallazgo("topologia_id_repetido", "error", c.id, f"Nodo {n} repetido en otra cadena"))
            vistos.add(n)
        for emb in c.embalses():
            nombre = c.grafo.nodes[emb].get("paratec")
            if nombre not in embalses_paratec:
                hallazgos.append(Hallazgo("topologia_paratec", "error", emb, f"'{nombre}' no existe en PARATEC"))
            if not c.plantas_aguas_abajo(emb):
                hallazgos.append(Hallazgo("topologia_sin_planta", "error", emb, "El embalse no alimenta ninguna planta"))
    return hallazgos


def validar_fisica(embalses: pd.DataFrame, nep: pd.DataFrame, tolerancias: dict) -> list[Hallazgo]:
    hallazgos = []
    tol_e = tolerancias["energia_vs_volumen_x_factor"]
    tol_v = tolerancias["volumen_util_vs_rango"]
    for _, r in embalses.iterrows():
        if not (r["nivel_min_fisico_msnm"] <= r["nivel_min_tecnico_msnm"] <= r["nivel_max_fisico_msnm"]):
            hallazgos.append(
                Hallazgo("niveles_ordenados", "error", r["embalse"], "Niveles mínimo físico, técnico y máximo no están en orden")
            )
        rango = r["vol_max_tecnico_mm3"] - r["vol_min_tecnico_mm3"]
        if abs(rango / r["vol_util_mm3"] - 1) > tol_v:
            hallazgos.append(
                Hallazgo(
                    "volumen_util_vs_rango",
                    "advertencia",
                    r["embalse"],
                    f"Vol. máx. técnico − mín. técnico = {rango:.2f} Mm³ frente a vol. útil {r['vol_util_mm3']:.2f} Mm³",
                )
            )
        dif = r["energia_control_gwh"] / r["energia_util_gwh"] - 1
        if abs(dif) > tol_e:
            hallazgos.append(
                Hallazgo(
                    "energia_vs_volumen_x_factor",
                    "advertencia",
                    r["embalse"],
                    f"Vol. útil × factor = {r['energia_control_gwh']:.1f} GWh frente a {r['energia_util_gwh']:.1f} GWh declarados ({dif * 100:+.0f} %)",
                )
            )
    sin_nep = nep.groupby("embalse")["nep"].apply(lambda s: s.isna().all())
    for emb in sin_nep[sin_nep].index:
        hallazgos.append(Hallazgo("nep_faltante", "advertencia", emb, "Sin NEP ni NPV declarados en PARATEC"))
    invertidos = nep[nep["nep"] > nep["npv"]]
    for _, r in invertidos.iterrows():
        hallazgos.append(Hallazgo("nep_mayor_npv", "error", r["embalse"], f"NEP > NPV en el mes {r['mes']}"))
    return hallazgos


def validar_factor_acumulado(cadenas: list[Cadena], embalses: pd.DataFrame) -> list[Hallazgo]:
    """El factor de un embalse debe ser mayor que el de cualquier embalse aguas abajo
    con generación entre ambos. Si se cumple, el factor de PARATEC es acumulado."""
    hallazgos = []
    factor = embalses.set_index("nodo_id")["factor_gwh_mm3"]
    for c in cadenas:
        for emb in c.embalses():
            for abajo in c.embalses_aguas_abajo(emb):
                if factor[emb] < factor[abajo]:
                    hallazgos.append(
                        Hallazgo(
                            "factor_acumulado",
                            "advertencia",
                            emb,
                            f"Factor {factor[emb]:.4f} menor que el de {abajo} aguas abajo ({factor[abajo]:.4f})",
                        )
                    )
    return hallazgos


def a_tabla(hallazgos: list[Hallazgo]) -> pd.DataFrame:
    return pd.DataFrame([asdict(h) for h in hallazgos], columns=["regla", "severidad", "objeto", "detalle"])


def validar_capacidad(tabla: pd.DataFrame) -> list[Hallazgo]:
    """Plantas sin capacidad efectiva neta de XM (usan el supuesto o no tienen potencia)."""
    hallazgos = []
    for _, f in tabla.iterrows():
        if f["fuente"] == "supuesto":
            hallazgos.append(
                Hallazgo(
                    "capacidad_supuesta",
                    "advertencia",
                    f["planta"],
                    f"Sin dato de XM para {f['recursos_xm'] or 'ningún recurso'}; se usa la potencia aproximada de config/supuestos.yaml",
                )
            )
        elif pd.isna(f["potencia_mw"]):
            hallazgos.append(Hallazgo("capacidad_faltante", "advertencia", f["planta"], "Sin capacidad de XM ni potencia supuesta"))
    return hallazgos


def validar_xm(diaria: pd.DataFrame, series: pd.DataFrame, embalses: pd.DataFrame, hoy: pd.Timestamp) -> list[Hallazgo]:
    """Reglas sobre las series diarias de XM."""
    hallazgos = []
    en_xm = set(diaria["serie_xm"])
    esperadas = set(series["serie_xm"])
    for s in sorted(esperadas - en_xm):
        hallazgos.append(Hallazgo("xm_serie_faltante", "error", s, "La serie no llegó de la API de XM"))
    for s in sorted(en_xm - esperadas):
        hallazgos.append(Hallazgo("xm_serie_sin_mapear", "advertencia", s, "Embalse de XM sin cadena asignada en config/cadenas.yaml"))

    ultima = diaria.groupby("serie_xm")["fecha"].max()
    for s, f in ultima.items():
        dias = (hoy - f).days
        if s in esperadas and dias > 5:
            hallazgos.append(Hallazgo("xm_dato_viejo", "advertencia", s, f"Último dato del {f.date()} ({dias} días)"))

    raros = diaria[(diaria["pct_util"] < -20) | (diaria["pct_util"] > 120)]
    for s, g in raros.groupby("serie_xm"):
        hallazgos.append(
            Hallazgo(
                "xm_pct_fuera_de_rango",
                "advertencia",
                s,
                f"{len(g)} días con % útil fuera de −20 a 120 % (p. ej. {g['fecha'].iloc[0].date()})",
            )
        )

    # Cruce con PARATEC: capacidad útil del último día frente a la energía útil declarada.
    ult = diaria.sort_values("fecha").groupby("serie_xm").tail(1).set_index("serie_xm")["capacidad_gwh"]
    paratec = embalses.merge(
        series.assign(nodo_id=series["nodos"].str.split(", ")).explode("nodo_id")[["nodo_id", "serie_xm"]], on="nodo_id"
    )
    paratec = paratec.groupby("serie_xm")["energia_util_gwh"].sum()
    for s in ult.index.intersection(paratec.index):
        dif = ult[s] / paratec[s] - 1
        if abs(dif) > 0.05:
            hallazgos.append(
                Hallazgo(
                    "xm_vs_paratec",
                    "advertencia",
                    s,
                    f"Capacidad útil XM {ult[s]:.1f} GWh frente a {paratec[s]:.1f} GWh en PARATEC ({dif * 100:+.0f} %)",
                )
            )
    return hallazgos
