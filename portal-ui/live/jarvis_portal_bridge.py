#!/usr/bin/env python3
"""JARVIS Portal Bridge - P6. Exposes staging DB via MA-HOME portal API pattern."""
import json, os
from flask import Blueprint, jsonify, request, g
import psycopg2

CREDS_FILE = '/home/andrew/.jarvis-staging/pg_creds'
DB_NAME = 'jarvis_staging'
DB_USER = 'jarvis_staging_rw'
DB_HOST = '127.0.0.1'

jarvis_bp = Blueprint('jarvis_bridge', __name__)

def get_conn():
    import traceback as _tb
    try:
        with open(CREDS_FILE) as f:
            pw = f.read().strip()
        return psycopg2.connect(dbname=DB_NAME, user=DB_USER, host=DB_HOST, password=pw, sslmode="disable")
    except Exception:
        open('/tmp/bridge_err.log','a').write(_tb.format_exc()+'\n')
        raise

@jarvis_bp.route('/api/jarvis/tasks', methods=['GET'])
def list_tasks():
    import traceback as _tb
    try:
        conn = get_conn()
        with conn.cursor() as cur:
            cur.execute("""SELECT task_id, title, status, assigned_to, priority, created_at, updated_at
                             FROM tasks ORDER BY created_at DESC LIMIT 50""")
            rows = cur.fetchall()
        conn.close()
        return jsonify([{'task_id': r[0], 'title': r[1], 'status': r[2], 'assigned_to': r[3],
                         'priority': r[4], 'created': str(r[5]), 'updated': str(r[6])} for r in rows])
    except Exception as e:
        open('/tmp/bridge_err.log','a').write(_tb.format_exc()+'\n')
        return jsonify(error=str(e)), 500

@jarvis_bp.route('/api/jarvis/tasks/<task_id>', methods=['GET'])
def get_task(task_id):
    conn = get_conn()
    with conn.cursor() as cur:
        cur.execute("""SELECT t.task_id, t.title, t.description, t.status, t.assigned_to, t.priority,
                                t.created_at, t.updated_at, array_agg(h.new_status || ':' || h.comment)
                         FROM tasks t LEFT JOIN task_history h ON t.id = h.task_id
                         WHERE t.task_id=%s GROUP BY t.id""", (task_id,))
        row = cur.fetchone()
    conn.close()
    if not row:
        return jsonify({'error': 'not found'}), 404
    return jsonify({'task_id': row[0], 'title': row[1], 'description': row[2], 'status': row[3],
                    'assigned_to': row[4], 'priority': row[5], 'created': str(row[6]),
                    'updated': str(row[7]), 'history': [h for h in row[8] if h]})

@jarvis_bp.route('/api/jarvis/memory', methods=['GET'])
def recall_memory():
    category = request.args.get('category')
    limit = int(request.args.get('limit', 20))
    conn = get_conn()
    with conn.cursor() as cur:
        if category:
            cur.execute("""SELECT memory_id, category, content, metadata, source_agent, confidence, created_at
                             FROM long_term_memory WHERE category=%s AND (expires_at IS NULL OR expires_at > NOW())
                             ORDER BY created_at DESC LIMIT %s""", (category, limit))
        else:
            cur.execute("""SELECT memory_id, category, content, metadata, source_agent, confidence, created_at
                             FROM long_term_memory WHERE expires_at IS NULL OR expires_at > NOW()
                             ORDER BY created_at DESC LIMIT %s""", (limit,))
        rows = cur.fetchall()
    conn.close()
    return jsonify([{'memory_id': r[0], 'category': r[1], 'content': r[2], 'metadata': r[3],
                     'source': r[4], 'confidence': float(r[5]), 'created': str(r[6])} for r in rows])

@jarvis_bp.route('/api/jarvis/watchdog', methods=['GET'])
def watchdog_status():
    conn = get_conn()
    with conn.cursor() as cur:
        cur.execute("""SELECT agent_handle, last_heartbeat, status FROM heartbeats
                         ORDER BY last_heartbeat DESC LIMIT 10""")
        rows = cur.fetchall()
    conn.close()
    return jsonify([{'agent': r[0], 'last_heartbeat': str(r[1]), 'status': r[2]} for r in rows])

if __name__ == '__main__':
    print('JARVIS Portal Bridge - register as Flask blueprint in portal.py')

# --- WRITE-PATH: Portal -> JARVIS-Kern (KIMI SOLO 2026-10-26) ---
import subprocess

CLI = '/home/andrew/.local/share/ma-jarvis/current/brain-runtime/jarvis_cli.py'
CLI_CFG = '/home/andrew/.config/ma-jarvis/jarvis.json'
MAX_REQUEST = 20000


def _cli(*args, stdin_text=None, timeout=60):
    """Fuehrt jarvis_cli aus und liefert (rc, parsed_json_oder_none)."""
    try:
        p = subprocess.run(
            ['python3', CLI, '--config', CLI_CFG, *args],
            input=stdin_text, capture_output=True, text=True, timeout=timeout,
            cwd='/home/andrew/.local/share/ma-jarvis/current/brain-runtime',
        )
    except subprocess.TimeoutExpired:
        return None, {'error': f'cli timeout nach {timeout}s'}
    line = (p.stdout or '').strip().splitlines()
    data = None
    if line:
        try:
            data = json.loads(line[-1])
        except ValueError:
            data = {'raw': line[-1][:500]}
    if p.returncode != 0 and not data:
        data = {'error': (p.stderr or 'cli fehler')[:500]}
    return p.returncode, data


@jarvis_bp.route('/api/jarvis/jobs', methods=['POST'])
def submit_job():
    body = request.get_json(silent=True) or {}
    req_text = str(body.get('request') or '').strip()
    if not (1 <= len(req_text) <= MAX_REQUEST):
        return jsonify({'error': f'request muss 1..{MAX_REQUEST} Zeichen haben'}), 400
    user = (getattr(g, 'user', '') or 'portal')[:40]
    payload = json.dumps({'request': req_text, 'client_id': f'portal:{user}',
                          'options': body.get('options') or {}}, ensure_ascii=False)
    rc, data = _cli('submit', stdin_text=payload + '\n', timeout=90)
    if data is None or 'error' in (data or {}):
        import traceback as _tb
        open('/tmp/bridge_err.log', 'a').write('SUBMIT-FAIL rc=%s data=%r\n' % (rc, data))
        return jsonify(data or {'error': 'unbekannter cli-fehler'}), 502
    return jsonify(data), 201


@jarvis_bp.route('/api/jarvis/jobs', methods=['GET'])
def list_jobs():
    rc, data = _cli('list', '--limit', str(min(int(request.args.get('limit') or 20), 100)))
    return jsonify(data or {'error': 'cli fehlgeschlagen'}), 200 if data else 502


def _job_arg(job):
    job = str(job or '')
    return job if job.replace('-', '').replace('_', '').isalnum() and len(job) <= 40 else None


@jarvis_bp.route('/api/jarvis/jobs/<job>', methods=['GET'])
def job_status(job):
    job = _job_arg(job)
    if not job:
        return jsonify({'error': 'ungueltige job-id'}), 400
    rc, data = _cli('status', job)
    return jsonify(data or {'error': 'cli fehlgeschlagen'}), 200 if data else 502


@jarvis_bp.route('/api/jarvis/jobs/<job>/events', methods=['GET'])
def job_events(job):
    job = _job_arg(job)
    if not job:
        return jsonify({'error': 'ungueltige job-id'}), 400
    since = request.args.get('since', '0')
    if not since.isdigit():
        return jsonify({'error': 'since muss integer sein'}), 400
    rc, data = _cli('events', job, '--since', since)
    return jsonify(data or {'error': 'cli fehlgeschlagen'}), 200 if data else 502


@jarvis_bp.route('/api/jarvis/jobs/<job>/result', methods=['GET'])
def job_result(job):
    job = _job_arg(job)
    if not job:
        return jsonify({'error': 'ungueltige job-id'}), 400
    rc, data = _cli('result', job)
    return jsonify(data or {'error': 'cli fehlgeschlagen'}), 200 if data else 502


@jarvis_bp.route('/api/jarvis/jobs/<job>/cancel', methods=['POST'])
def job_cancel(job):
    job = _job_arg(job)
    if not job:
        return jsonify({'error': 'ungueltige job-id'}), 400
    rc, data = _cli('cancel', job)
    return jsonify(data or {'error': 'cli fehlgeschlagen'}), 200 if data else 502


# --- AGENTEN & WATCHDOG (A5-2, KIMI SOLO 2026-10-26): echter Status aus PG heartbeats,
# Watchdog-State (JSON) und Engine-DB. Liest /opt/jarvis/watchdog + brain.db read-only. ---
import glob as _glob
import os as _os
import time as _time

WATCHDOG_STATE_DIR = '/opt/jarvis/watchdog/state'


@jarvis_bp.route('/api/jarvis/agents', methods=['GET'])
def agents_status():
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT agent_handle, last_heartbeat, status FROM heartbeats ORDER BY last_heartbeat DESC LIMIT 40")
            agents = [{'agent': r[0], 'last_heartbeat': str(r[1]), 'status': r[2]} for r in cur.fetchall()]
            cur.execute("""SELECT assigned_agent,
                                  count(*) FILTER (WHERE status = 'ACTIVE') AS active,
                                  count(*) AS total, max(updated_at) AS last_update
                           FROM tasks WHERE assigned_agent IS NOT NULL GROUP BY assigned_agent""")
            tasks = {r[0]: {'active': r[1], 'total': r[2], 'last_update': str(r[3])} for r in cur.fetchall()}
    finally:
        conn.close()

    incidents = []
    try:
        with open(_os.path.join(WATCHDOG_STATE_DIR, 'open_incidents.json')) as f:
            raw = json.load(f)
        now = _time.time()
        for v in raw.values():
            incidents.append({
                'incident_id': v.get('incident_id'), 'adapter': v.get('adapter'),
                'subject': v.get('subject'), 'classification': v.get('classification'),
                'opened_ts': v.get('opened_ts'),
                'age_min': int((now - (v.get('opened_ts') or now)) // 60),
                'state': v.get('state')})
        incidents.sort(key=lambda x: -(x['opened_ts'] or 0))
    except OSError:
        pass

    engine = {'active': [], 'recent': [], 'error': None}
    try:
        import sqlite3 as _sq
        paths = sorted(_glob.glob('/srv/ma-home/library/.jarvis/v16/*/brain.db'))
        if paths:
            con = _sq.connect('file:%s?mode=ro' % paths[0], uri=True)
            try:
                rows = con.execute("SELECT id, state, updated, tokens_new, started FROM jobs "
                                   "WHERE state IN ('queued','planning','running','waiting_approval','waiting_pc') "
                                   "ORDER BY updated DESC LIMIT 10").fetchall()
                engine['active'] = [{'id': r[0], 'state': r[1], 'updated': r[2],
                                     'tokens_new': r[3], 'started': r[4]} for r in rows]
                rows = con.execute("SELECT id, state, finished, tokens_new FROM jobs "
                                   "WHERE state IN ('done','partial','failed','cancelled') "
                                   "ORDER BY finished DESC LIMIT 5").fetchall()
                engine['recent'] = [{'id': r[0], 'state': r[1], 'finished': r[2], 'tokens_new': r[3]} for r in rows]
            finally:
                con.close()
    except Exception as e:
        engine['error'] = str(e)[:200]

    return jsonify({'agents': agents, 'tasks': tasks, 'incidents': incidents,
                    'engine': engine, 'ts': _time.time()})
# --- AGENTS-ENDPOINT-A5-2 ---
