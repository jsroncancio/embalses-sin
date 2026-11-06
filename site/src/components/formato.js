import * as d3 from "npm:d3";

// Formato numérico colombiano: punto para miles, coma para decimales.
export const localeCO = d3.formatLocale({decimal: ",", thousands: ".", grouping: [3], currency: ["$", ""]});

export const num = (d, decimales = 0) =>
  d == null || Number.isNaN(d) ? "–" : localeCO.format(`,.${decimales}f`)(d);

export const MESES = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"];

// Componentes de la energía útil en un mes (suman el total).
export const COMPONENTES = [
  {clave: "energia_bajo_nep_gwh", nombre: "Bajo NEP (reserva)", color: "#9aa5b1"},
  {clave: "banda_nep_npv_gwh", nombre: "Banda NEP–NPV (flexible)", color: "#2b7bb9"},
  {clave: "energia_sobre_npv_gwh", nombre: "Sobre NPV", color: "#e0b04c"}
];
