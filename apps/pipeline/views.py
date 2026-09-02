import hmac
import json
import logging
import hashlib
import redis
from django.http import JsonResponse, StreamingHttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from apps.core.models import AgentRegistry
from apps.agents.registry import register_agent

logger = logging.getLogger(__name__)

def _verify_signature(request) -> bool:
    signature = request.headers.get("X-Pipeline-Signature", "")
    expected = hmac.new(
        settings.PIPELINE_WEBHOOK_SECRET.encode(),
        request.body,
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(signature, expected)





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

    if not _verify_signature(request):
        return JsonResponse({'error': 'Invalid signature'}, status=401)

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

    from django.core.exceptions import ValidationError

    if status == 'success':
        k8s_url = body.get('k8s_service_url')
        if not k8s_url:
            k8s_url = f"http://{agent.slug}-svc.{agent.developer.namespace}.svc.cluster.local"

        agent.status = 'live'
        agent.k8s_service_url = k8s_url
        agent.health_status = 'healthy'
        agent.rejection_reason = ''
        try:
            agent.save()
        except ValidationError as e:
            return JsonResponse({'error': f'Validation failed: {e.message_dict if hasattr(e, "message_dict") else str(e)}'}, status=400)

        # Cache in Redis for active routing lookup
        agent_data = {
            'name': agent.name,
            'slug': agent.slug,
            'version': agent.version,
            'developer__namespace': agent.developer.namespace,
            'input_type': agent.input_type,
            'output_types': agent.output_types,
            'age_groups': agent.age_groups,
            'subject_areas': agent.subject_areas,
            'health_status': agent.health_status,
            'sessions_today': agent.sessions_today,
            'k8s_service_url': agent.k8s_service_url,
            'status': agent.status,
            'agent_key': str(agent.developer.api_key),
            'type': 'third_party',
        }
        try:
            register_agent(agent_data)
        except Exception as e:
            logger.error(f"Failed to cache registered agent {slug} in Redis: {e}")

        # Publish final completion event to Redis Pub/Sub
        try:
            r = redis.Redis.from_url(settings.REDIS_URL)
            event_data = {
                'type': 'completion',
                'status': 'success',
                'slug': slug,
                'k8s_service_url': k8s_url
            }
            r.publish(f"pipeline_events:{slug}", json.dumps(event_data))
        except Exception as e:
            logger.error(f"Failed to publish success event to Redis: {e}")

        logger.info(f"Agent {slug} successfully activated and cached.")

    elif status == 'failure':
        reason = body.get('rejection_reason', 'Pipeline validation failed.')
        agent.status = 'rejected'
        agent.rejection_reason = reason
        try:
            agent.save()
        except ValidationError as e:
            return JsonResponse({'error': f'Validation failed: {e.message_dict if hasattr(e, "message_dict") else str(e)}'}, status=400)

        # Publish final completion event to Redis Pub/Sub
        try:
            r = redis.Redis.from_url(settings.REDIS_URL)
            event_data = {
                'type': 'completion',
                'status': 'failure',
                'slug': slug,
                'rejection_reason': reason
            }
            r.publish(f"pipeline_events:{slug}", json.dumps(event_data))
        except Exception as e:
            logger.error(f"Failed to publish failure event to Redis: {e}")

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


#Deadcode or perhaps later on can be used for pipeline step updates and SSE streaming of events.
@csrf_exempt
def pipeline_step_update(request, slug):
    """
    Accept signed step updates from the GitHub Actions pipeline.
    Payload:
    {
        "step": "schema_validation" | "security_scan" | "smoke_test" | "deploy",
        "status": "running" | "success" | "failure",
        "message": "Detail or failure message..."
    }
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    if not _verify_signature(request):
        return JsonResponse({'error': 'Invalid signature'}, status=401)

    try:
        body = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    step = body.get('step')
    status = body.get('status')
    message = body.get('message', '')

    if not step or not status:
        return JsonResponse({'error': 'Missing step or status in payload'}, status=400)

    # Save failure message to DB row if step failed
    if status == 'failure' and message:
        try:
            agent = AgentRegistry.objects.get(slug=slug)
            agent.status = 'rejected'
            agent.rejection_reason = message
            agent.save(update_fields=['status', 'rejection_reason'])
        except Exception as e:
            logger.error(f"Failed to record step rejection reason for {slug}: {e}")

    # Publish step update to Redis Pub/Sub channel
    try:
        r = redis.Redis.from_url(settings.REDIS_URL)
        event_data = {
            'type': 'step_update',
            'step': step,
            'status': status,
            'message': message,
        }
        r.publish(f"pipeline_events:{slug}", json.dumps(event_data))
    except Exception as e:
        logger.error(f"Failed to publish step update to Redis for {slug}: {e}")
        return JsonResponse({'error': f'Redis publish failed: {e}'}, status=500)

    return JsonResponse({'status': 'ok'})


#Deadcode or perhaps later on can be used for pipeline step updates and SSE streaming of events.
def pipeline_events_stream(request, slug):
    """
    Server-Sent Events endpoint streaming pipeline progress updates to the browser.
    """
    def event_generator():
        import time
        r = redis.Redis.from_url(settings.REDIS_URL)
        pubsub = r.pubsub()
        pubsub.subscribe(f"pipeline_events:{slug}")
        
        # Send initial connection event
        yield f"data: {json.dumps({'type': 'connected'})}\n\n"
        
        start_time = time.time()
        try:
            while time.time() - start_time < 25:
                message = pubsub.get_message(timeout=1.0)
                if message and message['type'] == 'message':
                    data = message['data'].decode('utf-8')
                    yield f"data: {data}\n\n"
                    try:
                        parsed = json.loads(data)
                        if parsed.get('type') == 'completion':
                            break
                    except Exception:
                        pass
                else:
                    yield ": heartbeat\n\n"
        except GeneratorExit:
            logger.info(f"SSE stream generator exit for slug {slug}")
        finally:
            try:
                pubsub.unsubscribe(f"pipeline_events:{slug}")
                pubsub.close()
            except Exception:
                pass
            
    response = StreamingHttpResponse(event_generator(), content_type="text/event-stream")
    response['Cache-Control'] = 'no-cache'
    response['X-Accel-Buffering'] = 'no'  # Disable buffering in Nginx/proxies
    return response
