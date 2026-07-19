import json
import logging
from asgiref.sync import sync_to_async
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

from apps.agents.registry import get_agent, list_agents
from apps.agents.router import forward_to_agent
from apps.agents.exceptions import (
    AgentInvocationError,
    AgentNotFoundError,
    InputValidationError,
)
from apps.core.input_output_types import validate_input_payload

logger = logging.getLogger("apps.agents.views")


def _error_envelope(error_code: str, message: str, detail: str, request_id: str, status: int) -> JsonResponse:
    return JsonResponse(
        {
            "status": "error",
            "request_id": request_id,
            "error_code": error_code,
            "message": message,
            "detail": detail,
        },
        status=status,
    )


@csrf_exempt
async def invoke_agent(request, agent_slug):
    """
    Plain HTTP relay: learner UI -> a SPECIFIC agent chosen explicitly
    by the learner (agent_slug comes from the URL they're already on).
    """
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed"}, status=405)

    request_id = getattr(request, "request_id", "unknown")

    try:
        body = json.loads(request.body)
    except json.JSONDecodeError as exc:
        return _error_envelope(
            "VALIDATION_FAILED", "Invalid request format.", str(exc),
            request_id, 400,
        )

    input_payload = body.get("input")
    learner_context = body.get("context", {})

    if not input_payload:
        return _error_envelope(
            "VALIDATION_FAILED", "'input' is required.", "missing 'input' field",
            request_id, 400,
        )

    learner_id = learner_context.get("learner_id")
    request.mcp_learner_id = str(learner_id) if learner_id else "unknown"

    # get_agent() uses django.core.cache (sync) — wrap for the async view
    agent = await sync_to_async(get_agent)(agent_slug)
    if not agent:
        exc = AgentNotFoundError(request_id, agent_slug, "no live agent with this slug")
        return _error_envelope("NOT_FOUND", exc.message, exc.detail, request_id, 404)

    request.mcp_agent_name = agent["name"]  # fixed: was the URL before, not the name

    try:
        validate_input_payload(agent["input_type"], input_payload)
    except Exception as exc:
        err = InputValidationError(request_id, agent["name"], str(exc))
        return _error_envelope("VALIDATION_FAILED", err.message, err.detail, request_id, 422)

    try:
        result = await forward_to_agent(agent, input_payload, learner_context, request_id)
        request.mcp_status = "success"

        # Record learner progress dynamically
        try:
            from django.utils import timezone
            from apps.core.models import Learner, LearnerProgress, AgentRegistry

            def _record_progress():
                try:
                    l_id = int(learner_id) if str(learner_id).isdigit() else None
                    if not l_id:
                        return
                    learner_obj = Learner.objects.filter(user_id=l_id).first()
                    agent_obj = AgentRegistry.objects.filter(slug=agent_slug).first()
                    if not learner_obj or not agent_obj:
                        return

                    score = None
                    if isinstance(result.get("body"), dict):
                        score_val = result["body"].get("score")
                        if isinstance(score_val, (int, float)):
                            score = int(score_val)

                    LearnerProgress.objects.create(
                        learner=learner_obj,
                        agent_used=agent_obj,
                        completed_at=timezone.now(),
                        score=score
                    )
                except Exception as e:
                    logger.error(f"Failed to record learner progress: {e}")

            if learner_id and str(learner_id) != "smoke-test":
                await sync_to_async(_record_progress)()
        except Exception as e:
            logger.error(f"Error in progress tracking block: {e}")

        return JsonResponse(
            {"status": "success", "request_id": request_id, "data": result["body"]},
            status=result["status_code"],
        )
    except AgentInvocationError as exc:
        request.mcp_status = "error"
        logger.error(f"invoke_agent failed (request_id={request_id}, agent={agent_slug}): {exc.detail}")
        status_code = 504 if isinstance(exc, type(exc)) and "Timeout" in type(exc).__name__ else 503
        error_code = "AGENT_TIMEOUT" if status_code == 504 else "AGENT_UNAVAILABLE"
        return _error_envelope(error_code, exc.message, exc.detail, request_id, status_code)


@csrf_exempt
def agent_list(request):
    """GET - List all live agents (marketplace/browse use case)."""
    if request.method != 'GET':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    return JsonResponse({'status': 'success', 'data': list_agents()})


@csrf_exempt
def agent_health(request, slug):
    """GET - Health check for a specific agent by slug."""
    if request.method != 'GET':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    agent = get_agent(slug)
    if not agent:
        return JsonResponse({'status': 'error', 'error_code': 'NOT_FOUND', 'message': 'Agent not found'}, status=404)
    return JsonResponse({'status': 'success', 'data': {'slug': slug, 'health': agent.get('health_status', 'unknown')}})