import logging
from django.utils import timezone
from datetime import timedelta
from celery import shared_task
from apps.core.models import AgentRegistry

logger = logging.getLogger(__name__)


@shared_task
def expire_stale_pending_agents():
    """
    Daily cleanup task that auto-rejects pending registrations that have not
    received an image package push within 7 days.
    """
    cutoff = timezone.now() - timedelta(days=7)
    stale_agents = AgentRegistry.objects.filter(
        status='pending',
        created_at__lt=cutoff
    )

    count = stale_agents.count()
    if count > 0:
        logger.info(f"Expiring {count} stale pending agent registrations.")
        for agent in stale_agents:
            agent.status = 'rejected'
            agent.rejection_reason = "Pending registration expired: no package pushed within 7 days."
            agent.save()
    else:
        logger.info("No stale pending agent registrations found.")

    return count
