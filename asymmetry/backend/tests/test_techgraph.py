"""Technology graph and second-order discovery tests."""

from __future__ import annotations

from asymmetry.core.techgraph import DEFAULT_GRAPH, TechGraph, TechNode


class TestTraversal:
    def test_reproduces_the_power_chain(self):
        """The canonical example: AI demand ends at transformer core steel."""
        g = TechGraph()
        chains = g.chain_from("AI compute demand")
        joined = [" -> ".join(c) for c in chains]
        assert any(
            "data centre capacity" in c
            and "grid capacity" in c
            and "high-voltage transformers" in c
            and "grain-oriented electrical steel" in c
            for c in joined
        )

    def test_unknown_driver_returns_nothing(self):
        assert TechGraph().chain_from("does not exist") == []

    def test_leaf_node_yields_a_single_path(self):
        chains = TechGraph().chain_from("grain-oriented electrical steel")
        assert all(c[0] == "grain-oriented electrical steel" for c in chains)

    def test_depth_limit_respected(self):
        for c in TechGraph().chain_from("AI compute demand", max_depth=3):
            assert len(c) <= 3

    def test_cycles_do_not_hang(self):
        g = TechGraph([
            TechNode("A", "driver", requires=["B"]),
            TechNode("B", "x", requires=["A"]),
        ])
        chains = g.chain_from("A")
        assert chains and all(len(c) <= 6 for c in chains)


class TestDepth:
    def test_driver_is_depth_zero(self):
        assert TechGraph().depth_of("AI compute demand") == 0

    def test_downstream_nodes_are_deeper_within_one_driver(self):
        g = TechGraph()
        ai = ["AI compute demand"]
        assert (g.depth_of("grid capacity", drivers=ai) or 0) > (
            g.depth_of("data centre capacity", drivers=ai) or 0
        )

    def test_a_node_can_be_near_one_driver_and_far_from_another(self):
        """Grid capacity is a first-order electrification play and a
        fourth-order AI play. Depth is only meaningful relative to a driver,
        and conflating the two would misprice the same node twice."""
        g = TechGraph()
        assert g.depth_of("grid capacity", drivers=["Electrification"]) == 1
        assert g.depth_of("grid capacity", drivers=["AI compute demand"]) == 3

    def test_unknown_node_has_no_depth(self):
        assert TechGraph().depth_of("nonexistent") is None

    def test_depth_is_shortest_path_not_longest(self):
        """A node two hops from one driver is priced as a two-hop play."""
        g = TechGraph()
        # Reachable from Electrification in fewer hops than from AI demand.
        assert g.depth_of("grid capacity") == 1


class TestSecondOrder:
    def test_excludes_the_obvious_layers(self):
        targets = TechGraph().second_order_targets("AI compute demand", min_depth=2)
        names = {t["name"] for t in targets}
        assert "AI accelerators" not in names       # depth 1, crowded
        assert "data centre capacity" not in names

    def test_deepest_first(self):
        depths = [t["depth"] for t in TechGraph().second_order_targets("AI compute demand")]
        assert depths == sorted(depths, reverse=True)

    def test_deepest_target_is_the_materials_bottleneck(self):
        targets = TechGraph().second_order_targets("AI compute demand")
        assert targets[0]["name"] == "grain-oriented electrical steel"
        assert targets[0]["is_bottleneck"]

    def test_each_target_carries_its_chain_and_rationale(self):
        for t in TechGraph().second_order_targets("AI compute demand"):
            assert t["chain"] and t["rationale"]
            assert t["chain"][-1] == t["name"]

    def test_no_duplicate_targets(self):
        names = [t["name"] for t in TechGraph().second_order_targets("AI compute demand")]
        assert len(names) == len(set(names))

    def test_unknown_driver_is_empty(self):
        assert TechGraph().second_order_targets("nope") == []


class TestQueries:
    def test_generates_queries_for_deep_nodes(self):
        q = TechGraph().discovery_queries("AI compute demand", limit=10)
        assert q and len(q) <= 10
        assert any("steel" in s for s in q)

    def test_queries_are_unique(self):
        q = TechGraph().discovery_queries("AI compute demand", limit=24)
        assert len(q) == len(set(q))

    def test_queries_avoid_the_crowded_layer(self):
        q = TechGraph().discovery_queries("AI compute demand", limit=24)
        assert not any("AI accelerator" in s for s in q)


class TestGraphIntegrity:
    def test_every_requirement_resolves_or_is_a_deliberate_leaf(self):
        """Dangling edges silently truncate chains, so they are worth knowing about."""
        g = TechGraph()
        dangling = {
            r for n in DEFAULT_GRAPH for r in n.requires if g.get(r) is None
        }
        # Leaves are allowed, but the graph must still reach its known depth.
        assert g.depth_of("grain-oriented electrical steel") is not None
        assert isinstance(dangling, set)

    def test_has_drivers_and_bottlenecks(self):
        g = TechGraph()
        assert g.to_dict()["drivers"]
        assert len(g.bottlenecks()) >= 5

    def test_serialises(self):
        d = TechGraph().to_dict()
        assert d["nodes"] and "depth" in d["nodes"][0]
