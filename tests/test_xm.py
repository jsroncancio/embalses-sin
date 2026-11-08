"""Pruebas de la descarga y el procesamiento de XM con una API simulada (sin red)."""

import datetime as dt
import shutil
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from embalses_sin import xm
from embalses_sin.cli import run

RAIZ = Path(__file__).resolve().parents[1]

NOMBRES = [
    "AGREGADO BOGOTA", "ALTOANCHICAYA", "AMANI", "BETANIA", "CALIMA1", "CHUZA", "EL QUIMBO", "ESMERALDA",
    "GUAVIO", "ITUANGO", "MIRAFLORES", "MUNA", "PENOL", "PLAYAS", "PORCE II", "PORCE III", "PRADO",
    "PUNCHINA", "RIOGRANDE2", "SALVAJINA", "SAN LORENZO", "TOPOCORO", "TRONERAS", "URRA1",
]  # fmt: skip


class APISimulada:
    """Imita pydataxm.ReadDB.request_data con el formato real (Id, Name, Value, Date)."""

    def __init__(self):
        self.llamadas = []

    def request_data(self, metrica, entidad, inicio, fin):
        self.llamadas.append((metrica, entidad, inicio, fin))
        fechas = pd.date_range(inicio, fin, freq="D")
        doy = fechas.dayofyear.to_numpy()
        pct = 0.6 + 0.25 * np.sin(2 * np.pi * doy / 365)
        if entidad == "Recurso":
            # Capacidad efectiva neta en kW: 100 MW por recurso, más uno ajeno que se descarta.
            codigos = sorted(xm._codigos_recursos(RAIZ)) + ["AJENO"]
            return pd.DataFrame([{"Id": "Recurso", "Code": c, "Value": 100_000.0, "Date": f} for c in codigos for f in fechas.date])
        if entidad == "Sistema":
            cap = 17_000e6
            valores = {"PorcVoluUtilDiar": pct, "VoluUtilDiarEner": pct * cap, "CapaUtilDiarEner": np.full(len(doy), cap)}
            return pd.DataFrame({"Id": "Sistema", "Value": valores[metrica], "Date": fechas.date})
        filas = []
        for i, nombre in enumerate(NOMBRES):
            cap = (100 + 10 * i) * 1e6
            valores = {
                "PorcVoluUtilDiar": pct,
                "VoluUtilDiarEner": pct * cap,
                "VoluUtilDiarMasa": pct * cap / 2,
                "CapaUtilDiarEner": np.full(len(doy), cap),
                "VertEner": np.zeros(len(doy)),
            }[metrica]
            filas.append(pd.DataFrame({"Id": "Embalse", "Name": nombre, "Value": valores, "Date": fechas.date}))
        return pd.concat(filas, ignore_index=True)


@pytest.fixture
def raiz(tmp_path):
    shutil.copytree(RAIZ / "config", tmp_path / "config")
    shutil.copytree(RAIZ / "data/raw/paratec", tmp_path / "data/raw/paratec")
    return tmp_path


def test_tramos_anuales():
    tramos = xm._tramos_anuales(dt.date(2023, 11, 1), dt.date(2025, 2, 3))
    assert tramos == [
        (dt.date(2023, 11, 1), dt.date(2023, 12, 31)),
        (dt.date(2024, 1, 1), dt.date(2024, 12, 31)),
        (dt.date(2025, 1, 1), dt.date(2025, 2, 3)),
    ]


def test_descarga_incremental_reemplaza_dias_revisados(raiz):
    api = APISimulada()
    xm.actualizar(raiz, api=api, desde=dt.date(2024, 1, 1), hasta=dt.date(2024, 3, 1))
    antes = xm.leer_crudo(raiz, "VoluUtilDiarEner", "Embalse")
    assert len(antes) == 61 * len(NOMBRES)

    api.llamadas.clear()
    xm.actualizar(raiz, api=api, hasta=dt.date(2024, 3, 5))
    # Incremental: vuelve a pedir desde 7 días antes del último dato.
    assert api.llamadas[0][2] == dt.date(2024, 2, 23)
    despues = xm.leer_crudo(raiz, "VoluUtilDiarEner", "Embalse")
    assert len(despues) == 65 * len(NOMBRES)
    assert not despues.duplicated(subset=["Name", "Date"]).any()


def test_pipeline_con_xm(raiz):
    xm.actualizar(raiz, api=APISimulada(), desde=dt.date(2022, 1, 1), hasta=dt.date(2024, 6, 30))
    assert run(raiz, copiar_sitio=False) == 0
    salida = raiz / "data/processed"
    cad = pd.read_csv(salida / "xm_cadenas_diario.csv")
    assert set(cad["cadena_id"]) == set(pd.read_csv(salida / "cadenas.csv")["cadena_id"])
    assert cad["pct_util"].between(0, 100).all()
    ref = pd.read_csv(salida / "xm_referencia_nep_npv.csv")
    assert (ref["nep_pct"] <= ref["npv_pct"]).all()
    assert set(ref["tipo"]) == {"embalse", "cadena", "sistema"}
    # SIN: misma banda que el análisis de PARATEC en diciembre (10.503 GWh de 17.203 GWh menos Ituango).
    sin_dic = ref[(ref["tipo"] == "sistema") & (ref["mes"] == 12)].iloc[0]
    assert 0 < sin_dic["nep_pct"] < sin_dic["npv_pct"] < 100
    validacion = pd.read_csv(salida / "validacion.csv")
    assert not (validacion["regla"] == "xm_serie_faltante").any()


def test_serie_faltante_es_error(raiz):
    api = APISimulada()
    original = api.request_data

    def sin_guavio(*args):
        df = original(*args)
        return df[df.get("Name", pd.Series(dtype=str)) != "GUAVIO"] if "Name" in df.columns else df

    api.request_data = sin_guavio
    xm.actualizar(raiz, api=api, desde=dt.date(2024, 1, 1), hasta=dt.date(2024, 2, 1))
    assert run(raiz, copiar_sitio=False) == 1


def test_capacidad_efectiva_reemplaza_supuestos(raiz):
    xm.actualizar(raiz, api=APISimulada(), desde=dt.date(2026, 10, 1), hasta=dt.date(2026, 10, 3))
    crudo = xm.leer_crudo(raiz, "CapEfecNeta", "Recurso")
    assert "AJENO" not in set(crudo["Name"])
    assert run(raiz, copiar_sitio=False) == 0
    cap = pd.read_csv(raiz / "data/processed/capacidad_plantas.csv").set_index("planta_id")
    assert cap.loc["guatape", "fuente"] == "XM"
    assert cap.loc["guatape", "potencia_mw"] == pytest.approx(100)
    # Cadena antigua suma 9 recursos; La Guaca va incluida en Paraíso (PAGUA).
    assert cap.loc["cadena_antigua", "potencia_mw"] == pytest.approx(900)
    assert cap.loc["la_guaca", "potencia_mw"] == 0
    assert (cap["fuente"] != "supuesto").all()
    emb = pd.read_csv(raiz / "data/processed/embalses.csv").set_index("nodo_id")
    # Peñol: Guatapé + Playas + San Carlos.
    assert emb.loc["penol", "potencia_aguas_abajo_mw"] == pytest.approx(300)
