import * as Plot from "npm:@observablehq/plot";
import * as d3 from "npm:d3";
import {num} from "./formato.js";

const diaAnio = (d) => d3.utcDay.count(d3.utcYear(d), d) + 1;
export const fechaCO = d3.utcFormat("%d/%m/%Y");

/** Une cada fecha de la serie con la banda histórica de su día del año. */
export function conBanda(serie, rango, valor) {
  const porDia = new Map(rango.map((r) => [r.dia_anio, r]));
  return serie.map((d) => {
    const r = porDia.get(diaAnio(d.fecha)) ?? {};
    return {fecha: d.fecha, valor: d[valor], p10: r.p10, p50: r.p50, p90: r.p90, minimo: r.minimo, maximo: r.maximo};
  });
}

/** Nivel diario (% del volumen útil) con la banda histórica del mismo día del año. */
export function graficaNivel(datos, {width, height = 300, titulo = "Nivel", anios} = {}) {
  const ultimo = datos.at(-1);
  return Plot.plot({
    width,
    height,
    marginLeft: 44,
    marginRight: 70,
    x: {type: "utc", label: null},
    y: {label: "% del volumen útil", grid: true, domain: [0, Math.max(100, d3.max(datos, (d) => d.valor) ?? 100)]},
    marks: [
      Plot.areaY(datos, {x: "fecha", y1: "minimo", y2: "maximo", fill: "var(--theme-foreground-faint)", fillOpacity: 0.15}),
      Plot.areaY(datos, {x: "fecha", y1: "p10", y2: "p90", fill: "var(--theme-blue)", fillOpacity: 0.15}),
      Plot.lineY(datos, {x: "fecha", y: "p50", stroke: "var(--theme-blue)", strokeOpacity: 0.6, strokeDasharray: "4 3"}),
      Plot.lineY(datos, {x: "fecha", y: "valor", stroke: "var(--theme-foreground)", strokeWidth: 2}),
      ultimo ? Plot.dot([ultimo], {x: "fecha", y: "valor", r: 4, fill: "var(--theme-foreground)"}) : null,
      ultimo ? Plot.text([ultimo], {x: "fecha", y: "valor", text: (d) => `${num(d.valor, 1)} %`, dx: 8, textAnchor: "start", fontWeight: "bold"}) : null,
      Plot.ruleY([0]),
      Plot.tip(datos, Plot.pointerX({
        x: "fecha", y: "valor",
        title: (d) => `${fechaCO(d.fecha)}\n${titulo}: ${num(d.valor, 1)} %\nMediana histórica: ${num(d.p50, 1)} %\nRango usual (p10–p90): ${num(d.p10, 0)}–${num(d.p90, 0)} %`
      }))
    ],
    caption: anios ? `Línea negra: dato diario de XM. Banda azul: rango usual (percentiles 10 a 90) del mismo día del año en ${anios} años anteriores; gris: mínimo y máximo; punteada: mediana.` : null
  });
}

/** Cada embalse hoy frente a su rango usual para esta fecha. */
export function graficaEmbalsesHoy(filas, {width} = {}) {
  return Plot.plot({
    width,
    height: 28 * filas.length + 50,
    marginLeft: 190,
    marginRight: 60,
    x: {label: "% del volumen útil", domain: [0, 100], grid: true},
    y: {label: null, domain: d3.sort(filas, (d) => d.valor).map((d) => d.embalse)},
    color: {domain: ["Bajo lo usual", "Dentro de lo usual", "Sobre lo usual"], range: ["#c0392b", "#7f8c8d", "#2b7bb9"], legend: true},
    marks: [
      Plot.barX(filas, {y: "embalse", x1: "p10", x2: "p90", fill: "var(--theme-foreground-faint)", fillOpacity: 0.35, insetTop: 6, insetBottom: 6}),
      Plot.tickX(filas, {y: "embalse", x: "p50", stroke: "var(--theme-foreground-muted)", insetTop: 6, insetBottom: 6}),
      Plot.dot(filas, {y: "embalse", x: "valor", r: 5, fill: (d) => d.valor < d.p10 ? "Bajo lo usual" : d.valor > d.p90 ? "Sobre lo usual" : "Dentro de lo usual"}),
      Plot.text(filas, {y: "embalse", x: "valor", text: (d) => `${num(d.valor, 0)} %`, dx: 10, textAnchor: "start", fontSize: 11}),
      Plot.tip(filas, Plot.pointerY({y: "embalse", x: "valor", title: (d) => `${d.embalse}\nHoy: ${num(d.valor, 1)} %\nRango usual: ${num(d.p10, 0)}–${num(d.p90, 0)} %\nMediana: ${num(d.p50, 0)} %`}))
    ]
  });
}

/** Fila "hoy" por serie: valor más reciente + banda de su día del año. */
export function hoyFrenteAlRango(ultimos, rango, clave, valor) {
  const idx = d3.group(rango, (r) => r[clave]);
  return ultimos.map((u) => {
    const r = (idx.get(u[clave]) ?? []).find((x) => x.dia_anio === diaAnio(u.fecha)) ?? {};
    return {...u, valor: u[valor], p10: r.p10, p50: r.p50, p90: r.p90};
  });
}
