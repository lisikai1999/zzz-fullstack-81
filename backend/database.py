import sqlite3
import json
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "kol_sim.db")


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_conn()
    cur = conn.cursor()
    cur.executescript("""
        CREATE TABLE IF NOT EXISTS networks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            node_count INTEGER NOT NULL,
            edge_count INTEGER NOT NULL,
            kol_ids TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS nodes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            network_id INTEGER NOT NULL,
            node_id INTEGER NOT NULL,
            degree INTEGER DEFAULT 0,
            community INTEGER DEFAULT 0,
            is_kol INTEGER DEFAULT 0,
            label TEXT,
            FOREIGN KEY (network_id) REFERENCES networks(id)
        );
        CREATE TABLE IF NOT EXISTS edges (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            network_id INTEGER NOT NULL,
            source INTEGER NOT NULL,
            target INTEGER NOT NULL,
            FOREIGN KEY (network_id) REFERENCES networks(id)
        );
        CREATE TABLE IF NOT EXISTS simulations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            network_id INTEGER NOT NULL,
            seed_ids TEXT NOT NULL,
            spread_prob REAL DEFAULT 0.1,
            steps INTEGER DEFAULT 10,
            num_runs INTEGER DEFAULT 100,
            avg_reach REAL,
            reach_curve TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (network_id) REFERENCES networks(id)
        );
    """)
    conn.commit()
    conn.close()
