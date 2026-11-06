import {svg} from "npm:htl";
import {num} from "./formato.js";

const COL = 216; // ancho de cada capa
const FILA = 84; // alto de cada fila
const W = 184; // ancho de nodo
const H = 54; // alto de nodo

const ESTILO = {
  embalse: {fill: "var(--theme-blue)", fillOpacity: 0.14, stroke: "var(--theme-blue)"},
  planta: {fill: "var(--theme-foreground-focus)", fillOpacity: 0.1, stroke: "var(--theme-foreground-focus)"},
  rio: {fill: "none", stroke: "var(--theme-foreground-faint)"},
  desviacion: {fill: "none", stroke: "var(--theme-foreground-faint)"},
  uso: {fill: "none", stroke: "var(--theme-foreground-faint)"}
};

function subtitulo(n) {
  if (n.tipo === "embalse") return `${num(n.energia_util_gwh)} GWh · ${num(n.vol_util_mm3)} Mm³`;
  if (n.tipo === "planta") {
    const p = n.potencia_mw_supuesto != null ? `${num(n.potencia_mw_supuesto)} MW*` : "";
    return n.filo_de_agua ? `filo de agua ${p}`.trim() : p;
  }
  return {rio: "río / aporte", desviacion: "desviación", uso: "uso de agua"}[n.tipo];
}

function recortar(texto, max = 22) {
  return texto.length > max ? texto.slice(0, max - 1) + "…" : texto;
}

/** Dibuja la cadena de izquierda a derecha a partir de topologia.json. */
export function diagramaCadena(cadena) {
  const capas = Math.max(...cadena.nodos.map((n) => n.capa)) + 1;
  const filas = Math.max(...cadena.nodos.map((n) => n.fila)) + 1;
  const ancho = capas * COL + 24;
  const alto = filas * FILA + 24;
  const pos = new Map(cadena.nodos.map((n) => [n.id, {x: 12 + n.capa * COL, y: 12 + n.fila * FILA + (FILA - H) / 2}]));

  const aristas = cadena.aristas.map(({de, a}) => {
    const p = pos.get(de), q = pos.get(a);
    const x1 = p.x + W, y1 = p.y + H / 2, x2 = q.x - 4, y2 = q.y + H / 2;
    const mx = (x1 + x2) / 2;
    return svg`<path d="M${x1},${y1} C${mx},${y1} ${mx},${y2} ${x2},${y2}" fill="none" stroke="var(--theme-foreground-muted)" stroke-width="1.25" marker-end="url(#flecha)"></path>`;
  });

  const nodos = cadena.nodos.map((n) => {
    const {x, y} = pos.get(n.id);
    const e = ESTILO[n.tipo];
    const discontinuo = n.tipo !== "embalse" && n.tipo !== "planta" ? "4 3" : null;
    return svg`<g>
      <title>${n.nombre}\n${subtitulo(n)}${n.factor_gwh_mm3 ? `\nFactor acumulado ${num(n.factor_gwh_mm3, 4)} GWh/Mm³` : ""}</title>
      <rect x=${x} y=${y} width=${W} height=${H} rx="8" fill=${e.fill} fill-opacity=${e.fillOpacity ?? 1} stroke=${e.stroke} stroke-width=${n.tipo === "embalse" ? 1.75 : 1.25} stroke-dasharray=${discontinuo}></rect>
      <text x=${x + W / 2} y=${y + 22} text-anchor="middle" font-size="13" font-weight="600" fill="var(--theme-foreground)">${recortar(n.nombre)}</text>
      <text x=${x + W / 2} y=${y + 40} text-anchor="middle" font-size="11.5" fill="var(--theme-foreground-muted)">${subtitulo(n)}</text>
    </g>`;
  });

  return svg`<svg viewBox="0 0 ${ancho} ${alto}" width=${ancho} style="max-width:100%;height:auto;font-family:var(--sans-serif)">
    <defs><marker id="flecha" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0 0L10 5L0 10z" fill="var(--theme-foreground-muted)"></path></marker></defs>
    ${aristas}${nodos}
  </svg>`;
}
