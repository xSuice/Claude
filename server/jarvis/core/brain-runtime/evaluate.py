#!/usr/bin/env python3
"""Offline deterministic retrieval gate with fixed expected ids; not a Claude model benchmark."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from gateway import KnowledgeGateway


def evaluate(gateway: KnowledgeGateway, cases: dict) -> dict:
    results = []
    for index, case in enumerate(cases["cases"], 1):
        output = gateway.search(case["query"], case["project"])
        seen = {i["id"] for i in output["items"]}
        ok = set(case["required_ids"]).issubset(seen) and not (seen & set(case["forbidden_ids"]))
        results.append({"case": index, "pass": ok, "found": sorted(seen),
                        "response_chars": len(json.dumps(output, ensure_ascii=False))})
    return {"passed": sum(r["pass"] for r in results), "total": len(results), "results": results,
            "scope": "Synthetic retrieval/ACL tests only. No model quality or Claude quota measured."}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=Path("brain-runtime/config.demo.json"))
    parser.add_argument("--cases", type=Path, default=Path("brain-runtime/evals/cases.json"))
    args = parser.parse_args()
    conf = json.loads(args.config.read_text(encoding="utf-8"))
    res = evaluate(KnowledgeGateway(Path(conf["source"]), conf["identity"], set(conf["allowed_projects"])),
                   json.loads(args.cases.read_text(encoding="utf-8")))
    print(json.dumps(res, ensure_ascii=False, indent=2))
    return 0 if res["passed"] == res["total"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
