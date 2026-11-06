from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from embalses_sin import paratec
from embalses_sin.cli import run
from embalses_sin.topologia import cargar_cadenas

RAIZ = Path(__file__).resolve().parents[1]
PARATEC = max((RAIZ / "data/raw/paratec").glob("*/PARATEC_Detalle_Embalse_*.xlsx"))


@pytest.mark.parametrize(
    "texto, esperado",
    [("1.206,26", 1206.26), ("0,4795", 0.4795), ("13.329,37", 13329.37), ("420", 420.0), (3.5, 3.5)],
)
def test_numero_colombiano(texto, esperado):
    assert paratec.numero_co(texto) == pytest.approx(esperado)


def test_guion_es_vacio():
    assert np.isnan(paratec.numero_co("-"))


def test_paratec_tiene_29_filas_y_3_agregados():
    basica = paratec.leer_informacion_basica(PARATEC)
    assert len(basica) == 29
    assert basica["agregado"].sum() == 3


def test_cadenas_cubren_los_26_embalses_individuales():
    basica = paratec.leer_informacion_basica(PARATEC)
    individuales = set(basica.loc[~basica["agregado"], "embalse_paratec"])
    en_yaml = {c.grafo.nodes[e]["paratec"] for c in cargar_cadenas(RAIZ / "config/cadenas.yaml") for e in c.embalses()}
    assert en_yaml == individuales


def test_plantas_aguas_abajo_de_penol():
    nare = next(c for c in cargar_cadenas(RAIZ / "config/cadenas.yaml") if c.id == "nare_guatape")
    assert nare.plantas_aguas_abajo("penol") == ["guatape", "playas", "san_carlos"]


def test_pipeline_reproduce_totales_conocidos(tmp_path):
    # Totales del análisis v0 (PARATEC 03-nov-2026): 17.203 GWh y 13.636 Mm³ en 26 embalses;
    # banda NEP–NPV del SIN entre 10.503 GWh (dic) y 14.361 GWh (abr).
    assert run(RAIZ, copiar_sitio=False) == 0
    cadenas = pd.read_csv(RAIZ / "data/processed/cadenas.csv")
    assert cadenas["energia_util_gwh"].sum() == pytest.approx(17203.26, abs=0.5)
    assert cadenas["vol_util_mm3"].sum() == pytest.approx(13635.76, abs=0.5)
    banda = pd.read_csv(RAIZ / "data/processed/cadenas_mensual.csv").groupby("mes")["banda_nep_npv_gwh"].sum()
    assert banda.min() == pytest.approx(10503, abs=1)
    assert banda.idxmin() == 12
    assert banda.max() == pytest.approx(14361, abs=1)
    assert banda.idxmax() == 4


def test_factor_paratec_es_acumulado():
    run(RAIZ, copiar_sitio=False)
    hallazgos = pd.read_csv(RAIZ / "data/processed/validacion.csv")
    assert not (hallazgos["regla"] == "factor_acumulado").any()
