"""Topología de las cadenas: carga del YAML, grafo y disposición para dibujar."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import networkx as nx
import yaml


@dataclass
class Cadena:
    id: str
    nombre: str
    tipo: str
    region: str
    rios: list[str]
    diagrama: str
    grafo: nx.DiGraph
    notas: list[str] = field(default_factory=list)

    def nodos(self, tipo: str | None = None) -> list[str]:
        return [n for n, d in self.grafo.nodes(data=True) if tipo is None or d["tipo"] == tipo]

    def embalses(self) -> list[str]:
        return self.nodos("embalse")

    def plantas(self) -> list[str]:
        return self.nodos("planta")

    def plantas_aguas_abajo(self, nodo: str) -> list[str]:
        """Plantas que turbinan el agua que sale de `nodo` (en orden topológico)."""
        alcanzables = nx.descendants(self.grafo, nodo)
        orden = list(nx.topological_sort(self.grafo))
        return [n for n in orden if n in alcanzables and self.grafo.nodes[n]["tipo"] == "planta"]

    def embalses_aguas_abajo(self, nodo: str) -> list[str]:
        alcanzables = nx.descendants(self.grafo, nodo)
        return [n for n in alcanzables if self.grafo.nodes[n]["tipo"] == "embalse"]


def cargar_cadenas(ruta: Path) -> list[Cadena]:
    datos = yaml.safe_load(Path(ruta).read_text(encoding="utf-8"))
    cadenas = []
    for c in datos["cadenas"]:
        g = nx.DiGraph()
        for n in c["nodos"]:
            g.add_node(n["id"], **{k: v for k, v in n.items() if k != "id"})
        for origen, destino in c["aristas"]:
            g.add_edge(origen, destino)
        cadenas.append(
            Cadena(
                id=c["id"],
                nombre=c["nombre"],
                tipo=c["tipo"],
                region=c["region"],
                rios=c.get("rios", []),
                diagrama=c.get("diagrama", ""),
                grafo=g,
                notas=c.get("notas", []),
            )
        )
    return cadenas


def disposicion(cadena: Cadena) -> dict[str, tuple[int, int]]:
    """Coordenadas (capa, fila) por nodo: capa = distancia más larga desde una fuente.

    Es una disposición determinista y simple para dibujar el flujo de izquierda
    a derecha sin depender de librerías de dibujo de grafos.
    """
    g = cadena.grafo
    capa: dict[str, int] = {}
    for n in nx.topological_sort(g):
        preds = list(g.predecessors(n))
        capa[n] = 0 if not preds else max(capa[p] for p in preds) + 1
    # Cada nodo se corre lo más a la derecha posible (justo antes de su primer
    # sucesor) para que los ramales laterales tengan aristas cortas.
    for n in reversed(list(nx.topological_sort(g))):
        succ = list(g.successors(n))
        if succ:
            capa[n] = min(capa[s] for s in succ) - 1

    # Fila 0 = camino más largo (eje principal). El resto se ubica cerca de
    # sus vecinos ya ubicados, en la fila libre más cercana.
    filas: dict[str, int] = {n: 0 for n in nx.dag_longest_path(g)}
    ocupado = {(capa[n], 0) for n in filas}
    orden_yaml = {n: i for i, n in enumerate(g.nodes)}
    pendientes = sorted((n for n in g.nodes if n not in filas), key=orden_yaml.get)
    while pendientes:
        con_vecino = [n for n in pendientes if any(v in filas for v in nx.all_neighbors(g, n))] or pendientes[:1]
        n = con_vecino[0]
        vecinos = [filas[v] for v in nx.all_neighbors(g, n) if v in filas]
        deseada = round(sum(vecinos) / len(vecinos)) if vecinos else 0
        fila = next(f for d in range(50) for f in (deseada + d, deseada - d) if f >= 0 and (capa[n], f) not in ocupado)
        filas[n] = fila
        ocupado.add((capa[n], fila))
        pendientes.remove(n)
    return {n: (capa[n], filas[n]) for n in g.nodes}
