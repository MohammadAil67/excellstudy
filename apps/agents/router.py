"""
Plain HTTP relay to an agent pod. This file does NOT look up agents,
does NOT touch Redis/Postgres, and does NOT decide which agent to call.
The caller (views.py) must resolve the agent via registry.get_agent()
first and pass the result in.

route_agent() / subject-based auto-matching was removed intentionally:
this platform has no flow where the backend guesses which agent a
learner wants. The learner always picks an explicit agent, and its
slug is always known before this module is called.
"""
import httpx
from apps.agents.exceptions import (
    AgentTimeoutError,
    AgentUnavailableError,
)


async def forward_to_agent(agent: dict, input_payload: dict, learner_context: dict, request_id: str) -> dict:
    """
    Forward a single request to an already-resolved agent's service URL.

    agent: dict from registry.get_agent() — must contain k8s_service_url or fallback slug/namespace.
    Raises AgentTimeoutError / AgentUnavailableError on failure.
    """
    service_url = agent.get('k8s_service_url')
    if not service_url:
        slug = agent.get('slug', '')
        namespace = agent.get('developer__namespace', '')
        if not namespace:
            namespace = "platform"
        service_url = f"http://{slug}-svc.{namespace}.svc.cluster.local"

    invoke_url = f"{service_url.rstrip('/')}/invoke"
    payload = {"input": input_payload, "context": learner_context}

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(invoke_url, json=payload)
        return {
            "status_code": response.status_code,
            "body": _safe_json(response),
        }
    except httpx.TimeoutException as exc:
        raise AgentTimeoutError(
            request_id=request_id, agent_name=agent.get("name", agent.get("slug", "unknown")),
            detail=f"timeout calling {invoke_url}: {exc}",
        )
    except (httpx.ConnectError, httpx.HTTPError, Exception) as exc:
        raise AgentUnavailableError(
            request_id=request_id, agent_name=agent.get("name", agent.get("slug", "unknown")),
            detail=f"connect error calling {invoke_url}: {exc}",
        )


def _safe_json(response: httpx.Response) -> dict:
    try:
        return response.json()
    except Exception:
        return {"raw": response.text}