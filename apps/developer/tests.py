import json
import os
from unittest.mock import patch
import apps.developer.github_dispatch
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from apps.core.models import Developer, AgentRegistry


class DeveloperPortalTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username="testdev", password="password")
        self.developer = Developer.objects.create(user=self.user)
        self.client.force_login(self.user)

    def test_register_agent_view_get(self):
        url = reverse('developer:register-agent')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Register a New Agent")

    def test_register_agent_view_post_valid(self):
        url = reverse('developer:register-agent')
        payload = {
            'name': 'Science Helper',
            'input_type': 'free_text',
            'output_types': ['text', 'hint'],
            'subject_areas': 'science, physics',
            'age_groups': '12-15',
            'capabilities': 'step-by-step',
        }
        response = self.client.post(url, payload)
        self.assertEqual(response.status_code, 200)
        # Verify the agent registry is created as pending
        agent = AgentRegistry.objects.get(name='Science Helper')
        self.assertEqual(agent.status, 'pending')
        self.assertEqual(agent.subject_areas, ['science', 'physics'])
        self.assertEqual(agent.output_types, ['text', 'hint'])
        # Verify confirm page is rendered with slug
        self.assertContains(response, agent.slug)

    def test_register_agent_view_post_invalid(self):
        url = reverse('developer:register-agent')
        payload = {
            'name': '',  # missing name
            'input_type': 'free_text',
            'output_types': [],
        }
        response = self.client.post(url, payload)
        self.assertEqual(response.status_code, 200)
        # Verify form has errors and no row was created
        form = response.context['form']
        self.assertTrue(form.errors)
        self.assertIn('name', form.errors)
        self.assertEqual(form.errors['name'], ['This field is required.'])
        self.assertEqual(AgentRegistry.objects.count(), 0)

    def test_check_registration_api_valid(self):
        agent = AgentRegistry.objects.create(
            name="Math Helper",
            developer=self.developer,
            input_type="number",
            output_types=["score"],
            subject_areas=["math"],
            status="pending",
        )
        url = reverse('developer:check-registration') + f"?slug={agent.slug}"
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['name'], 'Math Helper')
        self.assertEqual(data['input_type'], 'number')
        self.assertEqual(data['output_types'], ['score'])

    def test_check_registration_api_not_found(self):
        url = reverse('developer:check-registration') + "?slug=non-existent-slug"
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

    def test_toggle_agent_status_live_to_suspended(self):
        agent = AgentRegistry.objects.create(
            name="Toggle Helper",
            developer=self.developer,
            input_type="number",
            status="live",
        )
        url = reverse('developer:toggle-agent-status', kwargs={'agent_slug': agent.slug})
        response = self.client.post(url)
        self.assertEqual(response.status_code, 302)
        agent.refresh_from_db()
        self.assertEqual(agent.status, 'suspended')

    def test_toggle_agent_status_suspended_to_live(self):
        agent = AgentRegistry.objects.create(
            name="Toggle Helper 2",
            developer=self.developer,
            input_type="number",
            status="suspended",
        )
        url = reverse('developer:toggle-agent-status', kwargs={'agent_slug': agent.slug})
        response = self.client.post(url)
        self.assertEqual(response.status_code, 302)
        agent.refresh_from_db()
        self.assertEqual(agent.status, 'live')

    def test_trigger_pipeline_view_post_not_pending(self):
        agent = AgentRegistry.objects.create(
            name="Trigger Fail Agent",
            developer=self.developer,
            input_type="number",
            status="live",
        )
        url = reverse('developer:trigger-pipeline', kwargs={'agent_slug': agent.slug})
        response = self.client.post(url, {'version': 'v1'})
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('developer:pipeline_status', kwargs={'job_id': agent.slug}))

    @patch('apps.developer.github_dispatch.image_exists_in_registry')
    def test_trigger_pipeline_view_post_image_not_exists(self, mock_exists):
        mock_exists.return_value = False
        agent = AgentRegistry.objects.create(
            name="Trigger Missing Image Agent",
            developer=self.developer,
            input_type="number",
            status="pending",
        )
        url = reverse('developer:trigger-pipeline', kwargs={'agent_slug': agent.slug})
        response = self.client.post(url, {'version': '3.0.0'})
        self.assertEqual(response.status_code, 302)
        mock_exists.assert_called_once_with(agent.slug, '3.0.0')

    @patch('apps.developer.github_dispatch.image_exists_in_registry')
    @patch('apps.developer.github_dispatch.trigger_pipeline')
    def test_trigger_pipeline_view_post_success(self, mock_trigger, mock_exists):
        mock_exists.return_value = True
        mock_trigger.return_value = (True, "Pipeline successfully dispatched.")
        agent = AgentRegistry.objects.create(
            name="Trigger Success Agent",
            developer=self.developer,
            input_type="number",
            status="pending",
        )
        url = reverse('developer:trigger-pipeline', kwargs={'agent_slug': agent.slug})
        response = self.client.post(url, {'version': '2.0.0'})
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('developer:pipeline_status', kwargs={'job_id': agent.slug}))
        mock_exists.assert_called_once_with(agent.slug, '2.0.0')
        mock_trigger.assert_called_once_with(agent.slug, '2.0.0', self.developer.namespace)
        agent.refresh_from_db()
        self.assertEqual(agent.version, '2.0.0')

    @patch('apps.developer.github_dispatch.image_exists_in_registry')
    @patch('apps.developer.github_dispatch.trigger_pipeline')
    def test_trigger_pipeline_view_post_rejected_success(self, mock_trigger, mock_exists):
        mock_exists.return_value = True
        mock_trigger.return_value = (True, "Pipeline successfully dispatched.")
        agent = AgentRegistry.objects.create(
            name="Trigger Rejected Success Agent",
            developer=self.developer,
            input_type="number",
            status="rejected",
            rejection_reason="some old failure log",
            version="1.0.0"
        )
        url = reverse('developer:trigger-pipeline', kwargs={'agent_slug': agent.slug})
        response = self.client.post(url, {'version': '1.0.1'})
        self.assertEqual(response.status_code, 302)
        
        agent.refresh_from_db()
        self.assertEqual(agent.status, 'pending')
        self.assertEqual(agent.rejection_reason, '')
        self.assertEqual(agent.version, '1.0.1')

    def test_trigger_pipeline_view_post_invalid_version(self):
        agent = AgentRegistry.objects.create(
            name="Trigger Invalid Version Agent",
            developer=self.developer,
            input_type="number",
            status="pending",
        )
        url = reverse('developer:trigger-pipeline', kwargs={'agent_slug': agent.slug})
        response = self.client.post(url, {'version': 'v1'})
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('developer:pipeline_status', kwargs={'job_id': agent.slug}))
        
        # Verify the version in the database did not change
        agent.refresh_from_db()
        self.assertEqual(agent.version, '1.0.0')

    def test_trigger_pipeline_view_post_different_developer(self):
        other_user = User.objects.create_user(username="otherdev", password="password")
        other_developer = Developer.objects.create(user=other_user)
        agent = AgentRegistry.objects.create(
            name="Other Agent",
            developer=other_developer,
            input_type="number",
            status="pending",
        )
        url = reverse('developer:trigger-pipeline', kwargs={'agent_slug': agent.slug})
        response = self.client.post(url, {'version': 'v1'})
        self.assertEqual(response.status_code, 404)

    @patch('subprocess.run')
    @patch('apps.agents.registry.invalidate_agent')
    def test_delete_agent_view_post_success(self, mock_invalidate, mock_run):
        agent = AgentRegistry.objects.create(
            name="Agent to Delete",
            developer=self.developer,
            input_type="number",
            status="live"
        )
        url = reverse('developer:delete-agent', kwargs={'agent_slug': agent.slug})
        response = self.client.post(url)
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('developer:portal'))

        # Verify database deletion
        self.assertFalse(AgentRegistry.objects.filter(slug=agent.slug).exists())

        # Verify Redis invalidation
        mock_invalidate.assert_called_once_with(agent.slug)

        # Verify subprocess.run was called twice (once for deployment, once for service)
        self.assertEqual(mock_run.call_count, 2)
        
        # Check first call: kubectl delete deployment ...
        first_call_args = mock_run.call_args_list[0][0][0]
        self.assertEqual(first_call_args[0], "kubectl")
        self.assertEqual(first_call_args[1], "delete")
        self.assertEqual(first_call_args[2], "deployment")
        self.assertEqual(first_call_args[3], agent.slug)

        # Check second call: kubectl delete service ...
        second_call_args = mock_run.call_args_list[1][0][0]
        self.assertEqual(second_call_args[0], "kubectl")
        self.assertEqual(second_call_args[1], "delete")
        self.assertEqual(second_call_args[2], "service")
        self.assertEqual(second_call_args[3], f"{agent.slug}-svc")


class GARRegistryDispatchTests(TestCase):
    @patch('apps.developer.github_dispatch._get_gcp_access_token')
    @patch('requests.get')
    def test_image_exists_in_registry_found(self, mock_requests_get, mock_get_token):
        from apps.developer.github_dispatch import image_exists_in_registry
        mock_get_token.return_value = "ya29.test-token"
        mock_requests_get.return_value.status_code = 200

        exists = image_exists_in_registry("test-agent", "1.0.0")
        self.assertTrue(exists)
        mock_requests_get.assert_called_once()
        args, kwargs = mock_requests_get.call_args
        self.assertIn("packages/test-agent/tags/1.0.0", args[0])
        self.assertEqual(kwargs['headers']['Authorization'], "Bearer ya29.test-token")

    @patch('apps.developer.github_dispatch._get_gcp_access_token')
    @patch('requests.get')
    def test_image_exists_in_registry_not_found(self, mock_requests_get, mock_get_token):
        from apps.developer.github_dispatch import image_exists_in_registry
        mock_get_token.return_value = "ya29.test-token"
        mock_requests_get.return_value.status_code = 404

        exists = image_exists_in_registry("test-agent", "1.0.0")
        self.assertFalse(exists)

    @patch('apps.developer.github_dispatch.settings')
    def test_image_exists_in_registry_unconfigured(self, mock_settings):
        from apps.developer.github_dispatch import image_exists_in_registry
        mock_settings.GCP_PROJECT_ID = None
        mock_settings.GAR_REPOSITORY = None
        self.assertTrue(image_exists_in_registry("test-agent", "1.0.0"))

    @patch('apps.developer.github_dispatch._get_gcp_access_token')
    def test_image_exists_in_registry_no_token(self, mock_get_token):
        from apps.developer.github_dispatch import image_exists_in_registry
        mock_get_token.return_value = None
        self.assertTrue(image_exists_in_registry("test-agent", "1.0.0"))

    @patch('apps.developer.github_dispatch._get_gcp_access_token')
    @patch('requests.get')
    def test_image_exists_in_registry_network_error(self, mock_requests_get, mock_get_token):
        import requests
        from apps.developer.github_dispatch import image_exists_in_registry
        mock_get_token.return_value = "ya29.test-token"
        mock_requests_get.side_effect = requests.RequestException("Network timeout")
        self.assertTrue(image_exists_in_registry("test-agent", "1.0.0"))

    @patch('apps.developer.github_dispatch.cache')
    def test_get_gcp_access_token_uses_cache(self, mock_cache):
        from apps.developer.github_dispatch import _get_gcp_access_token, GCP_TOKEN_CACHE_KEY
        mock_cache.get.return_value = "cached-access-token"
        token = _get_gcp_access_token()
        self.assertEqual(token, "cached-access-token")
        mock_cache.get.assert_called_once_with(GCP_TOKEN_CACHE_KEY)




import sys
import subprocess
import tempfile
from django.test import LiveServerTestCase


class ManifestScriptTests(LiveServerTestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="scriptdev", password="password")
        self.developer = Developer.objects.create(user=self.user)
        self.agent = AgentRegistry.objects.create(
            name="Valid Agent",
            developer=self.developer,
            input_type="number",
            output_types=["score", "hint"],
            subject_areas=["math"],
            status="pending",
        )

    def test_script_validation_success(self):
        manifest_data = {
            "name": "Valid Agent",
            "version": "1.0.0",
            "input_type": "number",
            "output_types": ["score", "hint"],
            "subject_areas": ["math"],
            "invoke": "/invoke",
            "health": "/health",
            "capabilities": "/capabilities"
        }

        with tempfile.NamedTemporaryFile(suffix='.json', mode='w', delete=False) as tf:
            json.dump(manifest_data, tf)
            temp_path = tf.name

        try:
            env = os.environ.copy()
            env['EXCELLSTUDY_HOST'] = self.live_server_url

            result = subprocess.run(
                [sys.executable, 'scripts/validate_manifest.py', temp_path, self.agent.slug],
                env=env,
                stdin=subprocess.DEVNULL,
                capture_output=True,
                text=True
            )
            self.assertEqual(result.returncode, 0)
            self.assertIn("Success: Manifest cross-validation passed", result.stdout)
        finally:
            os.remove(temp_path)

    def test_script_validation_mismatch(self):
        manifest_data = {
            "name": "Valid Agent",
            "version": "1.0.0",
            "input_type": "number",
            "output_types": ["score", "verdict"],
            "subject_areas": ["math"],
            "invoke": "/invoke",
            "health": "/health",
            "capabilities": "/capabilities"
        }

        with tempfile.NamedTemporaryFile(suffix='.json', mode='w', delete=False) as tf:
            json.dump(manifest_data, tf)
            temp_path = tf.name

        try:
            env = os.environ.copy()
            env['EXCELLSTUDY_HOST'] = self.live_server_url

            result = subprocess.run(
                [sys.executable, 'scripts/validate_manifest.py', temp_path, self.agent.slug],
                env=env,
                stdin=subprocess.DEVNULL,
                capture_output=True,
                text=True
            )
            self.assertEqual(result.returncode, 1)
            self.assertIn("Rejection: Output types mismatch!", result.stderr)
        finally:
            os.remove(temp_path)

