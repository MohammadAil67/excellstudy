from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from apps.core.models import AgentRegistry, Developer
from apps.developer.forms import AgentRegistrationForm


class MyAgentsListView(LoginRequiredMixin, View):
    """Lists all of the logged-in developer's agents with their current status."""

    def get(self, request):
        try:
            developer = request.user.developer_profile
        except Developer.DoesNotExist:
            # Fallback/auto-create profile for admin users visiting the portal
            developer = Developer.objects.create(user=request.user)

        agents = AgentRegistry.objects.filter(developer=developer).order_by('-created_at')
        context = {
            'user_type': 'developer',
            'developer': developer,
            'agents': agents,
        }
        return render(request, 'developer/portal.html', context)


class RegisterAgentView(LoginRequiredMixin, View):
    """
    GET  -> render the registration form
    POST -> create a pending AgentRegistry row, show the developer their exact push command
    """

    def get(self, request):
        form = AgentRegistrationForm()
        return render(request, 'developer/register_agent.html', {'form': form})

    def post(self, request):
        try:
            developer = request.user.developer_profile
        except Developer.DoesNotExist:
            developer = Developer.objects.create(user=request.user)

        form = AgentRegistrationForm(request.POST)
        if form.is_valid():
            agent = form.save(commit=False)
            agent.developer = developer
            agent.status = 'pending'
            agent.save()
            form.save_m2m()

            org = "excellstudy"
            return render(request, 'developer/register_confirm.html', {
                'agent': agent,
                'slug': agent.slug,
                'org': org,
            })

        return render(request, 'developer/register_agent.html', {'form': form})


class CheckRegistrationView(View):
    """
    API endpoint for the external pipeline script to cross-validate image manifest
    against the registered portal details.
    """

    def get(self, request):
        slug = request.GET.get('slug')
        if not slug:
            return JsonResponse({'error': 'Missing slug parameter'}, status=400)

        try:
            agent = AgentRegistry.objects.get(slug=slug, status='pending')
        except AgentRegistry.DoesNotExist:
            return JsonResponse(
                {'error': f'Pending agent registry not found for slug: {slug}'},
                status=404
            )

        return JsonResponse({
            'name': agent.name,
            'slug': agent.slug,
            'version': agent.version,
            'input_type': agent.input_type,
            'output_types': agent.output_types,
            'subject_areas': agent.subject_areas,
            'age_groups': agent.age_groups,
            'capabilities': agent.capabilities,
        })


def pipeline_status(request, job_id='job-abc123'):
    """Pipeline status view for rendering status page."""
    # Find matching agent by slug (using job_id parameter as slug/identifier)
    agent = AgentRegistry.objects.filter(slug=job_id).first()
    context = {
        'user_type': 'developer',
        'job_id': job_id,
        'agent': agent,
    }
    return render(request, 'developer/pipeline_status.html', context)
