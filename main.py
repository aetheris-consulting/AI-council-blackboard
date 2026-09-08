"""Horizon-native FastMCP entrypoint for the Council Blackboard System.

Deploy in Prefect Horizon with the entrypoint:
    main.py:mcp

The React/TypeScript application in this repository remains the companion UI.
This module provides a standalone FastMCP server that mirrors the core Council
Blackboard operations so Horizon can deploy the project directly from GitHub.
"""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from hashlib import sha256
from typing import Any, Literal
from uuid import uuid4

from fastmcp import FastMCP


Mode = Literal["brainstorming", "project_creation", "story_writing", "coding_embodiment"]
ItemType = Literal["concept", "task", "code", "character", "general"]
RuleType = Literal["round_robin", "socratic_debate", "bid_priority", "consensus_vote"]
Decision = Literal["approve", "reject"]


mcp = FastMCP(
    "Council Blackboard",
    instructions=(
        "Shared blackboard and AI-council coordination server. Mutating operations are "
        "explicit tools; proposals above the configured heuristic boundary remain pending "
        "for human approval. The current MVP stores state in-process and is not durable "
        "across redeployments or process replacement."
    ),
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex[:12]}"


def _default_state() -> dict[str, Any]:
    return {
        "id": "blackboard_main",
        "title": "Council Blackboard",
        "mode": "brainstorming",
        "cycleIndex": 1,
        "epsilon_x_global": 0.05,
        "hitlPaused": False,
        "items": [],
        "proposals": [],
        "activeAgents": [
            {"id": "agent_architect", "name": "Lead Architect", "role": "lead_architect", "enabled": True},
            {"id": "agent_sentinel", "name": "Security Sentinel", "role": "security_sentinel", "enabled": True},
            {"id": "agent_critic", "name": "Critic", "role": "critic", "enabled": True},
            {"id": "agent_creative", "name": "Creative Director", "role": "creative_director", "enabled": True},
        ],
        "updatedAt": _now(),
    }


def _default_colloquium() -> dict[str, Any]:
    return {
        "id": "colloquium_main",
        "topic": "Define the current problem or objective.",
        "ruleOfMotion": {"type": "round_robin", "consensusThreshold": 0.85},
        "currentSpeakerIndex": 0,
        "participatingAgentIds": ["agent_architect", "agent_sentinel", "agent_critic", "agent_creative"],
        "consensusReached": False,
        "consensusScore": 0.0,
        "sharedWorkingMemory": "",
        "messages": [],
        "updatedAt": _now(),
    }


BLACKBOARD = _default_state()
COLLOQUIUM = _default_colloquium()
AUDIT_LOG: list[dict[str, Any]] = []


def _audit(tool: str, arguments: dict[str, Any], result: dict[str, Any]) -> None:
    AUDIT_LOG.insert(0, {"id": _id("audit"), "timestamp": _now(), "tool": tool, "arguments": deepcopy(arguments), "result": deepcopy(result)})
    del AUDIT_LOG[100:]


def _heuristic_residual(title: str, content: str) -> float:
    """Return a deterministic MVP heuristic in [0.01, 0.12]."""
    digest = sha256(f"{title}\n{content}".encode("utf-8")).digest()
    bucket = int.from_bytes(digest[:2], "big") / 65535
    length_penalty = min(len(content) / 20_000, 1.0) * 0.02
    return round(min(0.12, 0.01 + bucket * 0.09 + length_penalty), 4)


@mcp.tool
def system_status() -> dict[str, Any]:
    """Return deployment identity, state model, and current chamber counts."""
    return {
        "server": "Council Blackboard",
        "runtime": "FastMCP / Prefect Horizon compatible",
        "horizon_entrypoint": "main.py:mcp",
        "persistence": "in-memory MVP; resets on process replacement/redeploy",
        "blackboard_items": len(BLACKBOARD["items"]),
        "pending_proposals": len(BLACKBOARD["proposals"]),
        "colloquium_messages": len(COLLOQUIUM["messages"]),
        "mode": BLACKBOARD["mode"],
        "updated_at": BLACKBOARD["updatedAt"],
    }


@mcp.tool
def blackboard_get_state(mode: Mode | None = None) -> dict[str, Any]:
    """Retrieve the shared Council Blackboard state."""
    state = deepcopy(BLACKBOARD)
    if mode:
        state["items"] = [item for item in state["items"] if mode in item.get("tags", [])]
    state["itemCount"] = len(state["items"])
    state["proposalCount"] = len(state["proposals"])
    state["activeAgentCount"] = len(state["activeAgents"])
    return state


@mcp.tool
def blackboard_add_item(title: str, content: str, type: ItemType = "concept", author_name: str = "MCP Agent", tags: list[str] | None = None) -> dict[str, Any]:
    """Commit a new item directly to the shared blackboard."""
    if not title.strip() or not content.strip():
        raise ValueError("title and content are required")
    item = {
        "id": _id("item"), "title": title.strip(), "content": content, "type": type,
        "author": {"name": author_name, "isAgent": True, "role": "mcp_connected_agent"},
        "version": 1, "timestamp": _now(), "status": "active",
        "tags": list(dict.fromkeys([*(tags or []), BLACKBOARD["mode"], "mcp"])),
    }
    BLACKBOARD["items"].insert(0, item)
    BLACKBOARD["cycleIndex"] += 1
    BLACKBOARD["updatedAt"] = _now()
    result = {"status": "committed", "item": item, "cycleIndex": BLACKBOARD["cycleIndex"]}
    _audit("blackboard_add_item", {"title": title, "type": type}, result)
    return result


@mcp.tool
def blackboard_propose_input(agent_name: str, title: str, content: str, role: str = "lead_architect", type: ItemType = "concept", justification: str = "") -> dict[str, Any]:
    """Submit a candidate mutation through the Human-In-The-Loop boundary."""
    if not title.strip() or not content.strip():
        raise ValueError("title and content are required")
    residual = _heuristic_residual(title, content)
    epsilon = float(BLACKBOARD["epsilon_x_global"])
    auto_accepted = residual <= epsilon
    proposal = {
        "id": _id("proposal"), "agentId": f"agent_mcp_{role}", "agentName": agent_name,
        "agentRole": role, "title": title, "proposedContent": content, "contentType": type,
        "rationale": justification or "Proposal submitted via FastMCP",
        "metrics": {"lambda": residual, "epsilon_x": epsilon, "meetsThreshold": auto_accepted, "metricSource": "deterministic_heuristic_mvp"},
        "timestamp": _now(), "status": "approved" if auto_accepted else "pending_hitl",
        "cycleIndex": BLACKBOARD["cycleIndex"],
    }
    if auto_accepted:
        item = {
            "id": _id("item"), "title": title, "content": content, "type": type,
            "author": {"name": agent_name, "isAgent": True, "role": role},
            "version": 1, "timestamp": _now(), "status": "active",
            "tags": ["auto-accepted", BLACKBOARD["mode"], "mcp"], "sourceProposalId": proposal["id"],
        }
        BLACKBOARD["items"].insert(0, item)
    else:
        BLACKBOARD["proposals"].insert(0, proposal)
    BLACKBOARD["cycleIndex"] += 1
    BLACKBOARD["updatedAt"] = _now()
    result = {
        "proposalId": proposal["id"], "status": proposal["status"], "autoAccepted": auto_accepted,
        "metrics": proposal["metrics"],
        "reason": f"heuristic lambda {residual:.4f} {'<=' if auto_accepted else '>'} epsilon_x {epsilon:.4f}; {'auto-accepted' if auto_accepted else 'held for HITL approval'}",
    }
    _audit("blackboard_propose_input", {"agent_name": agent_name, "title": title}, result)
    return result


@mcp.tool
def blackboard_approve_proposal(proposal_id: str, action: Decision, feedback: str = "") -> dict[str, Any]:
    """Approve or reject a pending proposal at the HITL supervisory boundary."""
    index = next((i for i, p in enumerate(BLACKBOARD["proposals"]) if p["id"] == proposal_id), -1)
    if index < 0:
        raise ValueError(f"proposal '{proposal_id}' not found")
    proposal = BLACKBOARD["proposals"].pop(index)
    item = None
    if action == "approve":
        item = {
            "id": _id("item"), "title": proposal["title"], "content": proposal["proposedContent"], "type": proposal["contentType"],
            "author": {"name": proposal["agentName"], "isAgent": True, "role": proposal["agentRole"]},
            "version": 1, "timestamp": _now(), "status": "active",
            "tags": ["hitl-approved", BLACKBOARD["mode"], "mcp"], "sourceProposalId": proposal["id"],
        }
        BLACKBOARD["items"].insert(0, item)
    BLACKBOARD["cycleIndex"] += 1
    BLACKBOARD["updatedAt"] = _now()
    result = {"status": "approved" if action == "approve" else "rejected", "proposalId": proposal_id, "feedback": feedback, "item": item}
    _audit("blackboard_approve_proposal", {"proposal_id": proposal_id, "action": action}, result)
    return result


@mcp.tool
def blackboard_set_mode(mode: Mode) -> dict[str, Any]:
    """Switch the operating mode of the Council Blackboard."""
    BLACKBOARD["mode"] = mode
    BLACKBOARD["updatedAt"] = _now()
    result = {"status": "updated", "mode": mode}
    _audit("blackboard_set_mode", {"mode": mode}, result)
    return result


@mcp.tool
def colloquium_get_session(limit_messages: int = 25) -> dict[str, Any]:
    """Inspect the current AI-first colloquium session."""
    limit_messages = max(1, min(limit_messages, 200))
    session = deepcopy(COLLOQUIUM)
    session["totalMessagesCount"] = len(session["messages"])
    session["recentMessages"] = session.pop("messages")[-limit_messages:]
    participants = session["participatingAgentIds"]
    session["activeSpeakerId"] = participants[session["currentSpeakerIndex"]] if participants else None
    return session


@mcp.tool
def colloquium_interject(directive: str, sender_name: str = "Supervisor (HITL)") -> dict[str, Any]:
    """Insert a high-priority supervisor directive into the colloquium stream."""
    if not directive.strip():
        raise ValueError("directive is required")
    packet = {
        "id": _id("packet"), "sequenceNumber": len(COLLOQUIUM["messages"]) + 1, "timestamp": _now(),
        "senderId": "human_supervisor", "senderName": sender_name, "senderRole": "hitl_supervisor",
        "intent": "SUPERVISOR_DIRECTIVE", "content": directive,
    }
    COLLOQUIUM["messages"].append(packet)
    COLLOQUIUM["updatedAt"] = _now()
    result = {"status": "interjected", "packet": packet}
    _audit("colloquium_interject", {"sender_name": sender_name}, result)
    return result


@mcp.tool
def colloquium_commit_to_blackboard(title: str, content: str, type: ItemType = "concept", tags: list[str] | None = None) -> dict[str, Any]:
    """Commit a distilled colloquium outcome into the shared blackboard."""
    return blackboard_add_item(title=title, content=content, type=type, author_name="Council Colloquium", tags=["colloquium", *(tags or [])])


@mcp.tool
def colloquium_update_rule_of_motion(rule_type: RuleType | None = None, consensus_threshold: float | None = None, topic: str | None = None) -> dict[str, Any]:
    """Update colloquium turn structure, consensus threshold, or active topic."""
    if rule_type is not None:
        COLLOQUIUM["ruleOfMotion"]["type"] = rule_type
    if consensus_threshold is not None:
        if not 0.0 <= consensus_threshold <= 1.0:
            raise ValueError("consensus_threshold must be between 0.0 and 1.0")
        COLLOQUIUM["ruleOfMotion"]["consensusThreshold"] = consensus_threshold
    if topic is not None and topic.strip():
        COLLOQUIUM["topic"] = topic.strip()
    COLLOQUIUM["updatedAt"] = _now()
    result = {"status": "updated", "topic": COLLOQUIUM["topic"], "ruleOfMotion": deepcopy(COLLOQUIUM["ruleOfMotion"])}
    _audit("colloquium_update_rule_of_motion", {"rule_type": rule_type, "consensus_threshold": consensus_threshold, "topic": topic}, result)
    return result


@mcp.tool
def audit_get_recent(limit: int = 25) -> list[dict[str, Any]]:
    """Return recent mutating MCP calls from the in-process audit log."""
    return deepcopy(AUDIT_LOG[:max(1, min(limit, 100))])


@mcp.resource("blackboard://state")
def blackboard_state_resource() -> dict[str, Any]:
    """Current complete blackboard state."""
    return deepcopy(BLACKBOARD)


@mcp.resource("colloquium://session")
def colloquium_session_resource() -> dict[str, Any]:
    """Current complete colloquium session."""
    return deepcopy(COLLOQUIUM)


@mcp.resource("agents://manifest")
def agent_manifest_resource() -> list[dict[str, Any]]:
    """Current agent manifest."""
    return deepcopy(BLACKBOARD["activeAgents"])


@mcp.prompt
def deliberate_problem(problem_statement: str, constraints: str = "") -> str:
    """Create a council-deliberation instruction using current shared-state boundaries."""
    return (
        "Council Deliberation Request\n"
        f"Problem: {problem_statement}\n"
        f"Constraints: {constraints or 'Use the current blackboard and HITL boundary.'}\n"
        f"Operating mode: {BLACKBOARD['mode']}\n"
        f"HITL epsilon_x: {BLACKBOARD['epsilon_x_global']}\n"
        "Evaluate the problem, surface disagreements, propose artifacts, and route any state-changing proposal through the appropriate blackboard tool. Provide concise decision rationale, not hidden chain-of-thought."
    )


@mcp.prompt
def evaluate_blackboard_proposal(proposal_id: str) -> str:
    """Create a supervisory review prompt for a pending blackboard proposal."""
    proposal = next((p for p in BLACKBOARD["proposals"] if p["id"] == proposal_id), None)
    return (
        f"Evaluate Council Blackboard proposal {proposal_id}.\nProposal: {proposal!r}\nCurrent epsilon_x: {BLACKBOARD['epsilon_x_global']}\n"
        "Assess correctness, risk, scope, and whether approval is justified. Return a concise decision rationale and then use blackboard_approve_proposal if authorized."
    )


if __name__ == "__main__":
    mcp.run()
