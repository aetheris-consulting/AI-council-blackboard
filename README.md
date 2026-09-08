# Council Blackboard System — FastMCP / Prefect Horizon

Council Blackboard is an AI-first shared-state and multi-agent deliberation system with a Human-In-The-Loop (HITL) boundary, blackboard state, colloquium/chamber coordination, audit visibility, and a companion React control interface.

## Primary deployment: Prefect Horizon

This repository is configured to deploy as an MCP server in **Prefect Horizon**.

**Horizon entrypoint:**

```text
main.py:mcp
```

Horizon detects `pyproject.toml`, installs `fastmcp==4.0.3`, imports the `mcp` object from `main.py`, and exposes the managed MCP endpoint.

### Deploy

1. Connect this GitHub repository to Prefect Horizon.
2. Create a server/project from `aetheris-consulting/AI-council-blackboard`.
3. Set the entrypoint to `main.py:mcp`.
4. Deploy and validate the tools in Horizon Inspector or ChatMCP.

See [`HORIZON.md`](HORIZON.md) for the exact deployment and local-validation commands.

## MCP capabilities

The Horizon-native server currently exposes blackboard state operations, HITL proposal routing and approval, operating-mode control, colloquium session inspection/interjection, colloquium-to-blackboard commits, rule-of-motion updates, resources, prompts, and a small in-process audit log.

The MVP is intentionally explicit about one limitation: **Horizon state is currently in-memory and non-durable**. It can reset on process replacement or redeploy. A durable shared-state backend should be added before multi-instance production use.

## Companion C2 / web UI

The original application remains in this repository as a React/Vite + Express TypeScript interface.

```bash
npm install
npm run dev
```

The web application includes:

- Council Blackboard UI
- AI-first colloquium/chamber UI
- HITL stage and proposal review
- agent panels and rule-of-motion controls
- connector and room UI
- an earlier hand-written MCP JSON-RPC router in `server/mcpServer.ts`

The Horizon-facing `main.py:mcp` server is the recommended MCP deployment surface. The TypeScript router is retained for the companion application and future consolidation.

## Repository layout

```text
main.py                 # FastMCP server for Prefect Horizon
pyproject.toml          # Horizon/Python dependency declaration
HORIZON.md              # Horizon deployment notes
server/mcpServer.ts     # Existing TypeScript MCP JSON-RPC implementation
server.ts               # Express/Vite companion app server
src/                    # React C2 / chamber UI
```

## Environment

The Horizon-native MCP server requires no provider API key for its current core state-management tools.

The companion TypeScript application can use:

```text
GEMINI_API_KEY=...
```

Do not commit real credentials. `.env*` files remain ignored except for `.env.example`.

## Validation notes

The source was reviewed before import for obvious embedded credentials. No live provider/API credential was found in the archive. The companion app does contain demo/session tokens and simulated/fallback behavior; those should not be treated as production authentication or durable governance controls.
