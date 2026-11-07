---
title: Metodología y fuentes
---

```js
import {num} from "./components/formato.js";
const fuentes = FileAttachment("data/fuentes.json").json();
const validacion = FileAttachment("data/validacion.csv").csv({typed: true});
```

# Metodología y fuentes

Cada cifra del sitio es de uno de tres tipos: **dato oficial** de XM, **cálculo** con la fórmula de esta página, o **supuesto** (marcado con asterisco y guardado en `config/supuestos.yaml`).

## Fuentes

| Fuente | Qué aporta | Archivo en el repositorio |
| --- | --- | --- |
| PARATEC, XM: Detalle de embalse | Niveles, volúmenes, factor de conversión, energía útil, curvas guía, NEP y NPV | `data/raw/paratec/<fecha>/` |
| Diagramas topológicos de los agentes declarados ante XM | Conexiones aguas arriba y abajo, desviaciones, usos de agua | `config/cadenas.yaml` (transcrito a mano) |
| API pública de XM (servapibi, vía `pydataxm`) | Nivel diario por embalse y del SIN desde 2025: % del volumen útil, energía almacenada y capacidad útil | `data/raw/xm/` (se actualiza a diario) |
| Sinergox, XM | Totales de referencia del SIN | `config/supuestos.yaml` |

```js
html`<p>Reporte PARATEC usado: <code>${fuentes.paratec.archivo}</code>, generado el ${fuentes.paratec.fecha_reporte}. Suma SHA-256: <code>${fuentes.paratec.sha256.slice(0, 16)}…</code>. Datos procesados el ${fuentes.generado.slice(0, 10)}.</p>`
```

## Cálculos

**Energía útil de una cadena.** Es la suma de la energía útil declarada por cada embalse. El factor de conversión de PARATEC es acumulado: ya incluye todas las plantas aguas abajo. Por ejemplo, Peñol tiene 3,99 GWh/Mm³, Playas 1,98 y Punchiná 1,50, porque el agua de Peñol turbina en Guatapé, Playas y San Carlos. El pipeline comprueba en cada corrida que el factor de un embalse nunca es menor que el de un embalse aguas abajo.

**Franjas mensuales.** Para cada embalse y mes, con E = energía útil:

- Bajo NEP = NEP × E (reserva que no se debería usar).
- Banda flexible = (NPV − NEP) × E.
- Sobre NPV = (1 − NPV) × E (por encima, riesgo de vertimiento).

Se asume factor de conversión constante con el nivel, la misma convención de PARATEC.

**Horas a potencia (supuesto).** Energía útil × 1.000 ÷ suma de la potencia de las plantas que turbinan esa agua, sin contar aportes. Es un orden de magnitud: la cifra real depende del caudal máximo de la primera planta, que se incorporará cuando haya datos de turbinamiento.

**Nivel diario.** Es el volumen útil como porcentaje de la capacidad útil, tal como lo publica XM (métrica `PorcVoluUtilDiar`); XM no publica la cota en m.s.n.m. El nivel de una cadena es su energía almacenada sobre su capacidad útil, ambas sumadas en GWh. La referencia de cada gráfica es la banda NEP–NPV del mes; para una cadena o el SIN se pondera por la energía útil de PARATEC.

## Supuestos vigentes

- Potencias por planta: aproximadas. Se reemplazan por la capacidad efectiva neta de XM en la fase 2.
- NEP = NPV = 0 todo el año se interpreta como "no declarado" (caso Ituango).
- Régimen por días a potencia: 60 o más multianual, 10 a 60 estacional, menos de 10 semanal o diario.

## Advertencias de la validación

Inconsistencias encontradas en la fuente. No se corrigen: se publican tal como vienen y se señalan aquí.

```js
Inputs.table(validacion, {
  columns: ["objeto", "regla", "detalle"],
  header: {objeto: "Embalse", regla: "Regla", detalle: "Detalle"},
  rows: 20
})
```
