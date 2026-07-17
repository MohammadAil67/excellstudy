import io
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from apps.core.models import Developer, AgentRegistry, Learner


class LearnerPortalTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username="testlearner", password="password")
        self.client.force_login(self.user)
        
        # Create a developer and live agent
        self.dev_user = User.objects.create_user(username="testdev", password="password")
        self.developer = Developer.objects.create(user=self.dev_user)
        self.agent = AgentRegistry.objects.create(
            name="Live Math Tutor",
            developer=self.developer,
            input_type="text_with_units",
            output_types=["text", "hint"],
            subject_areas=["math"],
            status="live",
        )

    def test_learner_profile_creation_without_skill_levels(self):
        new_user = User.objects.create_user(username="newlearner", password="password")
        learner = Learner.objects.create(user=new_user)
        self.assertEqual(learner.skill_levels, {})

    def test_dashboard_view(self):
        url = reverse('learner:dashboard')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Live Math Tutor")

    def test_agent_session_view_live(self):
        url = reverse('learner:agent-session', kwargs={'agent_slug': self.agent.slug})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['agent'], self.agent)
        self.assertEqual(response.context['input_type'], 'text_with_units')
        self.assertEqual(response.context['output_types'], ['text', 'hint'])

    def test_agent_session_view_not_live(self):
        # Create a pending agent
        pending_agent = AgentRegistry.objects.create(
            name="Pending Agent",
            developer=self.developer,
            input_type="number",
            status="pending",
        )
        url = reverse('learner:agent-session', kwargs={'agent_slug': pending_agent.slug})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

    def test_image_upload_valid(self):
        url = reverse('learner:learner-image-upload')
        # Create a small valid image file mock
        file_data = io.BytesIO(b"FakeImageHeader\x00\x00\x00")
        img_file = SimpleUploadedFile("test.png", file_data.read(), content_type="image/png")
        
        response = self.client.post(url, {'file': img_file})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['status'], 'success')
        self.assertIn('image_url', data['data'])
        self.assertTrue(data['data']['image_url'].startswith('/media/learner-uploads/'))

    def test_image_upload_invalid_type(self):
        url = reverse('learner:learner-image-upload')
        text_file = SimpleUploadedFile("test.txt", b"plain text", content_type="text/plain")
        
        response = self.client.post(url, {'file': text_file})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['status'], 'error')
