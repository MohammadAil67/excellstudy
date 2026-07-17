import json
import logging
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from apps.core.models import AgentRegistry
from apps.agents.registry import register_agent

logger = logging.getLogger(__name__)


@csrf_exempt
def pipeline_webhook(request):
    """
    Accept completion webhook trigger from GitHub Actions or external runner.
    Payload JSON structure:
    {
        "agent_slug": "dev-alice-math-helper",
        "status": "success" | "failure",
        "k8s_service_url": "http://...",  # required if success
        "rejection_reason": "mismatch..."  # required if failure
    }
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    try:
        body = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    slug = body.get('agent_slug')
    status = body.get('status')

    if not slug or not status:
        return JsonResponse({'error': 'Missing agent_slug or status in payload'}, status=400)

    try:
        agent = AgentRegistry.objects.get(slug=slug)
    except AgentRegistry.DoesNotExist:
        return JsonResponse({'error': f'Agent registry row not found for slug: {slug}'}, status=404)

    if status == 'success':
        k8s_url = body.get('k8s_service_url')
        if not k8s_url:
            return JsonResponse({'error': 'Missing k8s_service_url for successful status'}, status=400)

        agent.status = 'live'
        agent.k8s_service_url = k8s_url
        agent.health_status = 'healthy'
        agent.rejection_reason = ''
        agent.save()

        # Cache in Redis for active routing lookup
        agent_data = {
            'name': agent.name,
            'slug': agent.slug,
            'version': agent.version,
            'developer__namespace': agent.developer.namespace,
            'subject_areas': agent.subject_areas,
            'health_status': agent.health_status,
            'sessions_today': agent.sessions_today,
            'k8s_service_url': agent.k8s_service_url,
            'status': agent.status,
        }
        try:
            register_agent(agent_data)
        except Exception as e:
            logger.error(f"Failed to cache registered agent {slug} in Redis: {e}")

        logger.info(f"Agent {slug} successfully activated and cached.")

    elif status == 'failure':
        reason = body.get('rejection_reason', 'Pipeline validation failed.')
        agent.status = 'rejected'
        agent.rejection_reason = reason
        agent.save()

        logger.info(f"Agent {slug} was rejected: {reason}")

    else:
        return JsonResponse({'error': f'Invalid status: {status}'}, status=400)

    return JsonResponse({'slug': slug, 'status': agent.status})


def agent_pipeline_status(request, slug):
    """GET - Query the database for the current pipeline validation status of an agent."""
    try:
        agent = AgentRegistry.objects.get(slug=slug)
    except AgentRegistry.DoesNotExist:
        return JsonResponse({'error': f'Agent not found for slug: {slug}'}, status=404)

    return JsonResponse({
        'name': agent.name,
        'slug': agent.slug,
        'version': agent.version,
        'status': agent.status,
        'rejection_reason': agent.rejection_reason,
        'health_status': agent.health_status,
        'updated_at': agent.updated_at.isoformat() if agent.updated_at else None,
    })
