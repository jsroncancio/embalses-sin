import * as d3 from "npm:d3";

// Formato numérico colombiano: punto para miles, coma para decimales.
export const localeCO = d3.formatLocale({decimal: ",", thousands: ".", grouping: [3], currency: ["$", ""]});

export const num = (d, decimales = 0) =>
  d == null || Number.isNaN(d) ? "–" : localeCO.format(`,.${decimales}f`)(d);

export const MESES = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"];

// Colores de los límites, iguales en todas las gráficas del sitio.
export const COLORES = {bajo: "#c0392b", banda: "#2b7bb9", sobre: "#d68910"};

// Componentes de la energía útil en un mes (suman el total).
export const COMPONENTES = [
  {clave: "energia_bajo_nep_gwh", nombre: "Bajo el NEP (reserva)", color: COLORES.bajo},
  {clave: "banda_nep_npv_gwh", nombre: "Banda NEP–NPV (flexible)", color: COLORES.banda},
  {clave: "energia_sobre_npv_gwh", nombre: "Sobre el NPV (cerca de verter)", color: COLORES.sobre}
];
