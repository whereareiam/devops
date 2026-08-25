#!/usr/bin/env python3
"""Kubelet credential provider for Artifact Keeper CI-OIDC exchange.

The kubelet supplies a pod-bound Kubernetes ServiceAccount JWT on stdin. The
provider exchanges it for a short-lived Artifact Keeper token and returns a
Docker username/password pair. Registry configuration is intentionally kept in
a root-owned node file rather than in Kubernetes manifests.
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import urlparse


def fail(message: str) -> int:
    print(message, file=sys.stderr)
    return 1


def main() -> int:
    try:
        request = json.load(sys.stdin)
        config_path = os.environ.get(
            "ARTIFACT_KEEPER_CREDENTIAL_PROVIDER_CONFIG",
            "/etc/kubernetes/artifact-keeper-credential-provider.json",
        )
        config = json.loads(Path(config_path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        return fail(f"artifact-keeper credential provider configuration error: {error}")

    api_version = request.get("apiVersion", "credentialprovider.kubelet.k8s.io/v1")
    image = request.get("image", "")
    token = request.get("serviceAccountToken", "")
    if not image or not token:
        return fail("artifact-keeper credential provider requires image and serviceAccountToken")

    registry = image.split("/", 1)[0]
    target = config.get("registries", {}).get(registry)
    if not target:
        print(json.dumps({
            "apiVersion": api_version,
            "kind": "CredentialProviderResponse",
            "cacheKeyType": "Registry",
            "auth": {},
        }))
        return 0

    url = target["url"].rstrip("/")
    provider_id = target["provider_id"]
    parsed = urlparse(url)
    if parsed.scheme != "https" or not parsed.netloc:
        return fail("Artifact Keeper URL must be an HTTPS URL")

    payload = json.dumps({"provider_id": provider_id}).encode("utf-8")
    request_obj = urllib.request.Request(
        f"{url}/api/v1/auth/ci/token",
        data=payload,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request_obj, timeout=15) as response:
            result = json.load(response)
    except (OSError, urllib.error.HTTPError, json.JSONDecodeError) as error:
        return fail(f"Artifact Keeper CI-OIDC exchange failed: {error}")

    username = result.get("username")
    access_token = result.get("access_token")
    if not username or not access_token:
        return fail("Artifact Keeper CI-OIDC response did not contain a usable token")

    print(json.dumps({
        "apiVersion": api_version,
        "kind": "CredentialProviderResponse",
        "cacheKeyType": "Registry",
        "auth": {
            registry: {
                "username": username,
                "password": access_token,
            }
        },
    }))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
