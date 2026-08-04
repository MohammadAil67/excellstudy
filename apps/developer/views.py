import redis
import logging
from django.conf import settings
from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from apps.core.models import AgentRegistry, Developer
from apps.developer.forms import AgentRegistrationForm

logger = logging.getLogger(__name__)


class MyAgentsListView(LoginRequiredMixin, View):
    """Lists all of the logged-in developer's agents with their current status."""

    def get(self, request):
        try:
            developer = request.user.developer_profile
        except Developer.DoesNotExist:
            # Fallback/auto-create profile for admin users visiting the portal
            developer = Developer.objects.create(user=request.user)

        agents = AgentRegistry.objects.filter(developer=developer).order_by('-created_at')
        total_sessions_today = sum(a.sessions_today for a in agents)
        context = {
            'user_type': 'developer',
            'developer': developer,
            'agents': agents,
            'total_sessions_today': total_sessions_today,
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
            gh_user = form.cleaned_data.get('github_username', '').strip()
            if gh_user and developer:
                developer.github_username = gh_user
                developer.save()

            agent = form.save(commit=False)
            agent.developer = developer
            agent.status = 'pending'
            agent.save()
            form.save_m2m()

            org = "mohammadail67"
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
            agent = AgentRegistry.objects.get(slug=slug)
        except AgentRegistry.DoesNotExist:
            return JsonResponse(
                {'error': f'Agent registry not found for slug: {slug}'},
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



@login_required
def creation_guide(request):
    """Agent creation guide — constraints, manifest spec, I/O types."""
    return render(request, 'developer/agent_creation_guide.html', {'user_type': 'developer'})


@login_required
def deploy_guide(request):
    """Push and deploy guide — step-by-step deployment walkthrough."""
    return render(request, 'developer/deploy_guide.html', {'user_type': 'developer'})


@login_required
def pipeline_status(request, job_id):
    """Pipeline status page — shows the real deployment state of an agent."""
    agent = get_object_or_404(AgentRegistry, slug=job_id, developer__user=request.user)

    # Check if pipeline validation is active in Redis
    is_running = False
    try:
        r = redis.Redis.from_url(settings.REDIS_URL)
        is_running = r.exists(f"pipeline_run_active:{agent.slug}")
    except Exception as e:
        logger.error(f"Failed to check pipeline_run_active in Redis: {e}")

    # Derive pipeline state from agent's registry status and Redis run state
    if agent.status == 'live':
        pipeline_state = 'success'
    elif agent.status == 'rejected':
        pipeline_state = 'failed'
    elif agent.status == 'pending':
        if is_running:
            pipeline_state = 'running'
        else:
            pipeline_state = 'awaiting_push'
    else:
        pipeline_state = 'pending'

    context = {
        'user_type': 'developer',
        'agent': agent,
        'pipeline_state': pipeline_state,
    }
    return render(request, 'developer/pipeline_status.html', context)


class UpdateGithubUsernameView(LoginRequiredMixin, View):
    """
    POST -> Update developer's GitHub handle from portal sidebar.
    """

    def post(self, request):
        from django.contrib import messages
        gh_user = request.POST.get('github_username', '').strip()
        try:
            developer = request.user.developer_profile
        except Developer.DoesNotExist:
            developer = Developer.objects.create(user=request.user)

        developer.github_username = gh_user
        developer.save()
        messages.success(request, f"GitHub handle updated to '{developer.gh_username}'!")
        return redirect('developer:portal')


class ToggleAgentStatusView(LoginRequiredMixin, View):
    """
    POST -> toggle agent status between 'live' and 'suspended'.
    """

    def post(self, request, agent_slug):
        agent = get_object_or_404(AgentRegistry, slug=agent_slug, developer__user=request.user)
        from apps.agents.registry import invalidate_agent

        if agent.status == 'live':
            agent.status = 'suspended'
            agent.save()
            invalidate_agent(agent.slug)
        elif agent.status == 'suspended':
            agent.status = 'live'
            agent.save()
            invalidate_agent(agent.slug)

        return redirect('developer:portal')


class TriggerPipelineView(LoginRequiredMixin, View):
    """
    POST-only. Called when a developer clicks "I've pushed --
    validate my agent" on the registration confirmation page
    or the pipeline status page.
    """

    def post(self, request, agent_slug):
        from django.contrib import messages
        agent = get_object_or_404(AgentRegistry, slug=agent_slug, developer__user=request.user)

        if agent.status not in ("pending", "rejected"):
            if agent.status == "live":
                messages.warning(request, "This agent is already live.")
            elif agent.status == "suspended":
                messages.warning(request, "This agent is suspended — reactivate it via the portal.")
            else:
                messages.warning(request, f"This agent cannot be triggered (current status: {agent.status}).")
            return redirect('developer:pipeline_status', job_id=agent.slug)

        version = request.POST.get("version", "1.0.0").strip()
        if not version:
            version = "1.0.0"

        from django.core.exceptions import ValidationError
        # Validate version tag format
        old_version = agent.version
        agent.version = version
        try:
            agent.full_clean(exclude=['developer', 'name'])
        except ValidationError as e:
            agent.version = old_version  # restore
            messages.error(request, f"Invalid version format: {e.message_dict.get('version', e.messages)[0]}")
            referer = request.META.get('HTTP_REFERER')
            if referer:
                return redirect(referer)
            return redirect('developer:pipeline_status', job_id=agent.slug)

        from apps.developer.github_dispatch import image_exists_in_registry, trigger_pipeline

        dev_username = agent.developer.gh_username if agent.developer else ""
        if not image_exists_in_registry(agent.slug, version, dev_username):
            messages.error(
                request,
                f"No image found tagged '{version}' for slug '{agent.slug}'. Push it first, then click this button."
            )
            referer = request.META.get('HTTP_REFERER')
            if referer:
                return redirect(referer)
            return redirect('developer:pipeline_status', job_id=agent.slug)

        success, msg = trigger_pipeline(agent.slug, version, agent.developer.namespace, dev_username)
        if success:
            # Set active run indicator in Redis
            try:
                r = redis.Redis.from_url(settings.REDIS_URL)
                r.set(f"pipeline_run_active:{agent.slug}", "true", ex=3600)
            except Exception as e:
                logger.error(f"Failed to set pipeline_run_active in Redis: {e}")

            # Reset status and update version
            if agent.status == 'rejected':
                agent.status = 'pending'
                agent.rejection_reason = ''
            agent.version = version
            agent.save()

            messages.success(request, f"Validation pipeline successfully started for {agent.name} (version {version})!")
            return redirect('developer:pipeline_status', job_id=agent.slug)
        else:
            messages.error(request, f"Failed to dispatch pipeline: {msg}")
            referer = request.META.get('HTTP_REFERER')
            if referer:
                return redirect(referer)
            return redirect('developer:pipeline_status', job_id=agent.slug)


class DeleteAgentView(LoginRequiredMixin, View):
    """
    POST -> Permanently delete an agent registry from the database
    and remove its deployment/service in the Kubernetes cluster.
    """

    def post(self, request, agent_slug):
        agent = get_object_or_404(AgentRegistry, slug=agent_slug, developer__user=request.user)
        from apps.agents.registry import invalidate_agent
        from django.contrib import messages

        slug = agent.slug
        namespace = agent.developer.namespace

        # 1. Delete Kubernetes resources (Deployment & Service)
        try:
            self._delete_k8s_resources(slug, namespace)
        except Exception as e:
            logger.error(f"Failed to delete Kubernetes resources for {slug}: {e}")

        # 2. Invalidate in Redis
        try:
            invalidate_agent(slug)
        except Exception as e:
            logger.error(f"Failed to invalidate agent in Redis: {e}")

        # 3. Delete from database
        agent.delete()

        messages.success(request, f"Agent '{slug}' was successfully deleted and removed from the cluster.")
        return redirect('developer:portal')

    def _delete_k8s_resources(self, slug: str, namespace: str):
        """Delete Deployment and Service using official kubernetes SDK with in-cluster/kubeconfig fallback."""
        try:
            from apps.developer.k8s_utils import get_k8s_clients
            from kubernetes.client.exceptions import ApiException

            apps_api, core_api = get_k8s_clients()

            # Delete Deployment
            try:
                apps_api.delete_namespaced_deployment(name=slug, namespace=namespace)
            except ApiException as e:
                if e.status != 404:
                    logger.warning(f"K8s API error deleting deployment {slug}: {e}")

            # Delete Service
            try:
                core_api.delete_namespaced_service(name=f"{slug}-svc", namespace=namespace)
            except ApiException as e:
                if e.status != 404:
                    logger.warning(f"K8s API error deleting service {slug}-svc: {e}")

        except Exception as e:
            logger.warning(f"Kubernetes Python SDK call failed ({e}). Falling back to subprocess kubectl.")
            import subprocess
            subprocess.run(["kubectl", "delete", "deployment", slug, "-n", namespace], capture_output=True, text=True, timeout=10)
            subprocess.run(["kubectl", "delete", "service", f"{slug}-svc", "-n", namespace], capture_output=True, text=True, timeout=10)


