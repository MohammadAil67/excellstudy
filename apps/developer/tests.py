import json
import os
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
                capture_output=True,
                text=True
            )
            self.assertEqual(result.returncode, 1)
            self.assertIn("Rejection: Output types mismatch!", result.stderr)
        finally:
            os.remove(temp_path)

