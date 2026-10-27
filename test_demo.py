import requests
import json
import sqlite3
from datetime import datetime

API_URL = "http://localhost:8000"

def init_db_for_demo():
    """Initialize the database for demo - ensures tables exist."""
    conn = sqlite3.connect('mcp_guard.db')
    cursor = conn.cursor()
    cursor.execute('''
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
    cursor.execute('''
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

def log_audit_entry(session_id, tool_name, arguments, action_taken, reason=None):
    """Log an audit entry directly to DB for verification."""
    conn = sqlite3.connect('mcp_guard.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO audit_logs (timestamp, session_id, tool_name, arguments, action_taken, reason)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (datetime.now().isoformat(), session_id, tool_name, json.dumps(arguments), action_taken, reason))
    conn.commit()
    conn.close()

def get_audit_entries():
    """Fetch all audit entries for inspection."""
    conn = sqlite3.connect('mcp_guard.db')
    cursor = conn.cursor()
    cursor.execute('SELECT id, timestamp, session_id, tool_name, arguments, action_taken, reason FROM audit_logs')
    rows = cursor.fetchall()
    conn.close()
    return rows

def simulate_attack():
    """Simulate the indirect prompt injection attack flow."""
    print("[*] Starting MCP Guard demo simulation...")

    # Ensure DB tables exist (in case server not running yet)
    init_db_for_demo()

    session_id = "demo_session_123"
    print(f"[1] Using session ID: {session_id}")

    # Step 1: Call read_email (untrusted_content) - this taints the session
    read_email_payload = {
        "session_id": session_id,
        "tool_name": "read_email",
        "arguments": {
            "email_id": "malicious_phish@example.com",
            "content": "Hello! Click this link for prize: http://malicious-site.com"
        }
    }
    print("[2] Calling read_email (tainting session)...")
    resp1 = requests.post(f"{API_URL}/v1/tool-call", json=read_email_payload)
    print(f"    Response: {resp1.status_code} - {resp1.text}")

    # Step 2: Call send_email (outbound) - should be blocked because session is tainted
    send_email_payload = {
        "session_id": session_id,
        "tool_name": "send_email",
        "arguments": {
            "to": "attacker@example.com",
            "subject": "Your prize!",
            "body": "You've won a free iPhone! Click here: http://malicious-site.com"
        }
    }
    print("[3] Calling send_email (should be blocked)...")
    resp2 = requests.post(f"{API_URL}/v1/tool-call", json=send_email_payload)
    print(f"    Response: {resp2.status_code} - {resp2.text}")

    # Step 3: Check pending approvals
    print("[4] Fetching pending approvals...")
    resp3 = requests.get(f"{API_URL}/v1/approvals")
    print(f"    Endpoints: {resp3.status_code} - {resp3.text}")
    approvals = resp3.json()
    print(f"    Pending approvals count: {len(approvals)}")

    if approvals:
        approval_id = approvals[0]["id"]
        print(f"    Resolving approval ID {approval_id} as 'approve'...")
        resolve_resp = requests.post(f"{API_URL}/v1/approvals/{approval_id}/resolve", json={"action": "approve"})
        print(f"    Resolution response: {resolve_resp.status_code} - {resolve_resp.text}")

    # Step 4: Show audit log entries to verify block was recorded
    print("[5] Displaying audit log entries...")
    audit_entries = get_audit_entries()
    for entry in audit_entries:
        entry_dict = dict(zip([desc[0] for desc in sqlite3.connect('mcp_guard.db').execute("PRAGMA table_info(audit_logs)").description], entry))
        print(f"    ID:{entry_dict['id']} | Session:{entry_dict['session_id']} | Tool:{entry_dict['tool_name']} | "
              f"Action:{entry_dict['action_taken']} | Reason:{entry_dict['reason']}")

if __name__ == "__main__":
    # Ensure the database file exists before we query it
    sqlite3.connect('mcp_guard.db').close()
    simulate_attack()