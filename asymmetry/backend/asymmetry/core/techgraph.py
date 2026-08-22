"""Technology graph and second-order opportunity discovery (sections 37, 38).

The premise: when a trend is obvious, the obvious way to express it is crowded
and therefore expensive. The interesting position is usually several layers
upstream, in something unglamorous that the trend cannot proceed without.

    AI demand
      -> data centres
        -> electrical power
          -> grid capacity
            -> high-voltage transformers
              -> grain-oriented electrical steel
                -> specialty steel processing

Layer 1 is priced by everyone. Layer 6 is priced by almost nobody, and it is a
hard physical bottleneck. This module makes that traversal explicit and
searchable rather than leaving it to an agent's imagination.

Depth is the operative signal: **the further a node sits from the driver, the
less of the narrative is in its price** - which is the entire premise of a
second-order search.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from typing import Any, Iterable


@dataclass
class TechNode:
    """A node in the dependency graph.

    ``requires`` is the important edge: it points at what this technology
    consumes, and therefore at the bottlenecks that constrain it.
    """

    name: str
    category: str
    description: str = ""
    requires: list[str] = field(default_factory=list)   # upstream dependencies
    maturity: str = "emerging"      # research | emerging | scaling | mature
    bottleneck: bool = False        # a known physical or capacity constraint
    search_terms: list[str] = field(default_factory=list)

    def queries(self) -> list[str]:
        return self.search_terms or [self.name]


#: A starting graph. Deliberately opinionated about where the real constraints
#: sit, and deliberately incomplete - section 39 exists precisely because any
#: hand-built map has blind spots.
DEFAULT_GRAPH: list[TechNode] = [
    # ---- Drivers: the crowded, obvious layer -----------------------------
    TechNode("AI compute demand", "driver", "Training and inference growth.",
             requires=["AI accelerators", "data centre capacity"], maturity="scaling"),
    TechNode("Electrification", "driver", "Transport and industrial electrification.",
             requires=["grid capacity", "battery cells"], maturity="scaling"),
    TechNode("Defence modernisation", "driver", "Autonomy, sensing, munitions restock.",
             requires=["radiation-hardened electronics", "energetic materials",
                       "precision optics"], maturity="scaling"),
    TechNode("Reshoring of manufacturing", "driver", "Supply-chain relocation.",
             requires=["industrial automation", "machine tools", "grid capacity"],
             maturity="scaling"),

    # ---- Second layer ----------------------------------------------------
    TechNode("AI accelerators", "compute", "GPUs, ASICs, accelerators.",
             requires=["advanced packaging", "HBM memory", "leading-edge lithography"],
             maturity="scaling"),
    TechNode("data centre capacity", "infrastructure", "Halls, power, cooling.",
             requires=["electrical power", "thermal management", "construction capacity"],
             maturity="scaling"),
    TechNode("battery cells", "energy", "Cells for vehicles and storage.",
             requires=["cathode materials", "lithium refining", "separator film"],
             maturity="scaling"),

    # ---- Third layer: where crowding starts to thin ----------------------
    TechNode("electrical power", "energy", "Generation and delivery.",
             requires=["grid capacity", "generation capacity"], maturity="mature"),
    TechNode("thermal management", "infrastructure", "Liquid and immersion cooling.",
             requires=["heat exchangers", "dielectric fluids", "precision machining"],
             maturity="emerging",
             search_terms=["data centre liquid cooling", "immersion cooling",
                           "direct-to-chip cooling"]),
    TechNode("advanced packaging", "semiconductors", "2.5D/3D integration, CoWoS.",
             requires=["precision bonding equipment", "substrate materials",
                       "semiconductor metrology"], maturity="scaling",
             search_terms=["advanced semiconductor packaging", "hybrid bonding",
                           "glass substrate packaging"]),

    # ---- Fourth layer: the genuine bottlenecks ---------------------------
    TechNode("grid capacity", "infrastructure",
             "Transmission and distribution. Multi-year replacement backlog.",
             requires=["high-voltage transformers", "switchgear", "conductor cable"],
             maturity="mature", bottleneck=True,
             search_terms=["grid interconnection queue", "transmission upgrade",
                           "distribution transformer shortage"]),
    TechNode("semiconductor metrology", "semiconductors",
             "Inspection and measurement. Gates every process node.",
             requires=["precision optics", "electron optics"], maturity="scaling",
             bottleneck=True,
             search_terms=["e-beam inspection", "semiconductor metrology",
                           "wafer inspection"]),
    TechNode("cathode materials", "materials", "NMC, LFP, precursors.",
             requires=["rare-earth and critical-mineral processing",
                       "nickel refining"], maturity="scaling"),

    # ---- Fifth layer: almost entirely unpriced ---------------------------
    TechNode("high-voltage transformers", "electrical",
             "Large power transformers. Multi-year lead times, few suppliers.",
             requires=["grain-oriented electrical steel", "bushings and insulation"],
             maturity="mature", bottleneck=True,
             search_terms=["large power transformer manufacturing",
                           "phase shifting transformer", "transformer lead time"]),
    TechNode("precision optics", "materials", "Optical elements to sub-nm tolerance.",
             requires=["optical glass", "ultra-precision polishing"],
             maturity="mature", bottleneck=True),
    TechNode("rare-earth and critical-mineral processing", "materials",
             "Separation and refining. Concentrated in few jurisdictions.",
             requires=["solvent extraction capacity", "separation chemistry"],
             maturity="scaling", bottleneck=True,
             search_terms=["rare earth separation", "critical mineral refining",
                           "solvent extraction rare earth"]),

    # ---- Sixth layer: the far end ----------------------------------------
    TechNode("grain-oriented electrical steel", "materials",
             "Specialty steel for transformer cores. Very few producers.",
             requires=["specialty steel processing"], maturity="mature",
             bottleneck=True,
             search_terms=["grain oriented electrical steel",
                           "transformer core steel", "amorphous metal core"]),
    TechNode("separator film", "materials", "Battery separator film. Capital intensive.",
             requires=["precision film extrusion"], maturity="scaling", bottleneck=True),
    TechNode("HBM memory", "semiconductors", "High-bandwidth memory stacks.",
             requires=["advanced packaging", "DRAM capacity"], maturity="scaling",
             bottleneck=True),
]


class TechGraph:
    """Traversable dependency graph."""

    def __init__(self, nodes: Iterable[TechNode] | None = None) -> None:
        self.nodes: dict[str, TechNode] = {}
        for n in nodes if nodes is not None else DEFAULT_GRAPH:
            self.nodes[n.name.lower()] = n

    def get(self, name: str) -> TechNode | None:
        return self.nodes.get(name.lower())

    def add(self, node: TechNode) -> None:
        self.nodes[node.name.lower()] = node

    def chain_from(self, driver: str, max_depth: int = 6) -> list[list[str]]:
        """Every dependency path downstream of ``driver``.

        Cycle-safe: a node already on the current path is not revisited, so a
        mutually-dependent pair cannot produce an infinite chain.
        """
        start = self.get(driver)
        if start is None:
            return []

        chains: list[list[str]] = []

        def walk(node: TechNode, path: list[str]) -> None:
            if len(path) >= max_depth:
                chains.append(path)
                return
            unresolved = [
                r for r in node.requires
                if self.get(r) is not None and r.lower() not in {p.lower() for p in path}
            ]
            if not unresolved:
                chains.append(path)
                return
            for req in unresolved:
                child = self.get(req)
                assert child is not None
                walk(child, path + [child.name])

        walk(start, [start.name])
        return chains

    def depth_of(self, name: str, drivers: list[str] | None = None) -> int | None:
        """Shortest distance from any driver. Higher means less obvious.

        Breadth-first, so the answer is the *shortest* path: a node reachable in
        two hops is priced as a two-hop play even if it also sits six hops down
        some other chain.
        """
        target = self.get(name)
        if target is None:
            return None
        driver_names = drivers or [n.name for n in self.nodes.values() if n.category == "driver"]

        best: int | None = None
        for d in driver_names:
            start = self.get(d)
            if start is None:
                continue
            queue: deque[tuple[TechNode, int]] = deque([(start, 0)])
            seen = {start.name.lower()}
            while queue:
                node, depth = queue.popleft()
                if node.name.lower() == target.name.lower():
                    best = depth if best is None else min(best, depth)
                    break
                for req in node.requires:
                    child = self.get(req)
                    if child and child.name.lower() not in seen:
                        seen.add(child.name.lower())
                        queue.append((child, depth + 1))
        return best

    def second_order_targets(self, driver: str, min_depth: int = 2) -> list[dict[str, Any]]:
        """Nodes far enough from the driver to be plausibly unpriced.

        Ranked by depth, then by whether the node is a known bottleneck. A deep
        node that is *also* a physical constraint is the archetype this whole
        module exists to surface: demand cannot route around it, and nobody is
        talking about it.
        """
        start = self.get(driver)
        if start is None:
            return []

        out: list[dict[str, Any]] = []
        for chain in self.chain_from(driver):
            for depth, name in enumerate(chain):
                if depth < min_depth:
                    continue
                node = self.get(name)
                if node is None or any(o["name"] == node.name for o in out):
                    continue
                out.append({
                    "name": node.name,
                    "category": node.category,
                    "description": node.description,
                    "depth": depth,
                    "is_bottleneck": node.bottleneck,
                    "maturity": node.maturity,
                    "chain": chain[: depth + 1],
                    "queries": node.queries(),
                    "rationale": (
                        f"{depth} steps upstream of {start.name}"
                        + (" and a known capacity bottleneck" if node.bottleneck else "")
                        + ". Demand reaches it indirectly, so the narrative is less "
                          "likely to be reflected in its price."
                    ),
                })

        out.sort(key=lambda o: (-o["depth"], not o["is_bottleneck"]))
        return out

    def bottlenecks(self) -> list[TechNode]:
        return [n for n in self.nodes.values() if n.bottleneck]

    def discovery_queries(self, driver: str, limit: int = 24) -> list[str]:
        """Search queries aimed at the unglamorous end of a chain."""
        queries: list[str] = []
        for target in self.second_order_targets(driver):
            for q in target["queries"]:
                for suffix in ("small public company", "manufacturing capacity",
                               "supply shortage lead time"):
                    candidate = f"{q} {suffix}"
                    if candidate not in queries:
                        queries.append(candidate)
                if len(queries) >= limit:
                    return queries[:limit]
        return queries[:limit]

    def to_dict(self) -> dict[str, Any]:
        return {
            "nodes": [
                {"name": n.name, "category": n.category, "description": n.description,
                 "requires": n.requires, "maturity": n.maturity,
                 "is_bottleneck": n.bottleneck,
                 "depth": self.depth_of(n.name)}
                for n in self.nodes.values()
            ],
            "drivers": [n.name for n in self.nodes.values() if n.category == "driver"],
            "bottlenecks": [n.name for n in self.bottlenecks()],
        }
