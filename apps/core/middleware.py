class LearnerContextMiddleware:
    """Attaches the learner profile to every authenticated request."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.learner = None
        if hasattr(request, 'user') and request.user.is_authenticated:
            try:
                request.learner = request.user.learner_profile
            except Exception:
                pass
        response = self.get_response(request)
        return response
