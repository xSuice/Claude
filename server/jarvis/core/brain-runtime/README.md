# Claude Brain Runtime V5

Die vollständige Anleitung steht in `../docs/archiv/README-V5.md` (historisch; aktuell: `../START-HIER-V7.md`).

**Start:** `python -m unittest discover -s brain-runtime/tests -v`

**MCP:** `mcp_server_v5.py --config config.v5.demo.json` (Test) oder mit eigener, geschützter `config.local.json`.

**Administrative Bestätigung:** `brain_admin.py --config config.local.json pending ma-home`, danach ggf. `confirm <ID>`.

**Lokaler Zyklus:** `supervisor.py --config config.local.json --once`.

**Vergleich:** `compare_runs.py --before before.json --after after.json`.

Die ursprüngliche read-only V4-Anleitung ist in `README-V4-HISTORY.md` erhalten.
