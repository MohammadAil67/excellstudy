from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from apps.core.models import Developer, AgentRegistry


class MarketplacePortalTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username="testuser", password="password")
        self.client.force_login(self.user)
        
        self.dev_user = User.objects.create_user(username="testdev", password="password")
        self.developer = Developer.objects.create(user=self.dev_user)
        
        # Live agent
        self.live_agent = AgentRegistry.objects.create(
            name="Live Chem tutor",
            developer=self.developer,
            status="live",
            input_type="free_text",
            subject_areas=["Chemistry"],
        )
        
        # Pending agent
        self.pending_agent = AgentRegistry.objects.create(
            name="Pending Chem tutor",
            developer=self.developer,
            status="pending",
            input_type="free_text",
            subject_areas=["Chemistry"],
        )

    def test_marketplace_browse_lists_only_live_agents(self):
        url = reverse('marketplace:browse')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Live Chem tutor")
        self.assertNotContains(response, "Pending Chem tutor")
