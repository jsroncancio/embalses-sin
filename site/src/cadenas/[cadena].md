```js
import {num, MESES, COMPONENTES} from "../components/formato.js";
import {diagramaCadena} from "../components/topologia.js";
import {conReferencia, graficaNivel, graficaEmbalsesHoy, embalsesHoy, fechaCO} from "../components/nivel.js";

const id = observable.params.cadena;
const topologia = FileAttachment("../data/topologia.json").json();
const todas = FileAttachment("../data/cadenas.csv").csv({typed: true});
const todosEmbalses = FileAttachment("../data/embalses.csv").csv({typed: true});
const todoMensual = FileAttachment("../data/cadenas_mensual.csv").csv({typed: true});
const todoNep = FileAttachment("../data/nep_npv_mensual.csv").csv({typed: true});
const validacion = FileAttachment("../data/validacion.csv").csv({typed: true});
const xmCadenas = FileAttachment("../data/xm_cadenas_diario.csv").csv({typed: true});
const xmEmbalses = FileAttachment("../data/xm_embalses_diario.csv").csv({typed: true});
const referencia = FileAttachment("../data/xm_referencia_nep_npv.csv").csv({typed: true});
const xmUltimos = FileAttachment("../data/xm_embalses_ultimo.csv").csv({typed: true});
```

```js
const topo = topologia.find((d) => d.id === id);
const resumen = todas.find((d) => d.cadena_id === id);
const embalses = todosEmbalses.filter((d) => d.cadena_id === id);
const mensual = todoMensual.filter((d) => d.cadena_id === id);
const nep = todoNep.filter((d) => d.cadena_id === id);
const avisos = validacion.filter((d) => embalses.some((e) => e.embalse === d.objeto || e.nodo_id === d.objeto));
```

# ${resumen.cadena}

<p class="muted">${resumen.tipo === "serie" ? "Cadena en serie" : "Embalse aislado"} · ${resumen.region} · ríos ${resumen.rios}</p>

<div class="grid grid-cols-4">
  <div class="card"><h2>Energía útil</h2><span class="big">${num(resumen.energia_util_gwh)} GWh</span><br><span class="muted">${num(resumen.pct_energia_sin, 1)} % del SIN</span></div>
  <div class="card"><h2>Volumen útil</h2><span class="big">${num(resumen.vol_util_mm3)} Mm³</span><br><span class="muted">${resumen.n_embalses} embalses, ${resumen.n_plantas} plantas</span></div>
  <div class="card"><h2>Banda flexible</h2><span class="big">${num(resumen.banda_min_gwh)}–${num(resumen.banda_max_gwh)} GWh</span><br><span class="muted">mín. en ${resumen.mes_banda_min}, máx. en ${resumen.mes_banda_max}</span></div>
  <div class="card"><h2>Horas a potencia*</h2><span class="big">${num(resumen.horas_a_potencia_supuesto)} h</span><br><span class="muted">con ${num(resumen.potencia_regulada_mw_supuesto)} MW*</span></div>
</div>

## Nivel diario

```js
const serieCadena = xmCadenas.filter((d) => d.cadena_id === id);
const datosCadena = conReferencia(serieCadena, referencia.filter((r) => r.tipo === "cadena" && r.id === id));
const hoyCadena = datosCadena.at(-1);
const ultimosCadena = xmUltimos.filter((d) => d.cadena_id === id);
```

<p>Al ${fechaCO(hoyCadena.fecha)} la cadena tiene <b>${num(hoyCadena.energia_gwh)} GWh</b> almacenados, el <b>${num(hoyCadena.valor, 1)} %</b> de su capacidad útil${hoyCadena.nep != null ? html`. La banda NEP–NPV de este mes va de ${num(hoyCadena.nep, 0)} % a ${num(hoyCadena.npv, 0)} %` : ""}.</p>

<div class="card">

```js
display(graficaNivel(datosCadena, {width, titulo: resumen.cadena}));
```

</div>

```js
if (ultimosCadena.length > 1) {
  display(html`<h3>Por embalse</h3>`);
  display(graficaEmbalsesHoy(embalsesHoy(ultimosCadena, referencia), {width}));
  for (const u of ultimosCadena) {
    const datos = conReferencia(xmEmbalses.filter((d) => d.serie_xm === u.serie_xm), referencia.filter((r) => r.tipo === "embalse" && r.id === u.serie_xm));
    display(html`<h4>${u.embalse}</h4>`);
    display(graficaNivel(datos, {width, height: 200, titulo: u.embalse}));
  }
}
```

## Cómo fluye el agua

```js
display(diagramaCadena(topo));
```

<p class="muted">Azul: embalse (energía útil y volumen útil de PARATEC). Gris: planta. Borde discontinuo: ríos, desviaciones y usos de agua. Pase el cursor por un embalse para ver su factor de conversión acumulado. Fuente del diagrama: ${resumen.diagrama_fuente}.</p>

${topo.notas.length ? html`<ul>${topo.notas.map((n) => html`<li>${n}</li>`)}</ul>` : ""}

## Energía disponible mes a mes

```js
const largo = mensual.flatMap((d) => COMPONENTES.map((c) => ({mes: d.mes, franja: c.nombre, gwh: d[c.clave] ?? 0})));
display(Plot.plot({
  width,
  height: 280,
  marginLeft: 60,
  x: {label: null, tickFormat: (m) => MESES[m - 1], ticks: 12},
  y: {label: "GWh", grid: true, tickFormat: (d) => num(d)},
  color: {domain: COMPONENTES.map((c) => c.nombre), range: COMPONENTES.map((c) => c.color), legend: true},
  marks: [
    Plot.areaY(largo, {x: "mes", y: "gwh", fill: "franja", order: COMPONENTES.map((c) => c.nombre), curve: "step", tip: {format: {y: (d) => `${num(d)} GWh`, x: (m) => MESES[m - 1]}}}),
    Plot.ruleY([0])
  ]
}));
```

${resumen.nep_incompleto ? html`<p class="warning">Algún embalse de esta cadena no tiene NEP ni NPV declarados en PARATEC; su energía no aparece en el gráfico.</p>` : ""}

## Embalses

```js
Inputs.table(embalses, {
  columns: ["embalse", "operador", "vol_util_mm3", "energia_util_gwh", "factor_gwh_mm3", "nivel_min_tecnico_msnm", "nivel_max_fisico_msnm", "plantas_aguas_abajo", "dias_a_potencia_supuesto", "regimen_supuesto"],
  header: {
    embalse: "Embalse", operador: "Operador", vol_util_mm3: "Vol. útil (Mm³)", energia_util_gwh: "Energía útil (GWh)", factor_gwh_mm3: "Factor (GWh/Mm³)",
    nivel_min_tecnico_msnm: "Nivel mín. técnico (msnm)", nivel_max_fisico_msnm: "Nivel máx. físico (msnm)", plantas_aguas_abajo: "Plantas aguas abajo",
    dias_a_potencia_supuesto: "Días a potencia*", regimen_supuesto: "Régimen*"
  },
  format: {
    vol_util_mm3: (d) => num(d, 1), energia_util_gwh: (d) => num(d, 1), factor_gwh_mm3: (d) => num(d, 4),
    nivel_min_tecnico_msnm: (d) => num(d, 1), nivel_max_fisico_msnm: (d) => num(d, 1), dias_a_potencia_supuesto: (d) => num(d, 1)
  }
})
```

${avisos.length ? html`<h2>Advertencias de datos</h2><ul>${avisos.map((a) => html`<li><b>${a.objeto}:</b> ${a.detalle}</li>`)}</ul>` : ""}

<p class="muted">* Supuesto: potencias aproximadas, pendientes de la capacidad efectiva neta de XM. Régimen por días a potencia: 60 o más multianual, 10 a 60 estacional, menos de 10 semanal o diario.</p>
