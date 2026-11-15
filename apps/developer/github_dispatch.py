import os
import logging
import requests
from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)

GCP_TOKEN_CACHE_KEY = "gcp:gar_access_token"
GCP_TOKEN_CACHE_TTL = 3300  # 55 minutes (Google OAuth2 tokens expire at 60 mins)


def _get_gcp_access_token() -> str | None:
    """
    Acquire an OAuth2 access token for Google Cloud APIs with Redis caching.
    Reuses the cached token if valid (TTL: 55 minutes) to avoid repeated
    network round-trips to oauth2.googleapis.com on every registry check.
    """
    try:
        cached_token = cache.get(GCP_TOKEN_CACHE_KEY)
        if cached_token:
            logger.debug("Using cached GCP access token.")
            return cached_token
    except Exception as e:
        logger.warning(f"Failed to read GCP token from cache: {e}")

    try:
        import google.auth
        from google.auth.transport.requests import Request
        from google.oauth2 import service_account

        key_path = getattr(settings, 'GCP_SERVICE_ACCOUNT_KEY_PATH', None)
        scopes = ['https://www.googleapis.com/auth/cloud-platform.read-only']

        if key_path and os.path.isfile(key_path):
            creds = service_account.Credentials.from_service_account_file(
                key_path, scopes=scopes
            )
        else:
            creds, _ = google.auth.default(scopes=scopes)

        creds.refresh(Request())
        token = creds.token

        if token:
            try:
                cache.set(GCP_TOKEN_CACHE_KEY, token, timeout=GCP_TOKEN_CACHE_TTL)
            except Exception as e:
                logger.warning(f"Failed to write GCP token to cache: {e}")

        return token
    except Exception as e:
        logger.warning(f"Could not acquire GCP access token: {e}")
        return None


def image_exists_in_registry(slug: str, version: str, owner_username: str = None) -> bool:
    """
    Check Google Artifact Registry (GAR) for the pushed image BEFORE dispatching
    the pipeline, so a developer who clicks the button too early (before actually
    pushing) gets a clear error instead of failing in CI.

    Endpoint:
      GET https://artifactregistry.googleapis.com/v1/projects/{project}/locations/{location}/repositories/{repository}/packages/{slug}/tags/{version}

    Returns True if tag exists, False if 404.
    If auth/network errors occur or GCP is unconfigured in development, fails open (returns True)
    with a warning so local development is not blocked.
    """
    project = getattr(settings, 'GCP_PROJECT_ID', None)
    location = getattr(settings, 'GAR_LOCATION', 'asia-south1')
    repository = getattr(settings, 'GAR_REPOSITORY', 'excellstudy')

    if not project or not repository:
        logger.warning("GCP_PROJECT_ID or GAR_REPOSITORY settings not configured. Bypassing registry check.")
        return True

    token = _get_gcp_access_token()
    if not token:
        logger.warning("No GCP access token available. Skipping pre-check and proceeding to trigger pipeline.")
        return True

    # Artifact Registry packages/tags API
    # Slug is the package name (e.g. 'dev-alice-math-agent')
    url = (
        f"https://artifactregistry.googleapis.com/v1/projects/{project}/"
        f"locations/{location}/repositories/{repository}/packages/{slug}/tags/{version}"
    )
    headers = {
        "Authorization": f"Bearer {token}",
        "User-Agent": "ExcellStudy-Platform",
    }

    logger.info(f"Checking GAR: GET {url}")

    try:
        response = requests.get(url, headers=headers, timeout=10)
        logger.info(f"GAR registry response status: {response.status_code}")

        if response.status_code == 200:
            logger.info(f"Tag '{version}' confirmed in GAR for package '{slug}'.")
            return True
        elif response.status_code == 404:
            logger.warning(f"Tag '{version}' NOT found in GAR for package '{slug}'.")
            return False
        else:
            logger.warning(
                f"GAR returned unexpected status {response.status_code}: {response.text}. "
                "Failing open to allow workflow trigger."
            )
            return True
    except Exception as e:
        logger.error(f"Error querying Google Artifact Registry: {e}. Failing open.")
        return True


def trigger_pipeline(
    agent_slug: str,
    version: str,
    developer_namespace: str,
    developer_username: str = None
) -> tuple[bool, str]:
    """
    Trigger the agent deployment pipeline via GitHub Actions workflow dispatch.

    POST to:
      https://api.github.com/repos/{GITHUB_REPO_OWNER}/{GITHUB_REPO_NAME}/actions/workflows/agent-pipeline.yml/dispatches

    Headers:
      Authorization: Bearer {GITHUB_DISPATCH_TOKEN}
      Accept: application/vnd.github+json

    Body:
      {
        "ref": "main",
        "inputs": {
          "agent_slug": agent_slug,
          "version": version,
          "developer_namespace": developer_namespace
        }
      }

    Returns (success: bool, message: str).
    """
    token = settings.GITHUB_DISPATCH_TOKEN
    owner = settings.GITHUB_REPO_OWNER
    repo = settings.GITHUB_REPO_NAME

    if not token or not owner or not repo:
        return False, "GitHub dispatch credentials or repository setting is not configured in .env"

    url = f"https://api.github.com/repos/{owner}/{repo}/actions/workflows/agent-pipeline.yml/dispatches"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "User-Agent": "ExcellStudy-Platform",
    }
    payload = {
        "ref": "main",
        "inputs": {
            "agent_slug": agent_slug,
            "version": version,
            "developer_namespace": developer_namespace,
        },
    }
    if developer_username:
        payload["inputs"]["developer_username"] = developer_username

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=10)
        if response.status_code == 204:
            return True, "Pipeline successfully dispatched."
        else:
            return (
                False,
                f"GitHub API error (status {response.status_code}): {response.text}",
            )
    except Exception as e:
        return False, f"HTTP request failed: {e}"
