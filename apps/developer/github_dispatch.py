import logging
import requests
from django.conf import settings

logger = logging.getLogger(__name__)


def image_exists_in_registry(slug: str, version: str, owner_username: str = None) -> bool:
    """
    Check GHCR for the pushed image BEFORE dispatching the
    pipeline, so a developer who clicks the button too early
    (before actually pushing) gets a clear error instead of
    wasting a full pipeline run that fails at the pull step.

    GET /users/{owner}/packages/container/{slug}/versions
    Look through the returned versions for one whose
    metadata.container.tags list includes `version`.
    Return True/False. Treat any non-200 response or exception
    as False (fail closed -- don't dispatch if we can't confirm).
    """
    token = settings.GITHUB_DISPATCH_TOKEN
    owner = settings.GITHUB_REPO_OWNER

    if not token or not owner:
        logger.warning("GITHUB_DISPATCH_TOKEN or GITHUB_REPO_OWNER settings not configured.")
        return False

    # GHCR / GitHub Packages API requires lowercase owner names
    target_owner = (owner_username or owner).lower()

    url = f"https://api.github.com/users/{target_owner}/packages/container/{slug}/versions"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "User-Agent": "ExcellStudy-Platform",
    }

    logger.info(f"Checking registry: GET {url}  (looking for tag '{version}')")

    try:
        response = requests.get(url, headers=headers, timeout=10)
        logger.info(f"Registry response: status={response.status_code}")

        if response.status_code != 200:
            if response.status_code in (401, 403, 404):
                logger.warning(
                    f"GitHub registry check returned status {response.status_code} for owner '{target_owner}'. "
                    "Skipping pre-check and proceeding to trigger workflow validation pipeline."
                )
                return True
            logger.error(
                f"Failed to fetch package versions from GitHub. "
                f"status_code={response.status_code}, response={response.text}"
            )
            return True

        versions_list = response.json()
        logger.info(f"Found {len(versions_list)} version(s) for package '{slug}'")

        for v in versions_list:
            metadata = v.get("metadata", {})
            container = metadata.get("container", {})
            tags = container.get("tags", [])
            logger.debug(f"  Version id={v.get('id')}, tags={tags}")
            if version in tags:
                logger.info(f"Tag '{version}' found for '{slug}'")
                return True

        logger.warning(f"Tag '{version}' NOT found in any version of '{slug}'")
        return False
    except Exception as e:
        logger.error(f"Error checking registry for image: {e}")
        return False


def trigger_pipeline(agent_slug: str, version: str, developer_namespace: str, developer_username: str = None) -> tuple[bool, str]:
    """
    POST to:
      https://api.github.com/repos/{GITHUB_REPO_OWNER}/{GITHUB_REPO_NAME}/actions/workflows/agent-pipeline.yml/dispatches

    Headers:
      Authorization: Bearer {GITHUB_DISPATCH_TOKEN}
      Accept: application/vnd.github+json

    Body:
      {"ref": "main", "inputs": {"agent_slug": agent_slug, "version": version, "developer_namespace": developer_namespace, "developer_username": developer_username}}

    developer_namespace is REQUIRED, not optional.

    Returns (success: bool, message: str).
    GitHub returns 204 No Content on success.
    On non-204, return (False, f"...status code and response text...")
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
            "developer_username": developer_username or owner,
        },
    }

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
