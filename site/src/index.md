---
title: Embalses del SIN como batería
toc: false
---

```js
import {num, MESES, COMPONENTES} from "./components/formato.js";
import {feature} from "npm:topojson-client";
import {conReferencia, graficaNivel, graficaEmbalsesHoy, embalsesHoy, estado, ESTADOS, fechaCO, fechaLarga} from "./components/nivel.js";

const cadenas = FileAttachment("data/cadenas.csv").csv({typed: true});
const embalses = FileAttachment("data/embalses.csv").csv({typed: true});
const mensual = FileAttachment("data/cadenas_mensual.csv").csv({typed: true});
const fuentes = FileAttachment("data/fuentes.json").json();
const sistema = FileAttachment("data/xm_sistema_diario.csv").csv({typed: true});
const referencia = FileAttachment("data/xm_referencia_nep_npv.csv").csv({typed: true});
const ultimosEmb = FileAttachment("data/xm_embalses_ultimo.csv").csv({typed: true});
const mundo = fetch(import.meta.resolve("npm:world-atlas/countries-50m.json")).then((r) => r.json());
```

# Embalses del SIN como batería hidroeléctrica

<div class="card fecha-datos">
  <span class="muted">Datos de XM disponibles al</span><br>
  <span class="fecha-grande">${fechaLarga(sistema.at(-1).fecha)}</span><br>
  <span class="muted">Se actualizan cada día a las 8:30 a. m. (hora de Colombia) con el último dato que publica XM. Capacidad y curvas NEP–NPV: PARATEC, reporte del ${fuentes.paratec.fecha_reporte}.</span>
</div>

<style>
.fecha-datos {border-left: 4px solid var(--theme-blue);}
.fecha-grande {font-size: 2.2rem; font-weight: 700; line-height: 1.3;}
</style>

```js
const total = d3.sum(cadenas, (d) => d.energia_util_gwh);
const volumen = d3.sum(cadenas, (d) => d.vol_util_mm3);
const bandaMes = d3.rollups(mensual, (v) => d3.sum(v, (d) => d.banda_nep_npv_gwh), (d) => d.mes).sort((a, b) => a[0] - b[0]);
const [mesMin, bandaMin] = d3.least(bandaMes, (d) => d[1]);
const [mesMax, bandaMax] = d3.greatest(bandaMes, (d) => d[1]);
```

## Cómo están hoy los embalses

```js
const datosSIN = conReferencia(sistema, referencia.filter((r) => r.tipo === "sistema"));
const hoySIN = datosSIN.at(-1);
const filasHoy = embalsesHoy(ultimosEmb, referencia);
const conteo = d3.rollup(filasHoy, (v) => v.length, (d) => estado(d.valor, d.nep, d.npv));
```

<div class="grid grid-cols-3">
  <div class="card"><h2>Nivel del SIN</h2><span class="big">${num(hoySIN.valor, 1)} %</span><br><span class="muted">del volumen útil al ${fechaCO(hoySIN.fecha)}</span></div>
  <div class="card"><h2>Energía almacenada</h2><span class="big">${num(hoySIN.energia_gwh)} GWh</span><br><span class="muted">de ${num(hoySIN.capacidad_gwh)} GWh de capacidad útil</span></div>
  <div class="card"><h2>Embalses bajo el NEP</h2><span class="big">${conteo.get("bajo") ?? 0}</span><br><span class="muted">${conteo.get("alto") ?? 0} sobre el NPV, de ${filasHoy.length} series</span></div>
</div>

<div class="card">

```js
display(graficaNivel(datosSIN, {width, titulo: "SIN"}));
```

<p class="muted">Línea negra: nivel diario publicado por XM. Franja azul: banda NEP–NPV del mes (PARATEC), ponderada por energía útil. Por debajo del NEP (línea roja) el sistema está en reserva; por encima del NPV (línea naranja), cerca de verter.</p>
</div>

<div class="card">
<h2>Cada embalse hoy frente a su banda del mes</h2>

```js
display(graficaEmbalsesHoy(filasHoy, {width}));
```

<p class="muted">Punto: nivel de hoy. Franja azul: banda NEP–NPV del mes. Raya roja: NEP. Raya naranja: NPV. La distancia del punto a cada raya muestra qué tan cerca está el embalse de cada límite. Cuando un embalse declara el mismo valor para NEP y NPV (como Playas en varios meses), la banda tiene ancho cero y las dos rayas quedan juntas; si son casi iguales (como Esmeralda), la franja es muy delgada. Ituango no tiene NEP ni NPV declarados, por eso no tiene banda ni rayas (punto gris). Sisga, Tominé y Neusa se publican juntos en XM como agregado Bogotá.</p>
</div>

## Capacidad declarada

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
  columns: ["cadena", "tipo", "n_embalses", "energia_util_gwh", "pct_energia_sin", "vol_util_mm3", "banda_min_gwh", "mes_banda_min", "potencia_regulada_mw", "horas_a_potencia"],
  header: {
    cadena: "Cadena", tipo: "Tipo", n_embalses: "Embalses", energia_util_gwh: "Energía útil (GWh)", pct_energia_sin: "% del SIN",
    vol_util_mm3: "Vol. útil (Mm³)", banda_min_gwh: "Banda mín. (GWh)", mes_banda_min: "Mes", potencia_regulada_mw: "Potencia (MW)", horas_a_potencia: "Horas a potencia"
  },
  format: {
    cadena: (d, i) => htl.html`<a href="./cadenas/${cadenas[i].cadena_id}">${d}</a>`,
    energia_util_gwh: (d) => num(d), pct_energia_sin: (d) => num(d, 1), vol_util_mm3: (d) => num(d), banda_min_gwh: (d) => num(d),
    potencia_regulada_mw: (d) => num(d), horas_a_potencia: (d) => num(d)
  },
  sort: "energia_util_gwh", reverse: true, rows: 14
})
```

<p class="muted">Potencia: capacidad efectiva neta de XM de las plantas que turbinan el agua de la cadena, al ${fuentes.capacidad.fecha}. Horas a potencia = energía útil ÷ potencia de las plantas que turbinan esa agua, sin aportes.</p>
