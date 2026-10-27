import sqlite3
from datetime import datetime

DB_NAME = "mcp_guard.db"

def init_db():
    """Create tables if they don't already exist."""
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()

    cur.execute('''
        CREATE TABLE IF NOT EXISTS audit_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            session_id TEXT NOT NULL,
            tool_name TEXT NOT NULL,
            arguments TEXT NOT NULL,
            action_taken TEXT NOT NULL,
            reason TEXT
        )
    ''')

    cur.execute('''
        CREATE TABLE IF NOT EXISTS pending_approvals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            tool_name TEXT NOT NULL,
            arguments TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending'
        )
    ''')

    conn.commit()
    conn.close()

def log_audit(session_id, tool_name, arguments, action_taken, reason=None):
    """Record an audit-log entry."""
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute(
        '''INSERT INTO audit_logs
            (timestamp, session_id, tool_name, arguments, action_taken, reason)
           VALUES (?,?,?,?,?,?)''',
        (datetime.utcnow().isoformat(), session_id, tool_name,
         str(arguments), action_taken, reason)
    )
    conn.commit()
    conn.close()

def add_pending_approval(session_id, tool_name, arguments):
    """Queue a blocked tool call for manual review."""
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute(
        '''INSERT INTO pending_approvals
            (session_id, tool_name, arguments)
           VALUES (?,?,?)''',
        (session_id, tool_name, str(arguments))
    )
    conn.commit()
    conn.close()

def get_audit_entries():
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute('SELECT * FROM audit_logs ORDER BY timestamp')
    rows = cur.fetchall()
    conn.close()
    return rows

def resolve_approval(approval_id, status):
    """Approve or deny a pending entry."""
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute(
        '''UPDATE pending_approvals
           SET status = ?
           WHERE id = ? AND status = "pending" ''',
        (status, approval_id)
    )
    conn.commit()
    affected = cur.rowcount
    conn.close()
    return affected > 0