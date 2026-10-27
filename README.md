# MCP Guard Prototype

A minimal, working backend prototype for **MCP Guard** in Python using FastAPI and SQLite. This 1‑day emergency prototype demonstrates detecting and blocking an indirect prompt‑injection attack.

## Features

- **Policy‑driven tool registry** (`registry.yaml`) – define tools and their trust categories.
- **Session tainting** – after a session calls an `untrusted_content` tool, any subsequent `outbound` tool calls are blocked.
- **Audit logging** – every tool call (allowed or blocked) is stored in `audit_logs`.
- **Pending approvals queue** – blocked calls are inserted into `pending_approvals` for manual review.
- **REST API**
  - `POST /v1/tool-call` – receive tool‑call requests.
  - `GET /v1/approvals` – list pending approvals.
  - `POST /v1/approvals/{id}/resolve` – approve or deny a pending request.
- **Tiny dashboard** – view pending approvals and recent audit logs at `/dashboard`.
- **Demo scripts**
  - `test_demo.py` – automated sanity check (no LLM required).
  - `live_agent_demo.py` – interactive demo that uses a local Ollama LLM to simulate an AI agent deciding which tools to call.

## Project Structure

.
├── requirements.txt          # Python dependencies
├── database.py               # SQLite helper functions
├── registry.yaml             # Tool policy definitions
├── main.py                   # FastAPI server + dashboard
├── live_agent_demo.py        # Interactive LLM‑driven demo
├── test_demo.py              # Automated test (no LLM)
├── static/                   # (empty) place for CSS/JS
└── templates/
    └── dashboard.html        # Simple HTML dashboard

## Setup

### Prerequisites

- Python 3.9+ (tested with 3.11)
- [Ollama](https://ollama.com) (only needed for the interactive LLM demo)
- Git (optional, for cloning)

### 1. Clone the repository

```bash
git clone https://github.com/spajaypradeep/your_warden_mcp.git
cd your_warden_mcp

2. Install Python dependencies

pip install -r requirements.txt

3. (Optional) Pull an LLM model for the interactive demo

The demo defaults to llama3, but you can use any model Ollama provides. For a faster, lighter option, try Phi‑3:

ollama pull phi3   # or ollama pull llama3

If you prefer not to run the LLM demo, you can skip this step and use test_demo.py instead.

Running the Prototype

Start the services

Keep each command in its own terminal/pane.

Terminal A – Ollama server (only needed for live_agent_demo.py)

ollama serve

Terminal B – FastAPI proxy

python main.py

You should see:

INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)

Choose a demo

Option 1: Automated test (no LLM)

python test_demo.py

This will:
1. Call read_email (taints the session).
2. Attempt send_email – which will be blocked.
3. Print the pending approvals and audit log entries.

Option 2: Interactive LLM demo

python live_agent_demo.py

The script will:
- Ask the LLM which tool to call first (normally read_email).
- Simulate reading the email content.
- Ask the LLM what to do next.
- For a normal email, the LLM typically does nothing further.
- For a poisoned email, the LLM will likely chain read_private_file → send_email.
- The MCP Guard proxy will block the send_email call because the session is tainted.
- Pending approvals and audit logs are displayed.

View the Dashboard

Open a browser and navigate to:

http://localhost:8000/dashboard

You will see two tables:
- Pending Approvals – shows any blocked tool calls awaiting review.
- Recent Audit Log – shows the most recent 50 audit entries (including the blocked call and its reason).

Resolving a Pending Approval

You can approve or deny a pending request via the API:

# Example: approve pending approval with ID 1
curl -X POST "http://localhost:8000/v1/approvals/1/resolve" -H "Content-Type: application/json" -d '"approve"'

Refresh the dashboard to see the change.

How It Works

1. Policy loading – main.py reads registry.yaml and builds a dict TOOL_REGISTRY mapping tool names to their category (untrusted_content, private_data, outbound).
2. Taint tracking – a global set tainted_sessions stores session IDs that have executed an untrusted_content tool.
3. Tool‑call endpoint – when a request arrives:
   - If the session is already tainted and the requested tool is outbound, the call is blocked, logged, and inserted into pending_approvals.
   - If the tool is untrusted_content, the session is added to tainted_sessions.
   - Otherwise, the call is allowed and logged.
4. Dashboard – reads the SQLite tables and renders them with a simple Jinja2 template.

Extending the Prototype

- Add more tools – edit registry.yaml with new entries; no code changes needed.
- Change the block rule – modify the logic in main.py under the comment # Block if the session is already tainted and the tool is OUTBOUND.
- Persist tainted sessions – store them in a DB table instead of an in‑memory set if you need survivability across restarts.
- Enhance the UI – replace the inline CSS in templates/dashboard.html with a Bootstrap/Tailwind template or connect to a frontend framework.

License

This prototype is provided for educational and demonstration purposes. Feel free to adapt and extend it as needed.

---
Happy guarding! 🚀
