# 🍕 Restaurant Ordering Agent — LangGraph + Claude (Anthropic) + Fast‑MCP Menu Tool

This version mirrors your previous agent structure:
- **LangGraph** for the agent graph
- **Claude (Anthropic) via `langchain-anthropic`** for responses
- **System prompt** in `agent/prompts.py`
- **Fast‑MCP‑style tool**: `servers/menu_server.py`
- **State** with TypedDict, intent routing, and tool calls

## 🔑 Environment
Set your Claude API key:
- PowerShell (Windows): `$env:ANTHROPIC_API_KEY="sk-ant-..."`
- macOS/Linux: `export ANTHROPIC_API_KEY="sk-ant-..."`

## 🚀 Quickstart
```bash
python -m venv .venv
# Windows PowerShell
. .venv/Scripts/Activate.ps1
# macOS/Linux
# source .venv/bin/activate

pip install -r requirements.txt

# Start the Menu Tool server
uvicorn servers.menu_server:app --port 8001 --reload

# Run the agent (CLI streaming style)
python -m agent.run_agent

# Optional UI
streamlit run ui/app.py
```
## 🧠 Graph (Phase‑0 behavior)
- `classify_intent` → currently defaults to `browse` for demo
- `browse_menu` → calls `POST /tools/search_menu`
- `compose_llm_reply` → Claude formats a concise, friendly response using the system prompt

Next steps: add `update_cart`, `checkout`, `memory` servers,
and route with `tools_condition` like your pet agent.