# Embalses del SIN: cadenas hidráulicas, capacidad y operación

Análisis reproducible de los embalses del Sistema Interconectado Nacional (SIN) de Colombia como **batería hidroeléctrica**: cómo se conectan en cadenas, cuánta energía pueden almacenar y cuánta de ella es flexible mes a mes para respaldar la generación solar y eólica.

**Sitio:** https://jsroncancio.github.io/embalses-sin/ (se publica con GitHub Pages en cada cambio a `main`).

## Qué hay hoy

- **13 cadenas o sistemas** con su topología como grafo (`config/cadenas.yaml`): 26 embalses individuales y sus plantas.
- **Capacidad declarada en PARATEC (XM)**, reporte del 3 de noviembre de 2026: 13.636 Mm³ y 17.203 GWh de energía útil.
- **Banda flexible NEP–NPV** por embalse, cadena y mes: entre 10.503 GWh (diciembre) y 14.361 GWh (abril) para el SIN.
- **Capacidad efectiva neta de cada planta** (XM), para calcular cuántas horas puede entregar cada cadena a plena potencia.
- **Nivel diario de cada embalse** desde enero de 2025, descargado de la API pública de XM cada mañana (8:30 a. m.) y comparado con la banda NEP–NPV del mes.
- **Validación automática** de esquemas, reglas físicas y topología. Las inconsistencias de la fuente se publican como advertencias, no se corrigen en silencio.

| Tipo de cifra | Ejemplo | Dónde vive |
| --- | --- | --- |
| Dato oficial | Volumen útil, factor de conversión, NEP y NPV | `data/raw/` (XM, sin modificar) |
| Cálculo | Energía útil por cadena, banda flexible mensual | `src/embalses_sin/calculos.py` |
| Dato oficial | Capacidad efectiva neta por planta | `data/raw/xm/CapEfecNeta_Recurso/` (XM, a diario) |

## Cómo reproducirlo

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
embalses-sin xm         # descarga lo nuevo de la API de XM a data/raw/xm
embalses-sin run        # lee data/raw, calcula, valida y escribe data/processed
pytest                  # pruebas, incluidos los totales conocidos

cd site && npm ci && npm run dev   # sitio local en http://127.0.0.1:3000
```

## Estructura

```
config/            topología de cadenas y supuestos (editados a mano)
data/raw/          archivos de XM tal como se descargaron
data/processed/    tablas finales (CSV y JSON) que consume el sitio
docs/              registro de fuentes
src/embalses_sin/  lectura de PARATEC, cálculos, validación y CLI
tests/             pruebas
site/              sitio web (Observable Framework)
.github/workflows/ CI y publicación en GitHub Pages
```

## Hoja de ruta

1. **Base y catálogo** (esta versión): PARATEC, topología, validación y sitio.
2. **Datos de XM** (hecha): nivel diario por embalse y capacidad efectiva neta por planta, actualizados a diario.
3. **Operación**: perfiles horarios de generación, autonomía por cadena con datos reales, comparador.
4. **Publicación**: revisión de licencias, metodología completa, versión 1.0 con DOI.

## Licencia y citación

Código bajo [MIT](LICENSE). Datos derivados bajo CC BY 4.0; los datos crudos son de XM (ver [LICENSE-DATA.md](LICENSE-DATA.md)). Para citar, use el botón "Cite this repository" de GitHub ([CITATION.cff](CITATION.cff)).
