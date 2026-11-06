import * as Plot from "npm:@observablehq/plot";
import * as d3 from "npm:d3";
import {num} from "./formato.js";

export const fechaCO = d3.utcFormat("%d/%m/%Y");
const mesDe = (d) => d.getUTCMonth() + 1;

export const ESTADOS = {
  bajo: {nombre: "Bajo el NEP (reserva)", color: "#c0392b"},
  banda: {nombre: "En la banda NEP–NPV", color: "#2b7bb9"},
  alto: {nombre: "Sobre el NPV (cerca de verter)", color: "#d68910"}
};

export function estado(valor, nep, npv) {
  if (valor == null || nep == null) return null;
  return valor < nep ? "bajo" : valor > npv ? "alto" : "banda";
}

/** Añade a cada día el NEP y NPV de su mes. `ref`: filas {mes, nep_pct, npv_pct}. */
export function conReferencia(serie, ref, valor = "pct_util") {
  const porMes = new Map(ref.map((r) => [r.mes, r]));
  return serie.map((d) => {
    const r = porMes.get(mesDe(d.fecha)) ?? {};
    return {...d, valor: d[valor], nep: r.nep_pct, npv: r.npv_pct};
  });
}

/** Nivel diario (% del volumen útil) sobre la banda NEP–NPV del mes. */
export function graficaNivel(datos, {width, height = 280, titulo = "Nivel"} = {}) {
  const ultimo = datos.at(-1);
  const hayRef = datos.some((d) => d.nep != null);
  return Plot.plot({
    width,
    height,
    marginLeft: 44,
    marginRight: 64,
    x: {type: "utc", label: null},
    y: {label: "% del volumen útil", grid: true, domain: [0, Math.max(100, d3.max(datos, (d) => d.valor) ?? 100)]},
    marks: [
      hayRef ? Plot.areaY(datos, {x: "fecha", y1: "nep", y2: "npv", fill: ESTADOS.banda.color, fillOpacity: 0.12, curve: "step"}) : null,
      hayRef ? Plot.lineY(datos, {x: "fecha", y: "nep", stroke: ESTADOS.bajo.color, strokeWidth: 1, strokeDasharray: "4 3", curve: "step"}) : null,
      hayRef ? Plot.lineY(datos, {x: "fecha", y: "npv", stroke: ESTADOS.alto.color, strokeWidth: 1, strokeDasharray: "4 3", curve: "step"}) : null,
      Plot.lineY(datos, {x: "fecha", y: "valor", stroke: "var(--theme-foreground)", strokeWidth: 1.75}),
      ultimo ? Plot.dot([ultimo], {x: "fecha", y: "valor", r: 4, fill: "var(--theme-foreground)"}) : null,
      ultimo ? Plot.text([ultimo], {x: "fecha", y: "valor", text: (d) => `${num(d.valor, 1)} %`, dx: 8, textAnchor: "start", fontWeight: "bold"}) : null,
      Plot.ruleY([0]),
      Plot.tip(datos, Plot.pointerX({
        x: "fecha", y: "valor",
        title: (d) => `${fechaCO(d.fecha)}\n${titulo}: ${num(d.valor, 1)} %` + (d.nep != null ? `\nNEP ${num(d.nep, 0)} % · NPV ${num(d.npv, 0)} %` : "")
      }))
    ]
  });
}

/** Cada embalse hoy frente a la banda NEP–NPV de este mes. */
export function graficaEmbalsesHoy(filas, {width} = {}) {
  const conRef = filas.filter((d) => d.nep != null);
  return Plot.plot({
    width,
    height: 26 * filas.length + 60,
    marginLeft: 200,
    marginRight: 56,
    x: {label: "% del volumen útil", domain: [0, Math.max(100, d3.max(filas, (d) => d.valor))], grid: true},
    y: {label: null, domain: d3.sort(filas, (d) => d.valor).map((d) => d.embalse)},
    color: {domain: Object.values(ESTADOS).map((e) => e.nombre), range: Object.values(ESTADOS).map((e) => e.color), legend: true},
    marks: [
      Plot.barX(conRef, {y: "embalse", x1: "nep", x2: "npv", fill: ESTADOS.banda.color, fillOpacity: 0.15, insetTop: 5, insetBottom: 5}),
      Plot.dot(filas, {y: "embalse", x: "valor", r: 5, fill: (d) => ESTADOS[estado(d.valor, d.nep, d.npv)]?.nombre ?? "gray"}),
      Plot.text(filas, {y: "embalse", x: "valor", text: (d) => `${num(d.valor, 0)} %`, dx: 10, textAnchor: "start", fontSize: 11}),
      Plot.tip(filas, Plot.pointerY({
        y: "embalse", x: "valor",
        title: (d) => `${d.embalse}\nHoy: ${num(d.valor, 1)} %` + (d.nep != null ? `\nBanda del mes: ${num(d.nep, 0)}–${num(d.npv, 0)} %` : "\nSin NEP/NPV declarados")
      }))
    ]
  });
}

/** Último dato de cada embalse con el NEP/NPV de su mes. */
export function embalsesHoy(ultimos, ref) {
  const idx = new Map(ref.filter((r) => r.tipo === "embalse").map((r) => [`${r.id}|${r.mes}`, r]));
  return ultimos.map((u) => {
    const r = idx.get(`${u.serie_xm}|${mesDe(u.fecha)}`) ?? {};
    return {...u, valor: u.pct_util, nep: r.nep_pct, npv: r.npv_pct};
  });
}
