from rest_framework import serializers
from apps.core.models import Developer, AgentRegistry


class DeveloperSerializer(serializers.ModelSerializer):
    class Meta:
        model = Developer
        fields = [
            'id', 'namespace', 'api_key', 'status', 'created_at',
        ]
        read_only_fields = ['namespace', 'api_key']


class AgentRegistrySerializer(serializers.ModelSerializer):
    class Meta:
        model = AgentRegistry
        fields = [
            'id', 'name', 'slug', 'version', 'developer',
            'input_type', 'output_types', 'subject_areas',
            'age_groups', 'capabilities', 'status', 'health_status',
            'k8s_service_url', 'sessions_today', 'related_courses', 'created_at',
        ]
        read_only_fields = ['slug']
