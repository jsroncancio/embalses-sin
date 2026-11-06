import {readFileSync} from "node:fs";

const topologia = JSON.parse(readFileSync(new URL("./src/data/topologia.json", import.meta.url), "utf-8"));

export default {
  title: "Embalses del SIN",
  root: "src",
  lang: "es",
  pages: [
    {
      name: "Cadenas",
      pages: topologia.map((c) => ({name: c.nombre, path: `/cadenas/${c.id}`}))
    },
    {name: "Metodología y fuentes", path: "/metodologia"}
  ],
  dynamicPaths: topologia.map((c) => `/cadenas/${c.id}`),
  head: '<link rel="icon" href="data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 100 100%22><text y=%22.9em%22 font-size=%2290%22>💧</text></svg>">',
  footer:
    "Datos: XM (PARATEC). Código MIT, datos derivados CC BY 4.0. " +
    '<a href="https://github.com/jsroncancio/embalses-sin">Repositorio</a>.',
  toc: true,
  search: true
};
