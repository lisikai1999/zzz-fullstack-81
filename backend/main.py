from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import json
import networkx as nx

from database import init_db, get_conn
from simulation import (
    generate_network,
    simulate_spread,
    simulate_single_run,
    compute_overlap_matrix,
    greedy_seed_selection,
    get_community_stats,
)

app = FastAPI(title="KOL Spread Simulator")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

_graphs = {}


def _load_graph(network_id: int) -> nx.Graph:
    if network_id in _graphs:
        return _graphs[network_id]
    conn = get_conn()
    nodes = conn.execute("SELECT node_id, community, is_kol FROM nodes WHERE network_id=?", (network_id,)).fetchall()
    edges = conn.execute("SELECT source, target FROM edges WHERE network_id=?", (network_id,)).fetchall()
    conn.close()
    if not nodes:
        raise HTTPException(404, "Network not found")
    G = nx.Graph()
    for n in nodes:
        G.add_node(n["node_id"], community=n["community"], is_kol=bool(n["is_kol"]))
    for e in edges:
        G.add_edge(e["source"], e["target"])
    _graphs[network_id] = G
    return G


@app.on_event("startup")
def startup():
    init_db()


class NetworkCreateRequest(BaseModel):
    name: str = "Default Network"
    node_count: int = 500
    kol_count: int = 20
    m: int = 3
    seed: Optional[int] = 42


@app.post("/api/networks")
def create_network(req: NetworkCreateRequest):
    G, kol_ids, partition = generate_network(req.node_count, req.kol_count, req.m, req.seed)

    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO networks (name, node_count, edge_count, kol_ids) VALUES (?,?,?,?)",
        (req.name, G.number_of_nodes(), G.number_of_edges(), json.dumps(kol_ids)),
    )
    network_id = cur.lastrowid

    node_rows = []
    for node_id in G.nodes():
        node_rows.append((network_id, node_id, G.degree(node_id), partition[node_id], int(node_id in kol_ids), f"User_{node_id}"))
    cur.executemany("INSERT INTO nodes (network_id, node_id, degree, community, is_kol, label) VALUES (?,?,?,?,?,?)", node_rows)

    edge_rows = [(network_id, u, v) for u, v in G.edges()]
    cur.executemany("INSERT INTO edges (network_id, source, target) VALUES (?,?,?)", edge_rows)

    conn.commit()
    conn.close()

    _graphs[network_id] = G

    return {"network_id": network_id, "node_count": G.number_of_nodes(), "edge_count": G.number_of_edges(), "kol_ids": kol_ids}


@app.get("/api/networks")
def list_networks():
    conn = get_conn()
    rows = conn.execute("SELECT id, name, node_count, edge_count, kol_ids, created_at FROM networks ORDER BY id DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]


@app.get("/api/networks/{network_id}")
def get_network(network_id: int):
    conn = get_conn()
    net = conn.execute("SELECT * FROM networks WHERE id=?", (network_id,)).fetchone()
    if not net:
        conn.close()
        raise HTTPException(404, "Network not found")
    nodes = conn.execute("SELECT node_id, degree, community, is_kol, label FROM nodes WHERE network_id=?", (network_id,)).fetchall()
    edges = conn.execute("SELECT source, target FROM edges WHERE network_id=?", (network_id,)).fetchall()
    conn.close()
    return {
        "id": net["id"],
        "name": net["name"],
        "node_count": net["node_count"],
        "edge_count": net["edge_count"],
        "kol_ids": json.loads(net["kol_ids"]),
        "nodes": [dict(n) for n in nodes],
        "edges": [dict(e) for e in edges],
    }


class SimulateRequest(BaseModel):
    seed_ids: List[int]
    spread_prob: float = 0.1
    steps: int = 10
    num_runs: int = 100


@app.post("/api/networks/{network_id}/simulate")
def run_simulation(network_id: int, req: SimulateRequest):
    G = _load_graph(network_id)
    for s in req.seed_ids:
        if s not in G:
            raise HTTPException(400, f"Node {s} not in network")

    avg_reach, reach_curve = simulate_spread(G, req.seed_ids, req.spread_prob, req.steps, req.num_runs)

    conn = get_conn()
    conn.execute(
        "INSERT INTO simulations (network_id, seed_ids, spread_prob, steps, num_runs, avg_reach, reach_curve) VALUES (?,?,?,?,?,?,?)",
        (network_id, json.dumps(req.seed_ids), req.spread_prob, req.steps, req.num_runs, avg_reach, json.dumps(reach_curve)),
    )
    conn.commit()
    conn.close()

    return {"avg_reach": avg_reach, "reach_curve": reach_curve, "seed_ids": req.seed_ids}


@app.post("/api/networks/{network_id}/simulate_single")
def run_single_simulation(network_id: int, req: SimulateRequest):
    """Run a single simulation for animation purposes, returning step-by-step activations."""
    G = _load_graph(network_id)
    for s in req.seed_ids:
        if s not in G:
            raise HTTPException(400, f"Node {s} not in network")

    history = simulate_single_run(G, req.seed_ids, req.spread_prob, req.steps)
    return {"history": history, "total_reached": sum(len(step) for step in history)}


class CompareRequest(BaseModel):
    combinations: List[List[int]]
    spread_prob: float = 0.1
    steps: int = 10
    num_runs: int = 100


@app.post("/api/networks/{network_id}/compare")
def compare_combinations(network_id: int, req: CompareRequest):
    G = _load_graph(network_id)
    results = []
    for combo in req.combinations:
        for s in combo:
            if s not in G:
                raise HTTPException(400, f"Node {s} not in network")
        avg_reach, reach_curve = simulate_spread(G, combo, req.spread_prob, req.steps, req.num_runs)
        results.append({"seed_ids": combo, "avg_reach": avg_reach, "reach_curve": reach_curve})
    return {"results": results}


@app.get("/api/networks/{network_id}/overlap")
def get_overlap(network_id: int):
    G = _load_graph(network_id)
    conn = get_conn()
    net = conn.execute("SELECT kol_ids FROM networks WHERE id=?", (network_id,)).fetchone()
    conn.close()
    kol_ids = json.loads(net["kol_ids"])
    matrix = compute_overlap_matrix(G, kol_ids)
    return {"kol_ids": kol_ids, "overlap_matrix": matrix}


class OptimizeRequest(BaseModel):
    k: int = 5
    spread_prob: float = 0.1
    steps: int = 10
    num_runs: int = 50


@app.post("/api/networks/{network_id}/optimize")
def optimize_seeds(network_id: int, req: OptimizeRequest):
    G = _load_graph(network_id)
    conn = get_conn()
    net = conn.execute("SELECT kol_ids FROM networks WHERE id=?", (network_id,)).fetchone()
    conn.close()
    kol_ids = json.loads(net["kol_ids"])
    selected = greedy_seed_selection(G, kol_ids, req.k, req.spread_prob, req.steps, req.num_runs)
    avg_reach, reach_curve = simulate_spread(G, selected, req.spread_prob, req.steps, req.num_runs)
    return {"selected_seeds": selected, "avg_reach": avg_reach, "reach_curve": reach_curve}


@app.get("/api/networks/{network_id}/communities")
def get_communities(network_id: int):
    G = _load_graph(network_id)
    partition = nx.get_node_attributes(G, "community")
    stats = get_community_stats(G, partition)
    return {"communities": stats}


@app.get("/api/networks/{network_id}/graph_layout")
def get_graph_layout(network_id: int):
    """Get node positions using spring layout for visualization."""
    G = _load_graph(network_id)
    pos = nx.spring_layout(G, k=0.5, iterations=50, seed=42)
    nodes_data = []
    for node_id in G.nodes():
        x, y = pos[node_id]
        nodes_data.append({
            "id": node_id,
            "x": float(x) * 500 + 500,
            "y": float(y) * 500 + 500,
            "degree": G.degree(node_id),
            "community": G.nodes[node_id].get("community", 0),
            "is_kol": G.nodes[node_id].get("is_kol", False),
        })
    edges_data = [{"source": u, "target": v} for u, v in G.edges()]
    return {"nodes": nodes_data, "edges": edges_data}
