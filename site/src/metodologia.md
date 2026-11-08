---
title: Metodología y fuentes
---

```js
import {num} from "./components/formato.js";
const fuentes = FileAttachment("data/fuentes.json").json();
const validacion = FileAttachment("data/validacion.csv").csv({typed: true});
const capacidad = FileAttachment("data/capacidad_plantas.csv").csv({typed: true});
```

# Metodología y fuentes

Cada cifra del sitio es de uno de tres tipos: **dato oficial** de XM, **cálculo** con la fórmula de esta página, o **supuesto** (marcado con asterisco y guardado en `config/supuestos.yaml`).

## Fuentes

| Fuente | Qué aporta | Archivo en el repositorio |
| --- | --- | --- |
| PARATEC, XM: Detalle de embalse | Niveles, volúmenes, factor de conversión, energía útil, curvas guía, NEP y NPV | `data/raw/paratec/<fecha>/` |
| Diagramas topológicos de los agentes declarados ante XM | Conexiones aguas arriba y abajo, desviaciones, usos de agua | `config/cadenas.yaml` (transcrito a mano) |
| API pública de XM (servapibi, vía `pydataxm`) | Nivel diario por embalse y del SIN desde 2025: % del volumen útil, energía almacenada y capacidad útil | `data/raw/xm/` (se actualiza a diario) |
| API pública de XM, métrica `CapEfecNeta` por recurso | Capacidad efectiva neta de cada planta (MW) | `data/raw/xm/CapEfecNeta_Recurso/` (se actualiza a diario) |
| Sinergox, XM | Totales de referencia del SIN | `config/supuestos.yaml` |

```js
html`<p>Reporte PARATEC usado: <code>${fuentes.paratec.archivo}</code>, generado el ${fuentes.paratec.fecha_reporte}. Suma SHA-256: <code>${fuentes.paratec.sha256.slice(0, 16)}…</code>. Datos procesados el ${fuentes.generado.slice(0, 10)}.</p>`
```

## Qué son el NEP y el NPV

Cada agente declara en PARATEC, para cada embalse y cada mes, dos niveles expresados como porcentaje del volumen útil:

- **NEP, Nivel ENFICC Probabilístico.** Es el "nivel del embalse de una planta hidráulica suficiente para generar la ENFICC Base de la planta", aun con los aportes más críticos de la historia. La ENFICC es la energía firme que la planta compromete en el Cargo por Confiabilidad (Resolución CREG 071 de 2006). Por debajo del NEP el embalse está usando su reserva de confiabilidad.
- **NPV, Nivel de Probabilidad de Vertimiento.** Es el "nivel del embalse de una planta hidráulica a partir del cual existe probabilidad de vertimiento". Por encima, el agua que llegue puede salir por el rebosadero sin generar.

Las definiciones citadas son las del estatuto para situaciones de riesgo de desabastecimiento de la CREG (proyecto 701 143 de 2026, adoptado como Resolución CREG 101 127 de 2026). Durante un período de riesgo de desabastecimiento, ese estatuto usa el NEP y el NPV para fijar la curva de oferta de las plantas hidráulicas con embalse.

Cuando un embalse declara el mismo valor para NEP y NPV, la banda flexible de ese mes es cero: el agente indica que el embalse debe quedarse en ese nivel.

## Cálculos

**Energía útil de una cadena.** Es la suma de la energía útil declarada por cada embalse. El factor de conversión de PARATEC es acumulado: ya incluye todas las plantas aguas abajo. Por ejemplo, Peñol tiene 3,99 GWh/Mm³, Playas 1,98 y Punchiná 1,50, porque el agua de Peñol turbina en Guatapé, Playas y San Carlos. El pipeline comprueba en cada corrida que el factor de un embalse nunca es menor que el de un embalse aguas abajo.

**Franjas mensuales.** Para cada embalse y mes, con E = energía útil:

- Bajo el NEP = NEP × E (reserva que no se debería usar).
- Banda flexible = (NPV − NEP) × E.
- Sobre el NPV = (1 − NPV) × E (por encima, riesgo de vertimiento).

Se asume factor de conversión constante con el nivel, la misma convención de PARATEC.

**Horas a potencia.** Energía útil × 1.000 ÷ suma de la capacidad efectiva neta de las plantas que turbinan esa agua, sin contar aportes. Es un orden de magnitud: supone todas las plantas a plena carga, y en la práctica el agua de un embalse sale al ritmo de la primera planta aguas abajo.

**Nivel diario.** Es el volumen útil como porcentaje de la capacidad útil, tal como lo publica XM (métrica `PorcVoluUtilDiar`); XM no publica la cota en m.s.n.m. El nivel de una cadena es su energía almacenada sobre su capacidad útil, ambas sumadas en GWh. La referencia de cada gráfica es la banda NEP–NPV del mes; para una cadena o el SIN se pondera por la energía útil de PARATEC.

## Supuestos vigentes

- NEP = NPV = 0 todo el año se interpreta como "no declarado" (caso Ituango).
- "Cadena antigua" del río Bogotá = Charquito, El Limonar, Tequendama 1 a 4, Laguneta, Salto II y Darío Valencia Samper: agrupación nuestra de los recursos de XM.
- Régimen por días a potencia: 60 o más multianual, 10 a 60 estacional, menos de 10 semanal o diario.

## Capacidad efectiva neta por planta

Potencia de cada planta según XM (métrica `CapEfecNeta`, último dato publicado). Cada planta se asocia a sus códigos de recurso XM en `config/cadenas.yaml`. Cuando XM publica varias plantas como un solo recurso (GUATRON, PAGUA, ALBAN), la capacidad se asigna a la primera. Si una planta no tiene dato de XM, se usa una potencia aproximada de `config/supuestos.yaml` y aparece aquí como "supuesto".

```js
Inputs.table(capacidad, {
  columns: ["planta", "recursos_xm", "potencia_mw", "fuente", "incluida_en", "fecha_xm"],
  header: {planta: "Planta", recursos_xm: "Recursos XM", potencia_mw: "Capacidad (MW)", fuente: "Fuente", incluida_en: "Incluida en", fecha_xm: "Fecha XM"},
  format: {potencia_mw: (d) => num(d, 1), fecha_xm: (d) => (d ? d.toISOString().slice(0, 10) : "")},
  rows: 30
})
```

## Advertencias de la validación

Inconsistencias encontradas en la fuente. No se corrigen: se publican tal como vienen y se señalan aquí.

```js
Inputs.table(validacion, {
  columns: ["objeto", "regla", "detalle"],
  header: {objeto: "Embalse", regla: "Regla", detalle: "Detalle"},
  rows: 20
})
```
