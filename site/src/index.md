---
title: Embalses del SIN como batería
toc: false
---

```js
import {num, MESES, COMPONENTES} from "./components/formato.js";
import {feature} from "npm:topojson-client";

const cadenas = FileAttachment("data/cadenas.csv").csv({typed: true});
const embalses = FileAttachment("data/embalses.csv").csv({typed: true});
const mensual = FileAttachment("data/cadenas_mensual.csv").csv({typed: true});
const fuentes = FileAttachment("data/fuentes.json").json();
const mundo = fetch(import.meta.resolve("npm:world-atlas/countries-50m.json")).then((r) => r.json());
```

# Embalses del SIN como batería hidroeléctrica

```js
const total = d3.sum(cadenas, (d) => d.energia_util_gwh);
const volumen = d3.sum(cadenas, (d) => d.vol_util_mm3);
const bandaMes = d3.rollups(mensual, (v) => d3.sum(v, (d) => d.banda_nep_npv_gwh), (d) => d.mes).sort((a, b) => a[0] - b[0]);
const [mesMin, bandaMin] = d3.least(bandaMes, (d) => d[1]);
const [mesMax, bandaMax] = d3.greatest(bandaMes, (d) => d[1]);
```

<p class="muted">Capacidad declarada en PARATEC (XM), reporte del ${fuentes.paratec.fecha_reporte}. ${embalses.length} embalses individuales en ${cadenas.length} cadenas o sistemas.</p>

<div class="grid grid-cols-4">
  <div class="card"><h2>Energía útil almacenable</h2><span class="big">${num(total)} GWh</span></div>
  <div class="card"><h2>Volumen útil</h2><span class="big">${num(volumen)} Mm³</span></div>
  <div class="card"><h2>Banda flexible mínima</h2><span class="big">${num(bandaMin)} GWh</span><br><span class="muted">en ${MESES[mesMin - 1]}</span></div>
  <div class="card"><h2>Banda flexible máxima</h2><span class="big">${num(bandaMax)} GWh</span><br><span class="muted">en ${MESES[mesMax - 1]}</span></div>
</div>

## Cuánta de esa energía se puede mover cada mes

La energía útil se reparte en tres franjas según las curvas NEP y NPV que declara cada embalse. Solo la franja del medio es flexible para respaldar solar y eólica sin poner en riesgo la confiabilidad ni provocar vertimientos.

```js
const largo = mensual.flatMap((d) => COMPONENTES.map((c) => ({mes: d.mes, franja: c.nombre, gwh: d[c.clave] ?? 0})));
const porMes = d3.flatRollup(largo, (v) => d3.sum(v, (d) => d.gwh), (d) => d.mes, (d) => d.franja).map(([mes, franja, gwh]) => ({mes, franja, gwh}));
```

```js
display(Plot.plot({
  width,
  height: 320,
  marginLeft: 60,
  x: {label: null, tickFormat: (m) => MESES[m - 1], ticks: 12},
  y: {label: "GWh", grid: true, tickFormat: (d) => num(d)},
  color: {domain: COMPONENTES.map((c) => c.nombre), range: COMPONENTES.map((c) => c.color), legend: true},
  marks: [
    Plot.areaY(porMes, {x: "mes", y: "gwh", fill: "franja", order: COMPONENTES.map((c) => c.nombre), curve: "step", tip: {format: {y: (d) => `${num(d)} GWh`, x: (m) => MESES[m - 1]}}}),
    Plot.ruleY([0])
  ]
}));
```

<p class="muted">Ituango no tiene NEP ni NPV declarados: su energía no aparece en este gráfico. Ver <a href="./metodologia">metodología</a>.</p>

## Dónde está la energía

```js
const colombia = feature(mundo, mundo.objects.countries).features.filter((f) => ["Colombia", "Venezuela", "Ecuador", "Panama", "Peru", "Brazil"].includes(f.properties.name));
const nombreCadena = new Map(cadenas.map((d) => [d.cadena_id, d.cadena]));
```

<div class="grid grid-cols-2">
<div class="card">

```js
display(Plot.plot({
  width: Math.min(width / 2, 520),
  height: 600,
  projection: {type: "mercator", domain: {type: "MultiPoint", coordinates: [[-79.5, -1.5], [-71.5, 11.5]]}},
  r: {range: [2, 26]},
  marks: [
    Plot.geo(colombia, {fill: (f) => f.properties.name === "Colombia" ? "var(--theme-background-alt)" : "none", stroke: "var(--theme-foreground-faint)"}),
    Plot.dot(embalses, {x: "longitud", y: "latitud", r: "energia_util_gwh", fill: "var(--theme-blue)", fillOpacity: 0.35, stroke: "var(--theme-blue)",
      channels: {Embalse: "embalse", Cadena: (d) => nombreCadena.get(d.cadena_id), "Energía útil": (d) => `${num(d.energia_util_gwh)} GWh`},
      tip: {format: {x: false, y: false, r: false}}})
  ]
}));
```

</div>
<div class="card">

```js
display(Plot.plot({
  width: Math.min(width / 2, 520),
  height: 600,
  marginLeft: 210,
  x: {label: "Energía útil (GWh)", grid: true, tickFormat: (d) => num(d)},
  y: {label: null},
  marks: [
    Plot.barX(cadenas, {y: "cadena", x: "energia_util_gwh", sort: {y: "-x"}, fill: "var(--theme-blue)", href: (d) => `./cadenas/${d.cadena_id}`,
      tip: {format: {x: (d) => `${num(d)} GWh`}}}),
    Plot.ruleX([0])
  ]
}));
```

</div>
</div>

## Las 13 cadenas

```js
Inputs.table(cadenas, {
  columns: ["cadena", "tipo", "n_embalses", "energia_util_gwh", "pct_energia_sin", "vol_util_mm3", "banda_min_gwh", "mes_banda_min", "potencia_regulada_mw_supuesto", "horas_a_potencia_supuesto"],
  header: {
    cadena: "Cadena", tipo: "Tipo", n_embalses: "Embalses", energia_util_gwh: "Energía útil (GWh)", pct_energia_sin: "% del SIN",
    vol_util_mm3: "Vol. útil (Mm³)", banda_min_gwh: "Banda mín. (GWh)", mes_banda_min: "Mes", potencia_regulada_mw_supuesto: "Potencia* (MW)", horas_a_potencia_supuesto: "Horas a potencia*"
  },
  format: {
    cadena: (d, i) => htl.html`<a href="./cadenas/${cadenas[i].cadena_id}">${d}</a>`,
    energia_util_gwh: (d) => num(d), pct_energia_sin: (d) => num(d, 1), vol_util_mm3: (d) => num(d), banda_min_gwh: (d) => num(d),
    potencia_regulada_mw_supuesto: (d) => num(d), horas_a_potencia_supuesto: (d) => num(d)
  },
  sort: "energia_util_gwh", reverse: true, rows: 14
})
```

<p class="muted">* Supuesto: potencias aproximadas, pendientes de reemplazar por la capacidad efectiva neta de XM (fase 2). Horas a potencia = energía útil ÷ potencia de las plantas que turbinan esa agua, sin aportes.</p>
