# Prefect Horizon deployment

This repository includes a Horizon-native FastMCP server in `main.py`.

## Horizon settings

- **Repository:** `aetheris-consulting/AI-council-blackboard`
- **Entrypoint:** `main.py:mcp`
- **Dependency file:** `pyproject.toml`
- **MCP endpoint after deploy:** Horizon provides the managed `/mcp` URL.

## Local validation

```bash
uv sync
uv run fastmcp inspect main.py:mcp
uv run fastmcp run main.py:mcp
```

For an HTTP development endpoint:

```bash
uv run fastmcp run main.py:mcp --transport http --port 8000
```

The local endpoint is then `http://127.0.0.1:8000/mcp`.

## Architecture

`main.py:mcp` is the production-facing Horizon MCP surface. The React/Vite + Express TypeScript application remains a companion human/C2 UI and also contains an earlier hand-written MCP JSON-RPC router at `server/mcpServer.ts`.

For the MVP, the Horizon server keeps blackboard, colloquium, and audit state in memory. State can reset when Horizon replaces a process or redeploys the service. Durable shared state should be the next infrastructure upgrade before multi-instance production use.

## Current Horizon tool surface

- `system_status`
- `blackboard_get_state`
- `blackboard_add_item`
- `blackboard_propose_input`
- `blackboard_approve_proposal`
- `blackboard_set_mode`
- `colloquium_get_session`
- `colloquium_interject`
- `colloquium_commit_to_blackboard`
- `colloquium_update_rule_of_motion`
- `audit_get_recent`

Resources:

- `blackboard://state`
- `colloquium://session`
- `agents://manifest`

Prompts:

- `deliberate_problem`
- `evaluate_blackboard_proposal`
