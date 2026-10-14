#!/usr/bin/env python3
"""OPTIONAL real NengoSPA neural action-selection demo, NOT production routing.

Requires independently installed, compatible `nengo` and `nengo-spa`.
Based on documented spa.ActionSelection / ifmax / basal-ganglia-thalamus API.
Research-only: Nengo utility inputs come from external code, not language.
"""
from __future__ import annotations

import argparse
import json
import sys

ACTIONS = ("memory", "tool", "claude")


def pick_with_nengo(utilities: dict[str, float]) -> dict:
    for action in ACTIONS:
        value = utilities.get(action)
        if not isinstance(value, (int, float)) or isinstance(value, bool) or not 0.0 <= value <= 1.0:
            raise ValueError(f"{action}: Wert zwischen 0 und 1 notwendig")
    try:
        import nengo
        import nengo_spa as spa
        import numpy as np
    except ImportError as exc:
        raise RuntimeError("Optionale Forschungspakete fehlen. Separat installieren: pip install nengo nengo-spa") from exc
    # Independent biological *action-selection mechanism* from NengoSPA.
    # For each task this creates and simulates a fresh network (not cheap).
    # The utilities are NOT created by a language model or a connectome.
    with spa.Network(seed=4) as model:
        state = spa.State(16, neurons_per_dimension=20)
        with spa.ActionSelection() as decision:
            spa.ifmax("memory", float(utilities["memory"]), spa.sym.MEMORY >> state)
            spa.ifmax("tool", float(utilities["tool"]), spa.sym.TOOL >> state)
            spa.ifmax("claude", float(utilities["claude"]), spa.sym.CLAUDE >> state)
        p = nengo.Probe(decision.thalamus.output, synapse=0.01)
    with nengo.Simulator(model, progress_bar=False) as sim:
        sim.run(0.25, progress_bar=False)
        # Mean of latter half after transients; names correspond to ifmax order.
        neural_values = np.mean(sim.data[p][len(sim.data[p]) // 2 :], axis=0)
    if not np.all(np.isfinite(neural_values)):
        raise RuntimeError("Nengo-Ausgabe ungueltig")
    neural = {name: round(float(neural_values[i]), 5) for i, name in enumerate(ACTIONS)}
    chosen = max(neural, key=neural.get)
    baseline = max(ACTIONS, key=lambda name: utilities[name])
    return {"nengo_selection": chosen, "deterministic_baseline": baseline,
            "equal_to_baseline": chosen == baseline, "nengo_output": neural,
            "warning": "Forschungslauf, kein Beleg fuer bessere Entscheidungen, nicht automatisch im Claude-Router verwenden"}


def main() -> int:
    ap = argparse.ArgumentParser(description="NengoSPA Forschungsdemo (optional)")
    ap.add_argument("--memory", type=float, default=0.8)
    ap.add_argument("--tool", type=float, default=0.3)
    ap.add_argument("--claude", type=float, default=0.2)
    args = ap.parse_args()
    try:
        out = pick_with_nengo({"memory": args.memory, "tool": args.tool, "claude": args.claude})
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return 0
    except (ValueError, RuntimeError) as exc:
        print(f"nengo: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
