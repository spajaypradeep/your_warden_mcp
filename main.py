import os
import json
import sqlite3
from fastapi import FastAPI, Request, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import yaml
from database import init_db, log_audit, add_pending_approval, resolve_approval

app = FastAPI()

# Serve static assets (CSS/JS) -------------------------------------------------
app.mount("/static", StaticFiles(directory="static"), name="static")

# Jinja2 templates ------------------------------------------------------------
templates = Jinja2Templates(directory="templates")

# Load policy ---------------------------------------------------------------
with open('registry.yaml', 'r') as f:
    policy_data = yaml.safe_load(f)

# Dict of tool name → {category, description, …}
TOOL_REGISTRY = {t['name']: t for t in policy_data['tools']}

# Sessions that have executed an untrusted_content tool (tainted)
tainted_sessions = set()

# Initialise DB on startup
init_db()


# ------------------- Tool‑call endpoint ------------------------------------
@app.post("/v1/tool-call")
async def tool_call(request: Request):
    data = await request.json()
    session_id = data.get("session_id")
    tool_name = data.get("tool_name")
    arguments = data.get("arguments")

    # Minimal validation
    if not all([session_id, tool_name, arguments]):
        raise HTTPException(status_code=400, detail="Missing required fields")

    # Unknown tool?
    if tool_name not in TOOL_REGISTRY:
        raise HTTPException(status_code=400, detail="Unknown tool")

    tool_category = TOOL_REGISTRY[tool_name]['category']

    # Block if the session is already tainted and the tool is OUTBOUND
    if session_id in tainted_sessions and tool_category == 'outbound':
        log_audit(session_id, tool_name, arguments,
                  'blocked', 'Session previously executed untrusted_content tool')
        add_pending_approval(session_id, tool_name, arguments)
        return {"status": "blocked",
                "reason": "Session previously executed untrusted_content tool"}

    # Mark session as tainted if this call itself is UNTRUSTED_CONTENT
    if tool_category == 'untrusted_content':
        tainted_sessions.add(session_id)

    # Otherwise allow and log
    log_audit(session_id, tool_name, arguments, "allowed")
    return {"status": "allowed"}


# ------------------- Pending‑approvals endpoints ---------------------------
@app.get("/v1/approvals")
async def approvals():
    """Return all pending (blocked) tool calls awaiting review."""
    conn = sqlite3.connect('mcp_guard.db')
    cur = conn.cursor()
    cur.execute('''
        SELECT id, session_id, tool_name, arguments, status
        FROM pending_approvals WHERE status = "pending"''')
    rows = cur.fetchall()
    conn.close()
    return [
        {
            "id": row[0],
            "session_id": row[1],
            "tool_name": row[2],
            "arguments": row[3],
            "status": row[4]
        } for row in rows
    ]


@app.post("/v1/approvals/{approval_id}/resolve")
async def resolve_approval_endpoint(approval_id: int, resolve_action: str):
    if resolve_action not in ('approve', 'deny'):
        raise HTTPException(status_code=400,
                            detail="Decision must be 'approve' or 'deny'")
    ok = resolve_approval(approval_id, resolve_action)
    if not ok:
        raise HTTPException(status_code=404,
                            detail="Pending approval not found or already resolved")
    return {"status": "resolved", "decision": resolve_action}


# ------------------- Dashboard ------------------------------------------------
@app.get("/", defaults={"path": ""})
async def root():
    return {"message": "MCP Guard API is running. Visit /dashboard to see the admin panel."}


@app.get("/dashboard")
async def dashboard():
    """Render a simple HTML page showing pending approvals and recent audit log."""
    conn = sqlite3.connect('mcp_guard.db')
    cur = conn.cursor()

    cur.execute('SELECT * FROM audit_logs ORDER BY timestamp DESC LIMIT 50')
    audit_rows = cur.fetchall()

    cur.execute('SELECT * FROM pending_approvals WHERE status = "pending"')
    pending_rows = cur.fetchall()
    conn.close()

    # Transform rows into dictionaries for the template
    audit_logs = [
        {
            "id": r[0],
            "timestamp": r[1],
            "session_id": r[2],
            "tool_name": r[3],
            "action_taken": r[5],
            "reason": r[6]
        } for r in audit_rows
    ]

    pending_approvals = [
        {
            "id": r[0],
            "session_id": r[1],
            "tool_name": r[2],
            "arguments": r[3],
            "status": r[4]
        } for r in pending_rows
    ]

    return templates.TemplateResponse("dashboard.html",
                                      {"request": None,
                                       "audit_logs": audit_logs,
                                       "pending_approvals": pending_approvals})


# ------------------- Entrypoint ---------------------------------------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)