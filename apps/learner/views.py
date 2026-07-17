import os
from django.shortcuts import render, get_object_or_404
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from rest_framework.decorators import api_view
from rest_framework.response import Response

from apps.core.models import AgentRegistry


def dashboard(request):
    """Learner dashboard showing live agents from the database."""
    active_agents = AgentRegistry.objects.filter(status='live')

    context = {
        'user_type': 'learner',
        'learner': {
            'user': {'first_name': request.user.first_name if request.user.is_authenticated else 'Alex'},
            'streak': 12,
        },
        'skills': [
            {'name': 'Mathematics', 'score': 72, 'icon': 'calculator'},
            {'name': 'Science', 'score': 45, 'icon': 'flask-conical'},
            {'name': 'English', 'score': 88, 'icon': 'book-open'},
            {'name': 'History', 'score': 33, 'icon': 'landmark'},
            {'name': 'Geography', 'score': 61, 'icon': 'globe'},
            {'name': 'Coding', 'score': 79, 'icon': 'code'},
        ],
        'current_module': {
            'title': 'Quadratic Equations',
            'course': 'Algebra II',
            'agent_name': 'MathMentor AI',
            'estimated_time': '25 min',
        },
        'active_agents': active_agents,
        'recent_activity': [
            {'module': 'Linear Equations', 'agent': 'MathMentor AI', 'score': 85,
             'timestamp': '2 hours ago', 'icon': 'check-circle'},
            {'module': 'Cell Biology', 'agent': 'ScienceBot', 'score': 72,
             'timestamp': '5 hours ago', 'icon': 'check-circle'},
            {'module': 'Essay Writing', 'agent': 'LinguaFlow', 'score': 91,
             'timestamp': 'Yesterday', 'icon': 'check-circle'},
            {'module': 'Variables & Types', 'agent': 'CodeCoach', 'score': 68,
             'timestamp': 'Yesterday', 'icon': 'check-circle'},
            {'module': 'Ancient Rome', 'agent': 'HistoryGuide', 'score': 55,
             'timestamp': '2 days ago', 'icon': 'check-circle'},
        ],
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
