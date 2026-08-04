from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from apps.core.models import AgentRegistry


@login_required
def browse(request):
    """Marketplace browse view listing live registered agents."""
    live_agents = AgentRegistry.objects.filter(status='live')
    
    # Simple logic for featured agents: take up to 3 live agents
    featured_agents = live_agents[:3]
    
    context = {
        'user_type': request.GET.get('type', 'learner'),
        'featured_agents': featured_agents,
        'agents': live_agents,
    }
    return render(request, 'marketplace/browse.html', context)
