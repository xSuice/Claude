"""Chat Bus Mention Poller — PostgreSQL-Polling für @mentions und Routing an Hermes.

Implementiert Option B aus chat_bus_deployment_package.md:
- Pollt messages WHERE mentions && ARRAY['@agent-name']
- Routing an Hermes via message_agent (HTTP-POST an /api/bot/dm)
- Läuft als Background-Thread im Portal oder als separater Service

Integration in portal.py:
    from chat_bus_mention_poller import start_mention_poller
    start_mention_poller()  # Nach app.register_blueprint(chat_bus_bp)

Konfiguration via Umgebungsvariablen:
    CHAT_BUS_POLL_INTERVAL: Polling-Intervall in Sekunden (Default: 5.0)
    CHAT_BUS_HERMES_API: Hermes Bot-API URL (Default: http://localhost:8484/api/bot/dm)
    CHAT_BUS_PG_DSN: PostgreSQL DSN (Default: gleich wie chat_bus_backend.py)
"""
from __future__ import annotations

import json
import logging
import os
import threading
import time

try:
    import psycopg2
    import psycopg2.extras
except ImportError:
    psycopg2 = None

try:
    import requests
except ImportError:
    requests = None

log = logging.getLogger(__name__)

# --- Konfiguration ---
PG_DSN = os.environ.get('CHAT_BUS_PG_DSN',
    'host=/var/run/postgresql dbname=jarvis_staging user=jarvis_staging_rw application_name=mention_poller')
POLL_INTERVAL = float(os.environ.get('CHAT_BUS_POLL_INTERVAL', '5.0'))
HERMES_API = os.environ.get('CHAT_BUS_HERMES_API', 'http://localhost:8484/api/bot/dm')
BATCH_SIZE = 50  # Max mentions pro Poll-Zyklus

# Tracking: Welche messages wurden bereits geroutet?
_routed_lock = threading.Lock()
_routed_ids: set[int] = set()


def _pg():
    """Erstellt eine neue PostgreSQL-Verbindung."""
    if psycopg2 is None:
        raise RuntimeError('psycopg2 nicht installiert')
    conn = psycopg2.connect(PG_DSN)
    conn.autocommit = True
    return conn


def _fetch_unrouted_mentions(conn) -> list[dict]:
    """Holt messages mit mentions, die noch nicht geroutet wurden.

    Nutzt GIN-Index auf mentions[] für effiziente Abfrage.
    Filtert auf messages der letzten 24h, um alte Nachrichten zu ignorieren.
    """
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(
            """SELECT id, message_id, from_agent, channel, content, mentions, created_at
               FROM messages
               WHERE mentions IS NOT NULL
                 AND array_length(mentions, 1) > 0
                 AND created_at > NOW() - INTERVAL '24 hours'
               ORDER BY created_at DESC
               LIMIT %s""",
            (BATCH_SIZE,),
        )
        rows = cur.fetchall()

    with _routed_lock:
        return [
            {
                'id': r['id'],
                'message_id': r['message_id'],
                'from_agent': r['from_agent'],
                'channel': r['channel'],
                'content': r['content'],
                'mentions': list(r['mentions'] or []),
                'created_at': r['created_at'].isoformat() if r['created_at'] else None,
            }
            for r in rows
            if r['id'] not in _routed_ids
        ]


def _route_mention_to_hermes(mention: str, message: dict) -> bool:
    """Sendet eine Mention-Notification an Hermes via Bot-API.

    POST /api/bot/dm mit:
    {
        "target": "jarvis-core",
        "message": "@jarvis-core erwähnt in #jarvis von @user: ..."
    }

    Returns: True bei Erfolg, False bei Fehler.
    """
    if requests is None:
        log.error('requests nicht installiert, kann Mention nicht routen')
        return False

    from_agent = message.get('from_agent', 'unknown')
    channel = message.get('channel', '#unknown')
    content = message.get('content', {})

    if isinstance(content, dict):
        text = content.get('text', '')
    else:
        text = str(content)

    text_preview = text[:200] + ('...' if len(text) > 200 else '')

    notification = (
        f"@{mention} erwähnt in {channel} von @{from_agent}:\n"
        f"{text_preview}"
    )

    payload = {
        'target': mention,
        'message': notification,
    }

    try:
        resp = requests.post(
            HERMES_API,
            json=payload,
            timeout=5.0,
            headers={'Content-Type': 'application/json'},
        )
        if resp.status_code in (200, 201, 202):
            log.info(f'Mention @{mention} geroutet (message_id={message["message_id"]})')
            return True
        else:
            log.warning(f'Mention-Routing fehlgeschlagen: HTTP {resp.status_code} — {resp.text[:200]}')
            return False
    except Exception as exc:
        log.error(f'Mention-Routing Exception: {type(exc).__name__}: {exc}')
        return False


def _poll_once() -> int:
    """Einzelner Poll-Zyklus: Holt unrouted mentions und routet sie.

    Returns: Anzahl erfolgreich gerouteter mentions.
    """
    conn = None
    try:
        conn = _pg()
        messages = _fetch_unrouted_mentions(conn)

        routed_count = 0
        for msg in messages:
            for mention in msg['mentions']:
                success = _route_mention_to_hermes(mention, msg)
                if success:
                    routed_count += 1

            with _routed_lock:
                _routed_ids.add(msg['id'])
                if len(_routed_ids) > 1000:
                    _routed_ids.clear()
                    _routed_ids.add(msg['id'])

        return routed_count
    except Exception as exc:
        log.error(f'Poll-Zyklus fehlgeschlagen: {type(exc).__name__}: {exc}')
        return 0
    finally:
        if conn is not None:
            try:
                conn.close()
            except Exception:
                pass


def _poll_loop():
    """Background-Thread: Pollt alle POLL_INTERVAL Sekunden."""
    log.info(f'Mention-Poller gestartet (Intervall={POLL_INTERVAL}s, Hermes-API={HERMES_API})')
    while True:
        try:
            routed = _poll_once()
            if routed > 0:
                log.info(f'{routed} mentions geroutet')
        except Exception as exc:
            log.error(f'Poll-Loop Exception: {type(exc).__name__}: {exc}')

        time.sleep(POLL_INTERVAL)


def start_mention_poller():
    """Startet den Mention-Poller als Background-Thread.

    Aufruf in portal.py nach app.register_blueprint(chat_bus_bp):
        from chat_bus_mention_poller import start_mention_poller
        start_mention_poller()

    Der Thread läuft daemonized und wird beim Service-Stop automatisch beendet.
    """
    if psycopg2 is None:
        log.error('psycopg2 nicht installiert, Mention-Poller nicht gestartet')
        return
    if requests is None:
        log.error('requests nicht installiert, Mention-Poller nicht gestartet')
        return

    thread = threading.Thread(
        target=_poll_loop,
        name='chat-bus-mention-poller',
        daemon=True,
    )
    thread.start()
    log.info('Mention-Poller-Thread gestartet')


# --- Smoke-Test (nur beim direkten Aufruf) ---
if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')

    print('chat_bus_mention_poller: Smoke-Test')
    print(f'  PG_DSN: {PG_DSN}')
    print(f'  POLL_INTERVAL: {POLL_INTERVAL}s')
    print(f'  HERMES_API: {HERMES_API}')
    print(f'  BATCH_SIZE: {BATCH_SIZE}')

    print('\nSmoke-Test abgeschlossen. Starte Poller mit start_mention_poller() in portal.py.')
