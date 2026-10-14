#!/usr/bin/env python3
"""Inspect and probe a PUBLISHED C. elegans connectome as a research experiment.

Input schema: OpenWorm CElegansNeuroML/herm_full_edgelist.csv
https://github.com/openworm/CElegansNeuroML

This is a deterministic graph probe, NOT a biophysical neuron simulator or an
intelligence module. It never contacts Claude and has no model-token usage.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path

COLUMNS = {"Source", "Target", "Weight", "Type"}
MAX_FILE_BYTES = 5_000_000
MAX_EDGES = 50_000


def load_connectome(path: Path) -> tuple[list[tuple[str, str, int, str]], str]:
    if not path.is_file():
        raise ValueError(f"Datei nicht vorhanden: {path}")
    if path.stat().st_size > MAX_FILE_BYTES:
        raise ValueError("CSV zu gross fuer diesen kleinen Forschungslauf")
    raw = path.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    edges: list[tuple[str, str, int, str]] = []
    with path.open("r", encoding="utf-8-sig", newline="") as inp:
        reader = csv.DictReader(inp)
        if not reader.fieldnames or not COLUMNS.issubset(reader.fieldnames):
            raise ValueError(f"CSV-Spalten fehlen: {sorted(COLUMNS)}")
        for i, row in enumerate(reader, start=2):
            if len(edges) >= MAX_EDGES:
                raise ValueError("Zu viele Kanten, Limit erreicht")
            a, b = (row.get("Source") or "").strip(), (row.get("Target") or "").strip()
            kind = (row.get("Type") or "").strip().lower()
            if not a or not b or len(a) > 80 or len(b) > 80 or not kind:
                raise ValueError(f"Ungueltige Knoten/Kantentyp in Zeile {i}")
            try:
                weight = int((row.get("Weight") or "").strip())
            except ValueError as exc:
                raise ValueError(f"Ungueltiges Gewicht in Zeile {i}") from exc
            if weight <= 0 or weight > 1_000_000:
                raise ValueError(f"Gewicht ausserhalb des Limits in Zeile {i}")
            edges.append((a, b, weight, kind))
    if not edges:
        raise ValueError("Leerer Connectome-Datensatz")
    return edges, digest


def profile(edges: list[tuple[str, str, int, str]], digest: str) -> dict:
    nodes = {n for a, b, *_ in edges for n in (a, b)}
    kinds = Counter(kind for *_, kind in edges)
    return {"source_sha256": digest, "nodes": len(nodes), "edges": len(edges),
            "edge_types": dict(sorted(kinds.items())),
            "warning": "Connectome/Verbindungsdaten, keine rekonstruierte Intelligenz"}


def probe(edges: list[tuple[str, str, int, str]], source: str, steps: int = 3,
          decay: float = 0.7) -> dict:
    """Simple *non-biophysical* weighted directed graph diffusion.

    No invented language-to-neuron mapping, and no claims of brain behavior.
    """
    if not 1 <= steps <= 8:
        raise ValueError("steps muss 1 bis 8 sein")
    if not 0 < decay <= 1:
        raise ValueError("decay muss (0,1] sein")
    if source not in {n for a, b, *_ in edges for n in (a, b)}:
        raise ValueError(f"Knoten nicht gefunden: {source}")
    outgoing: dict[str, list[tuple[str, int]]] = defaultdict(list)
    for a, b, weight, _ in edges:
        outgoing[a].append((b, weight))
    state = {source: 1.0}
    for _ in range(steps):
        next_state: dict[str, float] = defaultdict(float)
        for a, activation in state.items():
            targets = outgoing.get(a, [])
            total = sum(weight for _, weight in targets)
            if total:
                for b, weight in targets:
                    next_state[b] += decay * activation * (weight / total)
        state = dict(next_state)
    top = sorted(state.items(), key=lambda pair: (-pair[1], pair[0]))[:10]
    return {"input_neuron": source, "steps": steps,
            "top_reached": [{"neuron": n, "graph_signal": round(v, 7)} for n, v in top],
            "note": "Deterministische Graphdiffusion auf realen Kanten; KEINE biologisch validierte Neuronenaktivitaet und keine Claude-Handlungsauswahl"}


def main() -> int:
    parser = argparse.ArgumentParser(description="OpenWorm-Connectome-Forschung ohne LLM")
    parser.add_argument("--csv", type=Path, required=True)
    parser.add_argument("--probe", metavar="NEURON", help="Optional: Graphsignal von diesem Neuron aus")
    parser.add_argument("--steps", type=int, default=3)
    args = parser.parse_args()
    try:
        edges, digest = load_connectome(args.csv)
        result = profile(edges, digest)
        if args.probe:
            result["probe"] = probe(edges, args.probe, args.steps)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (ValueError, OSError, csv.Error) as exc:
        parser.exit(2, f"openworm_connectome: {exc}\n")


if __name__ == "__main__":
    raise SystemExit(main())
