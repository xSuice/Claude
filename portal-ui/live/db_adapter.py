#!/usr/bin/env python3
"""JARVIS Council DB Adapter - P2. Writes tasks/decisions to jarvis_staging."""
import json, os, sys, uuid
from datetime import datetime, timezone
import psycopg2

CREDS_FILE = '/home/andrew/.jarvis-staging/pg_creds'
DB_NAME = 'jarvis_staging'
DB_USER = 'jarvis_staging_rw'
DB_HOST = '127.0.0.1'

def get_conn():
    with open(CREDS_FILE) as f:
        pw = f.read().strip()
    return psycopg2.connect(dbname=DB_NAME, user=DB_USER, host=DB_HOST, password=pw)

def create_task(title, description, assigned_to=None, priority=0, parent_task_id=None, payload=None):
    task_id = f'task-{uuid.uuid4().hex[:8]}'
    conn = get_conn()
    with conn.cursor() as cur:
        cur.execute("""INSERT INTO tasks (task_id, title, description, status, priority, assigned_to, parent_task_id, payload, created_at, updated_at)
                         VALUES (%s, %s, %s, 'INBOX', %s, %s, %s, %s::jsonb, NOW(), NOW())
                         RETURNING id, task_id""",
                    (task_id, title, description, priority, assigned_to, parent_task_id, json.dumps(payload or {})))
        row = cur.fetchone()
        cur.execute("""INSERT INTO task_history (task_id, old_status, new_status, changed_by, comment)
                         VALUES (%s, NULL, 'INBOX', 'council-adapter', 'Task created via P2 adapter')""", (row[0],))
    conn.commit()
    conn.close()
    return {'id': row[0], 'task_id': task_id}

def update_task_status(task_id, new_status, changed_by='council-adapter', comment=None):
    conn = get_conn()
    with conn.cursor() as cur:
        cur.execute('SELECT id, status FROM tasks WHERE task_id=%s', (task_id,))
        row = cur.fetchone()
        if not row:
            conn.close()
            return {'error': f'task {task_id} not found'}
        old_status = row[1]
        cur.execute("""UPDATE tasks SET status=%s, updated_at=NOW() WHERE task_id=%s""", (new_status, task_id))
        cur.execute("""INSERT INTO task_history (task_id, old_status, new_status, changed_by, comment)
                         VALUES ((SELECT id FROM tasks WHERE task_id=%s), %s, %s, %s, %s)""",
                    (task_id, old_status, new_status, changed_by, comment))
    conn.commit()
    conn.close()
    return {'task_id': task_id, 'old': old_status, 'new': new_status}

def record_council_decision(council_name, decision_type, outcome):
    decision_id = f'dec-{uuid.uuid4().hex[:8]}'
    conn = get_conn()
    with conn.cursor() as cur:
        cur.execute("""INSERT INTO council_decisions (decision_id, council_name, decision_type, outcome, created_at)
                         VALUES (%s, %s, %s, %s::jsonb, NOW()) RETURNING id, decision_id""",
                    (decision_id, council_name, decision_type, json.dumps(outcome)))
        row = cur.fetchone()
    conn.commit()
    conn.close()
    return {'id': row[0], 'decision_id': decision_id}

def list_active_tasks(assigned_to=None):
    conn = get_conn()
    with conn.cursor() as cur:
        if assigned_to:
            cur.execute("""SELECT task_id, title, status, priority, assigned_to FROM tasks
                             WHERE status IN ('INBOX','PLANNING','ACTIVE','BLOCKED') AND assigned_to=%s
                             ORDER BY priority DESC, created_at""", (assigned_to,))
        else:
            cur.execute("""SELECT task_id, title, status, priority, assigned_to FROM tasks
                             WHERE status IN ('INBOX','PLANNING','ACTIVE','BLOCKED')
                             ORDER BY priority DESC, created_at""")
        rows = cur.fetchall()
    conn.close()
    return [{'task_id': r[0], 'title': r[1], 'status': r[2], 'priority': r[3], 'assigned_to': r[4]} for r in rows]

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Usage: db_adapter.py <create_task|update_status|record_decision|list_active> [args...]')
        sys.exit(1)
    cmd = sys.argv[1]
    if cmd == 'create_task':
        result = create_task(sys.argv[2], sys.argv[3] if len(sys.argv)>3 else '', sys.argv[4] if len(sys.argv)>4 else None)
    elif cmd == 'update_status':
        result = update_task_status(sys.argv[2], sys.argv[3], sys.argv[4] if len(sys.argv)>4 else 'council-adapter')
    elif cmd == 'record_decision':
        result = record_council_decision(sys.argv[2], sys.argv[3], json.loads(sys.argv[4]) if len(sys.argv)>4 else {})
    elif cmd == 'list_active':
        result = list_active_tasks(sys.argv[2] if len(sys.argv)>2 else None)
    else:
        print(f'Unknown command: {cmd}')
        sys.exit(1)
    print(json.dumps(result, indent=2, default=str))
