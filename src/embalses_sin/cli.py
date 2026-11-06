"""Pipeline completo: `embalses-sin run`.

Pasos: leer PARATEC (crudo) -> calcular -> validar -> escribir data/processed
-> copiar al sitio. Si hay errores de validación no se escribe nada.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
from datetime import UTC, date, datetime
from pathlib import Path

import yaml

from . import calculos, operacion, paratec, validacion, xm
from .topologia import cargar_cadenas

RAIZ = Path(__file__).resolve().parents[2]


def _ultimo_paratec(raiz: Path) -> Path:
    archivos = sorted((raiz / "data/raw/paratec").glob("*/PARATEC_Detalle_Embalse_*.xlsx"))
    if not archivos:
        sys.exit("No hay reportes PARATEC en data/raw/paratec/")
    return archivos[-1]


def _sha256(ruta: Path) -> str:
    return hashlib.sha256(ruta.read_bytes()).hexdigest()


def run(raiz: Path = RAIZ, copiar_sitio: bool = True) -> int:
    ruta = _ultimo_paratec(raiz)
    supuestos = yaml.safe_load((raiz / "config/supuestos.yaml").read_text(encoding="utf-8"))
    potencias = {k: v for k, v in supuestos["potencia_planta_mw"].items() if not k.startswith("_")}
    cadenas = cargar_cadenas(raiz / "config/cadenas.yaml")

    basica = paratec.leer_informacion_basica(ruta)
    tecnica = paratec.leer_informacion_tecnica(ruta)
    nep_raw = paratec.leer_nep_npv(ruta)
    curvas_raw = paratec.leer_curvas_guia(ruta)

    embalses = calculos.tabla_embalses(cadenas, basica, tecnica, potencias)
    nep = calculos.tabla_nep_npv(embalses, nep_raw)
    curvas = calculos.tabla_curvas_guia(embalses, curvas_raw)
    mensual = calculos.tabla_cadenas_mensual(nep)
    resumen = calculos.tabla_cadenas(cadenas, embalses, mensual, potencias)
    topo = calculos.topologia_json(cadenas, embalses, potencias)

    hallazgos = (
        validacion.validar_topologia(cadenas, set(tecnica["embalse_paratec"]))
        + validacion.validar_esquemas(embalses, nep)
        + validacion.validar_fisica(embalses, nep, supuestos["tolerancias"])
        + validacion.validar_factor_acumulado(cadenas, embalses)
    )
    oper = operacion.tablas_operacion(raiz, cadenas)
    if oper:
        diaria = oper.pop("_diaria_completa")
        # La frescura se mide contra el dato más reciente, no contra el reloj,
        # para que el resultado sea reproducible.
        hallazgos += validacion.validar_xm(diaria, oper["xm_series.csv"], embalses, diaria["fecha"].max())
    else:
        print("Sin datos crudos de XM (data/raw/xm): se omiten las series diarias.")
    tabla_hallazgos = validacion.a_tabla(hallazgos)
    errores = tabla_hallazgos[tabla_hallazgos["severidad"] == "error"]
    print(tabla_hallazgos.to_string(index=False) if len(tabla_hallazgos) else "Sin hallazgos")
    if len(errores):
        print(f"\n{len(errores)} errores de validación: no se publica nada.", file=sys.stderr)
        return 1

    salida = raiz / "data/processed"
    salida.mkdir(parents=True, exist_ok=True)
    tablas = {
        "embalses.csv": embalses,
        "nep_npv_mensual.csv": nep,
        "curvas_guia.csv": curvas,
        "cadenas.csv": resumen,
        "cadenas_mensual.csv": mensual,
        "validacion.csv": tabla_hallazgos,
        **oper,
    }
    for nombre, df in tablas.items():
        df = df.copy()
        numericas = df.select_dtypes("number").columns
        df[numericas] = df[numericas].round(4)
        df.to_csv(salida / nombre, index=False)
    (salida / "topologia.json").write_text(json.dumps(topo, ensure_ascii=False, indent=1), encoding="utf-8")
    fuentes = {
        "generado": datetime.now(UTC).isoformat(timespec="seconds"),
        "paratec": {
            "archivo": str(ruta.relative_to(raiz)),
            "fecha_reporte": paratec.fecha_reporte(ruta),
            "sha256": _sha256(ruta),
            "origen": "XM, PARATEC: Detalle de embalse (descarga manual)",
        },
        "xm": {
            "origen": "API pública de XM (servapibi.xm.com.co) vía pydataxm",
            "ultimo_dato": str(oper["xm_sistema_diario.csv"]["fecha"].max().date()) if oper else None,
            "primer_dato": str(oper["xm_sistema_diario.csv"]["fecha"].min().date()) if oper else None,
            "metricas": [f"{m}/{e}" for m, e, *_ in xm.METRICAS],
        },
        "topologia": "config/cadenas.yaml",
        "supuestos": "config/supuestos.yaml",
        "referencias_sin": supuestos["referencias_sin"],
    }
    (salida / "fuentes.json").write_text(json.dumps(fuentes, ensure_ascii=False, indent=1, default=str), encoding="utf-8")

    if copiar_sitio:
        destino = raiz / "site/src/data"
        destino.mkdir(parents=True, exist_ok=True)
        for archivo in salida.iterdir():
            shutil.copy2(archivo, destino / archivo.name)
    print(f"\nPublicadas {len(tablas) + 2} tablas en {salida.relative_to(raiz)} ({len(embalses)} embalses, {len(resumen)} cadenas).")
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(prog="embalses-sin", description="Pipeline de cadenas de embalses del SIN")
    sub = parser.add_subparsers(dest="comando", required=True)
    p_run = sub.add_parser("run", help="Lee los crudos, calcula, valida y publica")
    p_run.add_argument("--sin-sitio", action="store_true", help="No copiar los datos a site/src/data")
    p_xm = sub.add_parser("xm", help="Descarga lo nuevo de la API de XM a data/raw/xm")
    p_xm.add_argument("--desde", type=date.fromisoformat, help="Fecha inicial AAAA-MM-DD (por defecto, incremental)")
    p_xm.add_argument("--hasta", type=date.fromisoformat, help="Fecha final AAAA-MM-DD (por defecto, hoy)")
    args = parser.parse_args()
    if args.comando == "run":
        sys.exit(run(copiar_sitio=not args.sin_sitio))
    if args.comando == "xm":
        xm.actualizar(RAIZ, desde=args.desde, hasta=args.hasta)


if __name__ == "__main__":
    main()
