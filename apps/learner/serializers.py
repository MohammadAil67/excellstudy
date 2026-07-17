from rest_framework import serializers
from apps.core.models import Learner, LearnerProgress, Course, Module


class LearnerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Learner
        fields = [
            'id', 'age', 'grade', 'language', 'skill_levels',
            'learning_style', 'mood_signal',
        ]


class LearnerProgressSerializer(serializers.ModelSerializer):
    class Meta:
        model = LearnerProgress
        fields = ['id', 'module', 'completed_at', 'score', 'agent_used']


class CourseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Course
        fields = '__all__'


class ModuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Module
        fields = '__all__'
