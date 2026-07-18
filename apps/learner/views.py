import os
from django.shortcuts import render, get_object_or_404
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from rest_framework.decorators import api_view
from rest_framework.response import Response

from django.contrib.auth.decorators import login_required
from apps.core.models import AgentRegistry, Learner, LearnerProgress


@login_required
def dashboard(request):
    """Learner dashboard showing live agents and dynamic recent activity from the database."""
    # Get or create learner profile to prevent crashes
    learner_profile, _ = Learner.objects.get_or_create(user=request.user)
    
    active_agents = AgentRegistry.objects.filter(status='live')
    
    # Query progress records for live agents used by this learner
    progress_entries = LearnerProgress.objects.filter(
        learner=learner_profile,
        agent_used__status='live'
    ).select_related('module', 'agent_used').order_by('-completed_at')[:5]
    
    recent_activity = []
    for entry in progress_entries:
        recent_activity.append({
            'module': entry.module.title if entry.module else 'General Lesson',
            'agent': entry.agent_used.name if entry.agent_used else 'AI Agent',
            'score': entry.score,
            'timestamp': entry.completed_at,
            'icon': 'check-circle'
        })

    # Query current module if assigned
    current_module_data = None
    if learner_profile.current_module:
        agent_name = "AI Tutor"
        if learner_profile.current_module.course:
            agents = learner_profile.current_module.course.agents.filter(status='live')
            if agents.exists():
                agent_name = agents.first().name
        
        current_module_data = {
            'title': learner_profile.current_module.title,
            'course': learner_profile.current_module.course.name if learner_profile.current_module.course else 'General Course',
            'agent_name': agent_name,
            'estimated_time': '25 min',
        }

    context = {
        'user_type': 'learner',
        'learner': {
            'user': request.user,
        },
        'current_module': current_module_data,
        'active_agents': active_agents,
        'recent_activity': recent_activity,
    }
    return render(request, 'learner/dashboard.html', context)


class AgentSessionView(LoginRequiredMixin, View):
    """
    ONE view for every agent on the platform. agent_slug comes from the URL.
    """

    def get(self, request, agent_slug):
        agent = get_object_or_404(
            AgentRegistry, slug=agent_slug, status="live"
        )
        return render(request, "learner/session.html", {
            "agent": agent,
            "input_type": agent.input_type,
            "output_types": agent.output_types,
            "invoke_url": f"/api/v1/agents/{agent.slug}/invoke/",
        })


def upload_to_storage(file, folder):
    """Save a file to local storage and return its public URL."""
    safe_folder = folder.replace("..", "")
    filename = default_storage.get_valid_name(file.name)
    path = os.path.join(safe_folder, filename)
    saved_path = default_storage.save(path, ContentFile(file.read()))
    return default_storage.url(saved_path)


class LearnerImageUploadView(LoginRequiredMixin, View):
    """
    Learner-facing image upload, used by the image_upload input partial.
    """

    def post(self, request):
        file = request.FILES.get("file")
        if not file:
            return JsonResponse({"status": "error", "message": "No file provided"}, status=400)

        # Validate file size (10MB limit)
        if file.size > 10 * 1024 * 1024:
            return JsonResponse({"status": "error", "message": "File too large. Max size is 10MB."}, status=400)

        # Validate mime type
        content_type = getattr(file, 'content_type', '')
        if not content_type.startswith('image/'):
            return JsonResponse({"status": "error", "message": "Invalid file type. Only images allowed."}, status=400)

        url = upload_to_storage(file, folder=f"learner-uploads/{request.user.id}")
        return JsonResponse({"status": "success", "data": {"image_url": url}})


@api_view(['GET'])
def learner_context_api(request):
    """Learner context API endpoint."""
    return Response({
        'learner_id': request.user.id if request.user.is_authenticated else 1,
        'skill_levels': {'mathematics': 72, 'science': 45, 'english': 88},
        'learning_style': 'visual',
        'mood_signal': 'focused',
    })
