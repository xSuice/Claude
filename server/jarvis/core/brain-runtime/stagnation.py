"""P3: Stagnation detection and loop detection for JARVIS watchdog."""
import logging
import psycopg2
from datetime import datetime, timedelta, timezone
from pathlib import Path

log = logging.getLogger('stagnation')

def get_staging_conn():
    """Connect to jarvis_staging using pg_creds file."""
    creds_file = Path.home() / '.jarvis-staging' / 'pg_creds'
    if not creds_file.exists():
        log.warning('pg_creds not found at %s', creds_file)
        return None
    password = creds_file.read_text().strip()
    try:
        return psycopg2.connect(
            dbname='jarvis_staging',
            user='jarvis_staging_rw',
            host='127.0.0.1',
            port=5432,
            password=password
        )
    except Exception as e:
        log.error('DB connection failed: %s', e)
        return None

def stagnation_check(conn, max_checks=3):
    """Check for stalled tasks: ACTIVE + last_heartbeat > 30min → STALLED."""
    if not conn:
        return {'checked': 0, 'stalled': 0, 'error': 'no connection'}
    
    results = {'checked': 0, 'stalled': 0, 'warnings': []}
    cutoff_30min = datetime.now(timezone.utc) - timedelta(minutes=30)
    cutoff_5min = datetime.now(timezone.utc) - timedelta(minutes=5)
    
    with conn.cursor() as cur:
        # Find ACTIVE tasks with stale heartbeats
        cur.execute("""
            SELECT t.id, t.task_id, t.assigned_to, h.last_heartbeat
            FROM tasks t
            LEFT JOIN heartbeats h ON h.current_task_id = t.id
            WHERE t.status = 'ACTIVE'
              AND (h.last_heartbeat IS NULL OR h.last_heartbeat < %s)
            LIMIT %s
        """, (cutoff_30min, max_checks))
        
        stalled_tasks = cur.fetchall()
        results['checked'] = len(stalled_tasks)
        
        for task_id, task_id_str, assigned_to, last_hb in stalled_tasks:
            # Update task status to STALLED
            cur.execute("""
                UPDATE tasks 
                SET status = 'STALLED', updated_at = NOW()
                WHERE id = %s
            """, (task_id,))
            
            # Record in task_history
            cur.execute("""
                INSERT INTO task_history (task_id, old_status, new_status, changed_by, comment)
                VALUES (%s, 'ACTIVE', 'STALLED', 'watchdog', 'Stagnation detected: no heartbeat > 30min')
            """, (task_id,))
            
            results['stalled'] += 1
            log.warning('Task %s (assigned=%s) marked STALLED (last_hb=%s)', 
                       task_id_str, assigned_to, last_hb)
        
        # Check for agents with stale heartbeats (warning only)
        cur.execute("""
            SELECT agent_handle, last_heartbeat 
            FROM heartbeats 
            WHERE last_heartbeat < %s AND agent_handle != 'watchdog'
        """, (cutoff_5min,))
        stale_agents = cur.fetchall()
        for handle, last_hb in stale_agents:
            results['warnings'].append(f'Agent {handle} last heartbeat: {last_hb}')
            log.warning('Agent %s has stale heartbeat: %s', handle, last_hb)
    
    conn.commit()
    return results

def loop_detection(conn, max_checks=3):
    """Detect status loops: >5 transitions between same states in <10min → BLOCKED."""
    if not conn:
        return {'checked': 0, 'blocked': 0, 'error': 'no connection'}
    
    results = {'checked': 0, 'blocked': 0}
    cutoff_10min = datetime.now(timezone.utc) - timedelta(minutes=10)
    
    with conn.cursor() as cur:
        # Find tasks with rapid status oscillation
        cur.execute("""
            SELECT th.task_id, t.task_id as task_id_str, t.assigned_to,
                   COUNT(*) as transition_count
            FROM task_history th
            JOIN tasks t ON t.id = th.task_id
            WHERE th.changed_at > %s
            GROUP BY th.task_id, t.task_id, t.assigned_to
            HAVING COUNT(*) > 5
            LIMIT %s
        """, (cutoff_10min, max_checks))
        
        looping_tasks = cur.fetchall()
        results['checked'] = len(looping_tasks)
        
        for task_int_id, task_id_str, assigned_to, count in looping_tasks:
            # Check if it's actually oscillating (same old/new pairs)
            cur.execute("""
                SELECT old_status, new_status, COUNT(*) as pair_count
                FROM task_history
                WHERE task_id = %s AND changed_at > %s
                GROUP BY old_status, new_status
                HAVING COUNT(*) >= 3
            """, (task_int_id, cutoff_10min))
            
            oscillating_pairs = cur.fetchall()
            if oscillating_pairs:
                # Mark as BLOCKED with loop_detected
                cur.execute("""
                    UPDATE tasks 
                    SET status = 'BLOCKED', 
                        payload = COALESCE(payload, '{}'::jsonb) || '{"blocker": "loop_detected"}'::jsonb,
                        updated_at = NOW()
                    WHERE id = %s
                """, (task_int_id,))
                
                cur.execute("""
                    INSERT INTO task_history (task_id, old_status, new_status, changed_by, comment)
                    VALUES (%s, 'ACTIVE', 'BLOCKED', 'watchdog', 
                            'Loop detected: %s transitions in 10min, oscillating pairs: %s')
                """, (task_int_id, count, str(oscillating_pairs)))
                
                results['blocked'] += 1
                log.warning('Task %s marked BLOCKED (loop detected, %s transitions)', 
                           task_id_str, count)
    
    conn.commit()
    return results
