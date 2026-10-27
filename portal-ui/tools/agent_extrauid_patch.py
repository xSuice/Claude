#!/usr/bin/env python3
"""Host-Agent: zusaetzliche erlaubte Portal-UID (fail-closed, konfigurierbar). Idempotent, mit Backups.
Aenderung 1: Handler akzeptiert uid in (0, web_uid, *extra_uids).
Aenderung 2: Socket-Gruppe/-Modus nur dann geoeffnet (0660, gid=extra_gid), wenn extra_uids konfiguriert sind.
Aenderung 3: host.json erhaelt extra_uids=[1000], extra_gid=1000.
Ohne diese Schluessel gilt exakt das alte Verhalten (uid 0/web_uid, Socket 0600)."""
import json, os, pathlib, py_compile, shutil, sys, tempfile

AG = pathlib.Path("/opt/ma-home/agent.py")
CF = pathlib.Path("/etc/ma-home/host.json")
TAG = "bak-vor-extrauid-20261027"

# --- Vorpruefung: keine aktiven Jobs ---
for st in pathlib.Path("/srv/ma-home/jobs").glob("*/state.json"):
    s = json.loads(st.read_text()).get("state")
    if s in ("queued", "running", "submitting"):
        sys.exit(f"ABBRUCH: aktiver Job {st.parent.name} ({s})")

src = AG.read_text()
OLD1 = "        if uid not in (0, cfg()['web_uid']):\n            return\n"
NEW1 = "        c = cfg()\n        if uid not in (0, c['web_uid'], *c.get('extra_uids', [])):   # extra_uids: optional, fehlt es -> altes Verhalten\n            return\n"
OLD2 = "        os.chown(SOCKET, cfg()['web_uid'], cfg()['web_uid'])\n        os.chmod(SOCKET, 0o600)\n"
NEW2 = ("        c = cfg()\n"
        "        if c.get('extra_uids'):   # Portal laeuft nicht als web_uid: Gruppe oeffnen, UID-Pruefung (SO_PEERCRED) bleibt massgeblich\n"
        "            os.chown(SOCKET, c['web_uid'], c.get('extra_gid', c['web_uid']))\n"
        "            os.chmod(SOCKET, 0o660)\n"
        "        else:\n"
        "            os.chown(SOCKET, c['web_uid'], c['web_uid'])\n"
        "            os.chmod(SOCKET, 0o600)\n")

changed = False
if "extra_uids" in src:
    print("agent.py: bereits gepatcht")
else:
    assert src.count(OLD1) == 1, "Anker 1 nicht eindeutig"
    assert src.count(OLD2) == 1, "Anker 2 nicht eindeutig"
    shutil.copy2(AG, str(AG) + "." + TAG)
    src = src.replace(OLD1, NEW1).replace(OLD2, NEW2)
    tmp = AG.with_suffix(".py.new")
    tmp.write_text(src)
    py_compile.compile(str(tmp), doraise=True)
    os.chmod(tmp, 0o644)
    os.replace(tmp, AG)
    changed = True
    print("agent.py: gepatcht + kompiliert")

cfg = json.loads(CF.read_text())
if cfg.get("extra_uids") == [1000] and cfg.get("extra_gid") == 1000:
    print("host.json: bereits gesetzt")
else:
    shutil.copy2(CF, str(CF) + "." + TAG)
    cfg["extra_uids"] = [1000]
    cfg["extra_gid"] = 1000
    fd, tmpn = tempfile.mkstemp(dir=str(CF.parent), prefix=".host.json.")
    with os.fdopen(fd, "w") as f:
        json.dump(cfg, f)
    st = CF.stat()
    os.chown(tmpn, st.st_uid, st.st_gid)
    os.chmod(tmpn, st.st_mode & 0o7777)
    json.loads(pathlib.Path(tmpn).read_text())
    os.replace(tmpn, CF)
    changed = True
    print("host.json: extra_uids/extra_gid gesetzt (Modus", oct(st.st_mode & 0o7777), "erhalten)")

print("FERTIG, Aenderung:", changed)
