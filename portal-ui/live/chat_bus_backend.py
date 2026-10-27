"""Chat Bus Backend — SSE-Streaming und Message-Posting für MA-HOME Portal.

Integration in portal.py:
    from chat_bus_backend import chat_bus_bp
    app.register_blueprint(chat_bus_bp)

Benötigt: python3-psycopg2, PostgreSQL jarvis_staging mit erweitertem Schema.
"""
from __future__ import annotations

import json
import os
import re
import threading
import time
import uuid
from datetime import datetime, timezone

from flask import Blueprint, Response, abort, g, jsonify, request, stream_with_context

try:
    import psycopg2
    import psycopg2.extras
    import psycopg2.pool
except ImportError:
    psycopg2 = None

chat_bus_bp = Blueprint('chat_bus', __name__)

# --- Konfiguration ---
PG_DSN = os.environ.get('CHAT_BUS_PG_DSN',
    'host=/var/run/postgresql dbname=jarvis_staging user=jarvis_staging_rw application_name=portal')
SSE_POLL_INTERVAL = float(os.environ.get('CHAT_BUS_POLL', '1.0'))
MAX_CONTENT_LEN = 4000
MAX_MENTIONS = 20
RATE_LIMIT_PER_SEC = 10

# --- Requester Identity (P0-Gate) ---
def _get_requester_id() -> str:
    """Extract requester identity from request headers or fallback to IP.
    Priority: X-Client-ID > Authorization bearer token hash > remote_addr
    """
    client_id = request.headers.get("X-Client-ID", "").strip()
    if client_id and len(client_id) <= 64:
        return f"client:{client_id}"
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        token_hash = hashlib.sha256(auth[7:].encode()).hexdigest()[:16]
        return f"bearer:{token_hash}"
    return f"ip:{request.remote_addr or "unknown"}"

import hashlib


# Hermes-Roster (Stand 2026-10-24)
HERMES_ROSTER = frozenset({
    'hermes', 'jarvis-architecture', 'jarvis-brain', 'jarvis-cloud-dev',
    'jarvis-context', 'jarvis-core', 'jarvis-dependencies', 'jarvis-design',
    'jarvis-integrator', 'jarvis-observability', 'jarvis-planner',
    'jarvis-portal', 'jarvis-qa', 'jarvis-recovery', 'jarvis-research',
    'jarvis-router', 'jarvis-security', 'jarvis-server-fix', 'jarvis-worker',
})

CHANNEL_RE = re.compile(r'^#[a-z][a-z0-9-]{0,40}$')
MENTION_RE = re.compile(r'@([a-z][a-z0-9-]{0,30})', re.IGNORECASE)

# --- Rate-Limiting (thread-safe) ---
_rate_lock = threading.Lock()
_rate_buckets: dict[str, list[float]] = {}


def _rate_ok(user: str = None) -> bool:
    if user is None:
        user = _get_requester_id()
    now = time.monotonic()
    with _rate_lock:
        bucket = _rate_buckets.setdefault(user, [])
        # Fenster: letzte 1 Sekunde
        cutoff = now - 1.0
        _rate_buckets[user] = [t for t in bucket if t > cutoff]
        if len(_rate_buckets[user]) >= RATE_LIMIT_PER_SEC:
            return False
        _rate_buckets[user].append(now)
        return True


def _valid_channel(ch: str) -> bool:
    return bool(CHANNEL_RE.match(ch or ''))


def _extract_mentions(text: str) -> list[str]:
    if not text:
        return []
    raw = MENTION_RE.findall(text[:MAX_CONTENT_LEN])
    seen: set[str] = set()
    out: list[str] = []
    for m in raw:
        norm = m.lower()
        if norm in HERMES_ROSTER and norm not in seen:
            seen.add(norm)
            out.append(norm)
            if len(out) >= MAX_MENTIONS:
                break
    return out


def _pg():
    if psycopg2 is None:
        abort(500, 'psycopg2 nicht installiert')
    conn = psycopg2.connect(PG_DSN)
    conn.autocommit = True
    return conn


# --- SSE-Stream ---
@chat_bus_bp.route('/api/chat/stream')
def chat_stream():
    """Server-Sent Events. Query-Param: channels=#jarvis,#council-x (Komma-separiert)."""
    raw_channels = (request.args.get('channels') or '#jarvis').split(',')
    channels = [c.strip() for c in raw_channels if _valid_channel(c.strip())]
    if not channels:
        abort(400, 'Keine gültigen Kanäle')

    try:
        since_id = int(request.args.get('since') or 0)
    except (TypeError, ValueError):
        since_id = 0

    user = getattr(g, 'user', 'anonymous')

    def generate():
        # Initialer Snapshot + Keepalive
        yield f"event: hello\ndata: {json.dumps({'user': user, 'channels': channels, 'since': since_id})}\n\n"
        last_id = since_id
        conn = None
        try:
            while True:
                try:
                    if conn is None or conn.closed:
                        conn = _pg()
                    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                        cur.execute(
                            """SELECT id, message_id, from_agent, to_agent, channel,
                                      created_at, content, thread_id, mentions, metadata
                               FROM messages
                               WHERE channel = ANY(%s) AND id > %s
                               ORDER BY id ASC LIMIT 100""",
                            (channels, last_id),
                        )
                        rows = cur.fetchall()
                    for row in rows:
                        payload = {
                            'id': row['id'],
                            'message_id': row['message_id'],
                            'from_agent': row['from_agent'],
                            'to_agent': row['to_agent'],
                            'channel': row['channel'],
                            'created_at': row['created_at'].isoformat() if row['created_at'] else None,
                            'content': row['content'],
                            'thread_id': row['thread_id'],
                            'mentions': list(row['mentions'] or []),
                            'metadata': row['metadata'] or {},
                        }
                        yield f"event: message\ndata: {json.dumps(payload, default=str)}\n\n"
                        last_id = row['id']
                except Exception as exc:
                    yield f"event: error\ndata: {json.dumps({'error': str(exc)[:200]})}\n\n"
                    conn = None
                # Keepalive alle 15s, Polling alle SSE_POLL_INTERVAL
                for _ in range(15):
                    time.sleep(SSE_POLL_INTERVAL)
                    # Flask/WSGI kann hier abbrechen; Generator wird dann beendet.
        finally:
            if conn is not None:
                try:
                    conn.close()
                except Exception:
                    pass

    return Response(
        stream_with_context(generate()),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache, no-store',
            'X-Accel-Buffering': 'no',
            'Connection': 'keep-alive',
        },
    )


# --- History ---
@chat_bus_bp.route('/api/chat/messages', methods=['GET'])
def chat_messages_get():
    channel = request.args.get('channel') or '#jarvis'
    if not _valid_channel(channel):
        abort(400, 'Ungültiger Kanal')
    try:
        limit = min(int(request.args.get('limit') or 50), 200)
        before = int(request.args.get('before') or 0)
    except (TypeError, ValueError):
        abort(400)

    conn = _pg()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            if before:
                cur.execute(
                    """SELECT id, message_id, from_agent, to_agent, channel,
                              created_at, content, thread_id, mentions, metadata
                       FROM messages
                       WHERE channel = %s AND id < %s
                       ORDER BY id DESC LIMIT %s""",
                    (channel, before, limit),
                )
            else:
                cur.execute(
                    """SELECT id, message_id, from_agent, to_agent, channel,
                              created_at, content, thread_id, mentions, metadata
                       FROM messages WHERE channel = %s
                       ORDER BY id DESC LIMIT %s""",
                    (channel, limit),
                )
            rows = cur.fetchall()
    finally:
        conn.close()

    rows = list(reversed(rows))
    for r in rows:
        if r.get('created_at'):
            r['created_at'] = r['created_at'].isoformat()
        r['mentions'] = list(r.get('mentions') or [])
        r['metadata'] = r.get('metadata') or {}
    return jsonify({'channel': channel, 'messages': rows})


# --- Posten ---
@chat_bus_bp.route('/api/chat/messages', methods=['POST'])
def chat_messages_post():
    user = getattr(g, 'user', None)
    if not user:
        abort(401)
    if not _rate_ok(user):
        abort(429, 'Rate-Limit überschritten')

    body = request.get_json(silent=True) or {}
    channel = (body.get('channel') or '').strip()
    content = (body.get('content') or '').strip()
    thread_id = body.get('thread_id')
    metadata = body.get('metadata') or {}

    if not _valid_channel(channel):
        abort(400, 'Ungültiger Kanal')
    if not (1 <= len(content) <= MAX_CONTENT_LEN):
        abort(400, f'Content muss 1–{MAX_CONTENT_LEN} Zeichen haben')
    if not isinstance(metadata, dict):
        abort(400, 'metadata muss Objekt sein')
    # P0-GATE: Inject requester identity for memory isolation
    if "auth_user" not in metadata:
        metadata["auth_user"] = _get_requester_id()

    mentions = _extract_mentions(content)
    message_id = f"msg-{uuid.uuid4().hex[:16]}"
    now = datetime.now(timezone.utc)

    conn = _pg()
    try:
        with conn.cursor() as cur:
            if thread_id is not None:
                try:
                    thread_id = int(thread_id)
                except (TypeError, ValueError):
                    abort(400, 'thread_id muss Integer sein')
                cur.execute(
                    """INSERT INTO messages
                         (message_id, from_agent, to_agent, channel, created_at,
                          content, thread_id, mentions, metadata)
                       VALUES (%s, %s, %s, %s, %s, %s::jsonb, %s, %s, %s::jsonb)
                       RETURNING id""",
                    (message_id, user, None, channel, now,
                     json.dumps({'text': content}), thread_id,
                     mentions, json.dumps(metadata)),
                )
            else:
                cur.execute(
                    """INSERT INTO messages
                         (message_id, from_agent, to_agent, channel, created_at,
                          content, mentions, metadata)
                       VALUES (%s, %s, %s, %s, %s, %s::jsonb, %s, %s::jsonb)
                       RETURNING id""",
                    (message_id, user, None, channel, now,
                     json.dumps({'text': content}),
                     mentions, json.dumps(metadata)),
                )
            new_id = cur.fetchone()[0]
    finally:
        conn.close()

    result = {
        'ok': True,
        'id': new_id,
        'message_id': message_id,
        'channel': channel,
        'mentions': mentions,
        'created_at': now.isoformat(),
    }

    # Mention-Routing-Hook: Hier kann der Koordinator später
    # message_agent(target=..., message=...) aufrufen.
    # Architektur-Entscheidung (Socket/PG-Polling/HTTP-Callback) ausstehend.
    if mentions:
        result['routed_to'] = mentions  # Platzhalter, bis Bridge implementiert

    return jsonify(result), 201


# --- Channel-Liste ---
@chat_bus_bp.route('/api/chat/channels', methods=['GET'])
def chat_channels():
    conn = _pg()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """SELECT channel, COUNT(*) AS message_count,
                          MAX(created_at) AS last_activity
                   FROM messages
                   WHERE channel IS NOT NULL
                   GROUP BY channel
                   ORDER BY last_activity DESC NULLS LAST"""
            )
            rows = cur.fetchall()
    finally:
        conn.close()

    channels = [
        {
            'name': r[0],
            'message_count': int(r[1]),
            'last_activity': r[2].isoformat() if r[2] else None,
        }
        for r in rows
    ]
    # Standardkanal immer listen, auch wenn leer
    if not any(c['name'] == '#jarvis' for c in channels):
        channels.insert(0, {'name': '#jarvis', 'message_count': 0, 'last_activity': None})
    return jsonify({'channels': channels})


# --- Smoke-Test (nur beim Import) ---
if __name__ == '__main__':
    assert _valid_channel('#jarvis')
    assert _valid_channel('#council-cloud-dev')
    assert not _valid_channel('invalid')
    assert not _valid_channel('#UPPER')
    assert not _valid_channel('')
    assert _extract_mentions('@jarvis-core bitte @hermes hilfe @invalid-xx') == ['jarvis-core', 'hermes']
    assert _extract_mentions('') == []
    print('chat_bus_backend: self-test OK')
