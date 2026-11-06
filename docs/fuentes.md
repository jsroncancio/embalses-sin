# Registro de fuentes

| Fuente | Contenido | Fecha | Dónde está |
| --- | --- | --- | --- |
| PARATEC (XM), reporte "Detalle de embalse" | Información básica y técnica, curvas guía, NEP y NPV de 29 embalses (26 individuales y 3 agregados) | 2026-11-03 | `data/raw/paratec/2026-11-03/` |
| Diagramas topológicos declarados por los agentes ante XM (EPM, ISAGEN, Enel/Emgesa, Celsia/EPSA, AES, Urrá), 2010 a 2022 | Conexiones entre embalses, plantas, desviaciones y usos de agua | varias | No se redistribuyen; transcritos a `config/cadenas.yaml` |
| Sinergox (XM) | Capacidad efectiva neta hidráulica del SIN: 13.329,37 MW | 2026-10-31 | `config/supuestos.yaml` |

## Cómo actualizar PARATEC

1. Descargue el reporte "Detalle de embalse" desde PARATEC.
2. Guárdelo sin modificar en `data/raw/paratec/<aaaa-mm-dd>/PARATEC_Detalle_Embalse_<dd-mm-aaaa>.xlsx`.
3. Ejecute `embalses-sin run`. El pipeline usa siempre el reporte más reciente y se detiene si algo no valida.
4. Revise `data/processed/validacion.csv` y haga commit de los cambios.

## Diagramas usados por cadena

| Cadena | Diagrama |
| --- | --- |
| Nare–Guatapé | Playas.pdf, SanCarlos.pdf, SanMiguel.pdf |
| Porce–Guadalupe–Riogrande | Troneras.pdf, LaTasajera.pdf, Porce 2.pdf, Porce 3.pdf |
| Bogotá–Pagua | Paraiso.pdf |
| Cauca | Salvajina.pdf, SanFrancisco.pdf |
| Sogamoso | Sogamoso.pdf |
| La Miel | Miel1.pdf |
| Urrá | Urrá.pdf |
| Prado | Prado.pdf |
| Calima | sin diagrama; topología desde estaciones hidrológicas de PARATEC |
