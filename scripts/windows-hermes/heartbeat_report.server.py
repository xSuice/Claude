#!/usr/bin/env python3
"""Heartbeat-Annahme fuer Hermes-Profile (KIMI SOLO 2026-10-27).
Aufruf: heartbeat_report.py <handle> [<handle> ...]
Schreibt je Handle einen Heartbeat (Upsert wie watchdog.write_self_heartbeat). Quelle = PC-Reporter, der nur meldet,
wenn das Hermes-Gateway nachweislich laeuft (PID lebt, Zustand 'running', Status < 3 min alt). Keine Heartbeats = Watchdog schlaegt an."""
import re
import sys

sys.path.insert(0, '/opt/jarvis/council')
import db_adapter  # noqa: E402

OK = re.compile(r'^[a-z0-9][a-z0-9-]{1,40}$')


def main(argv):
    handles = [h for h in argv if OK.match(h)]
    bad = [h for h in argv if not OK.match(h)]
    if bad:
        print('verworfen (ungueltiger Handle): ' + ', '.join(b[:30] for b in bad), file=sys.stderr)
    if not handles or len(handles) > 40:
        print('keine/zu viele Handles', file=sys.stderr)
        return 2
    conn = db_adapter.get_conn()
    try:
        with conn.cursor() as cur:
            for h in handles:
                cur.execute("INSERT INTO heartbeats (agent_handle, last_heartbeat, status) VALUES (%s, NOW(), 'ACTIVE') "
                            "ON CONFLICT (agent_handle) DO UPDATE SET last_heartbeat=NOW(), status='ACTIVE'", (h,))
        conn.commit()
    finally:
        conn.close()
    print('ok %d' % len(handles))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
