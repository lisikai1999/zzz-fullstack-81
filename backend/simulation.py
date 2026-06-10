import networkx as nx
import community as community_louvain
import numpy as np
import random
from itertools import combinations


def generate_network(node_count=500, kol_count=20, m=3, seed=None):
    """Generate a scale-free network using Barabási-Albert model with KOL designation."""
    if seed is not None:
        random.seed(seed)
        np.random.seed(seed)

    G = nx.barabasi_albert_graph(node_count, m, seed=seed)

    degrees = sorted(G.degree(), key=lambda x: x[1], reverse=True)
    kol_ids = [node_id for node_id, _ in degrees[:kol_count]]

    partition = community_louvain.best_partition(G, random_state=seed or 42)
    nx.set_node_attributes(G, partition, "community")

    for node_id in G.nodes():
        G.nodes[node_id]["is_kol"] = node_id in kol_ids

    return G, kol_ids, partition


def independent_cascade(G, seeds, prob=0.1, steps=10):
    """Run one Independent Cascade simulation and return activation history per step."""
    activated = set(seeds)
    history = [list(seeds)]
    newly_activated = set(seeds)

    for step in range(steps):
        next_activated = set()
        for node in newly_activated:
            for neighbor in G.neighbors(node):
                if neighbor not in activated:
                    if random.random() < prob:
                        next_activated.add(neighbor)
        if not next_activated:
            break
        activated.update(next_activated)
        newly_activated = next_activated
        history.append(list(next_activated))

    return activated, history


def simulate_spread(G, seeds, prob=0.1, steps=10, num_runs=100):
    """Run multiple IC simulations and return average reach curve."""
    all_reach_curves = []

    for _ in range(num_runs):
        _, history = independent_cascade(G, seeds, prob, steps)
        curve = []
        total = 0
        for step_nodes in history:
            total += len(step_nodes)
            curve.append(total)
        while len(curve) < steps + 1:
            curve.append(curve[-1])
        all_reach_curves.append(curve)

    avg_curve = np.mean(all_reach_curves, axis=0).tolist()
    avg_reach = avg_curve[-1]
    return avg_reach, avg_curve


def simulate_single_run(G, seeds, prob=0.1, steps=10):
    """Run a single IC simulation returning full activation detail per step."""
    activated, history = independent_cascade(G, seeds, prob, steps)
    return history


def compute_overlap(G, kol_a, kol_b):
    """Compute follower overlap between two KOLs (shared neighbors)."""
    neighbors_a = set(G.neighbors(kol_a))
    neighbors_b = set(G.neighbors(kol_b))
    shared = neighbors_a & neighbors_b
    union = neighbors_a | neighbors_b
    if not union:
        return 0.0, 0
    jaccard = len(shared) / len(union)
    return jaccard, len(shared)


def compute_overlap_matrix(G, kol_ids):
    """Compute pairwise overlap matrix for a set of KOLs."""
    n = len(kol_ids)
    matrix = [[0.0] * n for _ in range(n)]
    for i in range(n):
        for j in range(i + 1, n):
            jaccard, _ = compute_overlap(G, kol_ids[i], kol_ids[j])
            matrix[i][j] = jaccard
            matrix[j][i] = jaccard
        matrix[i][i] = 1.0
    return matrix


def greedy_seed_selection(G, candidates, k=5, prob=0.1, steps=10, num_runs=50):
    """Greedy submodular maximization to select k seeds maximizing expected spread."""
    selected = []
    remaining = set(candidates)

    for _ in range(k):
        best_node = None
        best_marginal = -1

        for node in remaining:
            test_seeds = selected + [node]
            reach, _ = simulate_spread(G, test_seeds, prob, steps, num_runs)
            marginal = reach
            if marginal > best_marginal:
                best_marginal = marginal
                best_node = node

        if best_node is not None:
            selected.append(best_node)
            remaining.remove(best_node)

    return selected


def get_community_stats(G, partition):
    """Analyze community structure: sizes, inter-community edges, bridge nodes."""
    communities = {}
    for node, comm_id in partition.items():
        communities.setdefault(comm_id, []).append(node)

    stats = []
    for comm_id, members in communities.items():
        subgraph = G.subgraph(members)
        internal_edges = subgraph.number_of_edges()

        external_edges = 0
        bridge_nodes = set()
        for node in members:
            for neighbor in G.neighbors(node):
                if partition[neighbor] != comm_id:
                    external_edges += 1
                    bridge_nodes.add(node)

        stats.append({
            "community_id": comm_id,
            "size": len(members),
            "internal_edges": internal_edges,
            "external_edges": external_edges // 2,
            "bridge_nodes": list(bridge_nodes)[:10],
            "bridge_count": len(bridge_nodes),
        })

    return sorted(stats, key=lambda x: x["size"], reverse=True)
