#!/usr/bin/env python3
"""Optional explicit download of original OpenWorm connectome data (not automatic)."""
from __future__ import annotations
import argparse
import hashlib
import urllib.request
from pathlib import Path

URL = "https://raw.githubusercontent.com/openworm/CElegansNeuroML/master/herm_full_edgelist.csv"
MAX_BYTES = 5_000_000


def fetch(destination: Path, expected_sha256: str | None = None) -> str:
    if expected_sha256 is not None and (len(expected_sha256) != 64 or
                                         any(ch not in "0123456789abcdef" for ch in expected_sha256.lower())):
        raise ValueError("sha256 muss ein 64-stelliger Hex-Hash sein")
    if destination.exists():
        raise FileExistsError("Bestehende Datei nicht ueberschreiben")
    request = urllib.request.Request(URL, headers={"User-Agent": "claude-brain-research/1.0"})
    with urllib.request.urlopen(request, timeout=20) as handle:
        if handle.geturl() != URL:  # Refuse redirects to another host/revision.
            raise ValueError("Unerwartete Weiterleitung")
        data = handle.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES:
        raise ValueError("Datei ueber Limit")
    if not data.startswith(b"Source,Target,Weight,Type"):
        raise ValueError("Nicht das erwartete CSV-Format")
    digest = hashlib.sha256(data).hexdigest()
    if expected_sha256 is not None and digest.lower() != expected_sha256.lower():
        raise ValueError("SHA256 stimmt nicht mit dem freigegebenen Datenstand ueberein")
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(data)
    return digest


def main():
    ap = argparse.ArgumentParser(description="Fetch public OpenWorm data ON DEMAND")
    ap.add_argument("--output", type=Path, required=True)
    ap.add_argument("--sha256", help="Optionaler freigegebener SHA-256 zur Versionsbindung")
    args = ap.parse_args()
    try:
        digest = fetch(args.output, args.sha256)
    except (OSError, ValueError) as exc:
        ap.exit(2, f"Download fehlgeschlagen: {exc}\n")
    print(f"Download abgeschlossen: {args.output}\nSHA256: {digest}")


if __name__ == "__main__":
    main()
