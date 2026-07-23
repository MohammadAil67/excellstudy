import uuid
from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.validators import (
    MinValueValidator,
    MaxValueValidator,
    RegexValidator,
)
from django.utils.text import slugify

from apps.core.input_output_types import APPROVED_INPUT_TYPES, APPROVED_OUTPUT_TYPES


# ─────────────────────────────────────────────────────────────────────
# Learner
# ─────────────────────────────────────────────────────────────────────
class Learner(models.Model):
    """Learner profile linked to a Django User."""

    LEARNING_STYLE_CHOICES = [
        ('visual', 'Visual'),
        ('auditory', 'Auditory'),
        ('kinesthetic', 'Kinesthetic'),
        ('reading_writing', 'Reading/Writing'),
    ]

    MOOD_CHOICES = [
        ('neutral', 'Neutral'),
        ('engaged', 'Engaged'),
        ('frustrated', 'Frustrated'),
        ('confused', 'Confused'),
    ]

    PACE_CHOICES = [
        ('slow', 'Slow'),
        ('normal', 'Normal'),
        ('fast', 'Fast'),
    ]

    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name='learner_profile',
    )
    age = models.PositiveSmallIntegerField(
        null=True, blank=True,
        validators=[MinValueValidator(3), MaxValueValidator(120)],
    )
    grade = models.CharField(max_length=20, blank=True)
    language = models.CharField(max_length=10, default='en')
    skill_levels = models.JSONField(default=dict, blank=True)
    learning_style = models.CharField(
        max_length=20, choices=LEARNING_STYLE_CHOICES, default='visual',
    )
    pace = models.CharField(
        max_length=10, choices=PACE_CHOICES, default='normal',
    )

    current_module = models.ForeignKey(
        'Module', on_delete=models.SET_NULL, null=True, blank=True,
    )
    mood_signal = models.CharField(
        max_length=20, choices=MOOD_CHOICES, default='neutral',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(age__gte=3) & models.Q(age__lte=120),
                name='learner_age_realistic_range',
            ),
        ]

    def __str__(self):
        return self.user.username

    def clean(self):
        super().clean()
        for subject, level in self.skill_levels.items():
            if not isinstance(level, int) or not (0 <= level <= 100):
                raise ValidationError(
                    f"skill_levels['{subject}'] must be an int 0-100, "
                    f"got {level!r}"
                )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)


# ─────────────────────────────────────────────────────────────────────
# Developer
# ─────────────────────────────────────────────────────────────────────
class Developer(models.Model):
    """Developer profile for agent creators."""

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('active', 'Active'),
        ('suspended', 'Suspended'),
    ]

    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name='developer_profile',
    )
    namespace = models.SlugField(
        max_length=50, unique=True, editable=False,
        help_text="Auto-derived as 'dev-{username}'. Cannot be set manually.",
    )
    api_key = models.UUIDField(default=uuid.uuid4, editable=False)

    quota_pods = models.PositiveSmallIntegerField(default=3)
    quota_memory_gb = models.DecimalField(max_digits=4, decimal_places=1, default=2.0)

    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default='pending',
        db_index=True,
    )
    github_username = models.CharField(
        max_length=100, blank=True, default='',
        help_text="Developer's exact GitHub handle for GHCR image tags (e.g. ShafayatHossain423).",
    )
    registry_token_added_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.namespace

    @property
    def gh_username(self):
        if self.github_username and self.github_username.strip():
            return self.github_username.strip()
        return self.user.username.replace(' ', '').strip()

    def save(self, *args, **kwargs):
        if not self.namespace:
            self.namespace = slugify(f'dev-{self.user.username}')
        self.full_clean()
        super().save(*args, **kwargs)

    @property
    def active_pods_count(self):
        return self.agents.filter(status='live').count()

    @property
    def active_memory_gb(self):
        return self.active_pods_count * 0.6

    @property
    def memory_percentage(self):
        if self.quota_memory_gb:
            return min(int((self.active_memory_gb / float(self.quota_memory_gb)) * 100), 100)
        return 0

    @property
    def pods_percentage(self):
        if self.quota_pods:
            return min(int((self.active_pods_count / self.quota_pods) * 100), 100)
        return 0


# ─────────────────────────────────────────────────────────────────────
# Course & Module
# ─────────────────────────────────────────────────────────────────────
class Course(models.Model):
    """A course containing multiple modules."""
    title = models.CharField(max_length=200)
    subject = models.CharField(max_length=50)
    description = models.TextField(blank=True)
    age_group_min = models.PositiveIntegerField(default=6)
    age_group_max = models.PositiveIntegerField(default=18)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(age_group_min__lte=models.F('age_group_max')),
                name='course_age_min_lte_max',
            ),
        ]

    def __str__(self):
        return self.title
    

# ─────────────────────────────────────────────────────────────────────
# AgentRegistry
# ─────────────────────────────────────────────────────────────────────    

class AgentRegistry(models.Model):
    """Registry entry for an AI teaching agent."""

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('live', 'Live'),
        ('rejected', 'Rejected'),
        ('suspended', 'Suspended'),
    ]
    HEALTH_STATUS_CHOICES = [
        ('unknown', 'Unknown'),
        ('healthy', 'Healthy'),
        ('unhealthy', 'Unhealthy'),
        ('unreachable', 'Unreachable'),
    ]

    name = models.CharField(max_length=100)
    slug = models.SlugField(
        max_length=100, unique=True, db_index=True,
        help_text=(
            "URL-safe identifier, e.g. 'dev-alice-biology-checker'. "
            "Auto-generated from developer namespace + name."
        ),
    )

    version = models.CharField(
        max_length=20, default='1.0.0',
        validators=[RegexValidator(
            regex=r'^\d+\.\d+\.\d+$',
            message='version must be semver format, e.g. 1.0.0',
        )],
    )
    developer = models.ForeignKey(
        Developer, on_delete=models.CASCADE, related_name='agents',
    )
    input_type = models.CharField(
        max_length=30,
        choices=[(t, t) for t in APPROVED_INPUT_TYPES],
        default='text',
    )
    output_types = models.JSONField(default=list, blank=True)
    subject_areas = models.JSONField(default=list, blank=True)
    age_groups = models.JSONField(default=list, blank=True)
    capabilities = models.JSONField(default=list, blank=True)
    image_url = models.URLField(blank=True)
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default='pending',
        db_index=True,
    )
    health_status = models.CharField(
        max_length=20, choices=HEALTH_STATUS_CHOICES, default='unknown',
    )
    k8s_service_url = models.URLField(blank=True)
    deployed_at = models.DateTimeField(null=True, blank=True)
    sessions_today = models.PositiveIntegerField(default=0)
    related_courses = models.ManyToManyField(Course, blank=True, related_name='agents')
    rejection_reason = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = 'Agent registries'
        constraints = [
            models.UniqueConstraint(
                fields=['developer', 'name', 'version'],
                name='unique_agent_name_version_per_developer',
            ),
        ]
        indexes = [
            models.Index(fields=['status', 'slug']),
        ]

    def __str__(self):
        return f'{self.name} v{self.version}'

    def clean(self):
        super().clean()
        invalid = [t for t in self.output_types if t not in APPROVED_OUTPUT_TYPES]
        if invalid:
            raise ValidationError(
                f"Invalid output_types: {invalid}. "
                f"Must be a subset of {APPROVED_OUTPUT_TYPES}"
            )

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(f'{self.developer.namespace}-{self.name}')
        self.full_clean()
        super().save(*args, **kwargs)



class Module(models.Model):
    """A module within a course."""
    course = models.ForeignKey(
        Course, on_delete=models.CASCADE, related_name='modules',
    )
    title = models.CharField(max_length=200)
    order = models.PositiveIntegerField(default=0)
    concept_key = models.CharField(max_length=100, blank=True)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return self.title


# ─────────────────────────────────────────────────────────────────────
# LearnerProgress
# ─────────────────────────────────────────────────────────────────────
class LearnerProgress(models.Model):
    """Tracks a learner's progress through modules."""
    learner = models.ForeignKey(
        Learner, on_delete=models.CASCADE, related_name='progress_entries',
    )
    module = models.ForeignKey(
        Module, on_delete=models.SET_NULL, null=True, blank=True,
    )
    completed_at = models.DateTimeField(null=True, blank=True)
    score = models.PositiveSmallIntegerField(
        null=True, blank=True,
        validators=[MaxValueValidator(100)],
    )
    agent_used = models.ForeignKey(
        AgentRegistry, on_delete=models.SET_NULL, null=True, blank=True,
    )

    class Meta:
        indexes = [
            models.Index(fields=['learner', '-completed_at']),
        ]
