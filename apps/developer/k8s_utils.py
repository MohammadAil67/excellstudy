"""
Kubernetes API Utilities
─────────────────────────
Provides in-cluster configuration loading for pod execution with fallback
to local ~/.kube/config for development and testing.
"""

import logging
from kubernetes import client, config

logger = logging.getLogger(__name__)


def load_k8s_config():
    """
    Load Kubernetes client configuration.
    Tries load_incluster_config() first (when running inside K8s pod),
    falling back to load_kube_config() (when running locally).
    """
    try:
        config.load_incluster_config()
        logger.info("Loaded in-cluster Kubernetes configuration.")
    except Exception:
        config.load_kube_config()
        logger.info("Loaded local kubeconfig file.")


def get_k8s_clients():
    """
    Return initialized (AppsV1Api, CoreV1Api) client tuple.
    """
    load_k8s_config()
    return client.AppsV1Api(), client.CoreV1Api()
