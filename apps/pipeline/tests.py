import json
import hmac
import hashlib
from django.test import TestCase, Client
from django.urls import reverse
from django.conf import settings
from apps.core.models import Developer, AgentRegistry
from django.contrib.auth.models import User

class PipelineWebhookTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username="testdev", password="password")
        self.developer = Developer.objects.create(user=self.user)
        self.agent = AgentRegistry.objects.create(
            developer=self.developer,
            name="Test Agent",
            slug="test-agent",
            version="1.0.0",
            input_type="free_text",
            output_types=["text"],
            status="pending"
        )
        self.webhook_url = reverse('pipeline:webhook')

    def test_webhook_invalid_signature(self):
        payload = {
            "agent_slug": "test-agent",
            "status": "success",
            "k8s_service_url": "http://fake-service",
        }
        data = json.dumps(payload)
        response = self.client.post(
            self.webhook_url,
            data=data,
            content_type="application/json",
            HTTP_X_PIPELINE_SIGNATURE="invalid_signature"
        )
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json(), {"error": "Invalid signature"})

    def test_webhook_valid_signature_success(self):
        payload = {
            "agent_slug": "test-agent",
            "status": "success",
            "k8s_service_url": "http://localhost:8080/",
        }
        data = json.dumps(payload).encode()
        
        # Calculate valid signature
        secret = settings.PIPELINE_WEBHOOK_SECRET
        sig = hmac.new(secret.encode(), data, hashlib.sha256).hexdigest()

        response = self.client.post(
            self.webhook_url,
            data=data,
            content_type="application/json",
            HTTP_X_PIPELINE_SIGNATURE=sig
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"slug": "test-agent", "status": "live"})
        
        # Verify database update
        self.agent.refresh_from_db()
        self.assertEqual(self.agent.status, "live")
        self.assertEqual(self.agent.k8s_service_url, "http://localhost:8080/")
        self.assertEqual(self.agent.health_status, "healthy")

    def test_webhook_agent_not_found(self):
        payload = {
            "agent_slug": "does-not-exist",
            "status": "success",
            "k8s_service_url": "http://localhost:8080/",
        }
        data = json.dumps(payload).encode()
        
        secret = settings.PIPELINE_WEBHOOK_SECRET
        sig = hmac.new(secret.encode(), data, hashlib.sha256).hexdigest()

        response = self.client.post(
            self.webhook_url,
            data=data,
            content_type="application/json",
            HTTP_X_PIPELINE_SIGNATURE=sig
        )
        self.assertEqual(response.status_code, 404)
        self.assertIn("error", response.json())

    def test_webhook_validation_error(self):
        payload = {
            "agent_slug": "test-agent",
            "status": "success",
            "k8s_service_url": "invalid-url",  # triggers ValidationError
        }
        data = json.dumps(payload).encode()
        
        secret = settings.PIPELINE_WEBHOOK_SECRET
        sig = hmac.new(secret.encode(), data, hashlib.sha256).hexdigest()

        response = self.client.post(
            self.webhook_url,
            data=data,
            content_type="application/json",
            HTTP_X_PIPELINE_SIGNATURE=sig
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("Validation failed", response.json()["error"])
