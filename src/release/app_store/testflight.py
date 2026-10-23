"""Hands an uploaded build to a TestFlight group through the App Store Connect API.

It waits until App Store Connect has processed the build, adds it to the group, and, for an external
group, submits it for beta review, which external testers need. Standard library only, so the macOS
runner that uploaded the build runs it without installing anything; the key is signed through the
system's `openssl`.
"""

from __future__ import annotations

import argparse
import base64
import json
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

API = "https://api.appstoreconnect.apple.com/v1"

#: App Store Connect's names for the platforms xcodebuild archives for.
PLATFORMS = {"iOS": "IOS", "macOS": "MAC_OS", "tvOS": "TV_OS", "visionOS": "VISION_OS"}


class DistributionError(Exception):
    """Something the person running the workflow can fix, such as a group name that doesn't exist."""


def _base64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def raw_signature(der: bytes) -> bytes:
    """An ECDSA signature as JSON Web Tokens want it, r and s as 32 bytes each, from the DER that
    `openssl dgst` writes."""
    if len(der) < 8 or der[0] != 0x30:
        raise ValueError("not a DER signature")
    index = 2
    parts = []
    for _ in range(2):
        if der[index] != 0x02:
            raise ValueError("not a DER integer")
        length = der[index + 1]
        value = der[index + 2 : index + 2 + length]
        parts.append(value.lstrip(b"\x00").rjust(32, b"\x00"))
        index += 2 + length
    return parts[0] + parts[1]


def token(key_id: str, issuer_id: str, key_path: Path, now: int | None = None) -> str:
    """A token for the App Store Connect API, valid for 15 minutes."""
    issued = int(time.time()) if now is None else now
    header = _base64url(json.dumps({"alg": "ES256", "kid": key_id, "typ": "JWT"}).encode())
    payload = _base64url(
        json.dumps({"iss": issuer_id, "iat": issued, "exp": issued + 900, "aud": "appstoreconnect-v1"}).encode()
    )
    message = f"{header}.{payload}".encode()
    der = subprocess.run(
        ["openssl", "dgst", "-sha256", "-sign", str(key_path)], input=message, capture_output=True, check=True
    ).stdout
    return f"{header}.{payload}.{_base64url(raw_signature(der))}"


#: Sends a request: method, path with its query, JSON body or None; answers the decoded JSON.
Request = Callable[[str, str, Any], Any]


def http_request(bearer: Callable[[], str]) -> Request:
    def send(method: str, path: str, body: Any = None) -> Any:
        data = None if body is None else json.dumps(body).encode()
        request = urllib.request.Request(API + path, data=data, method=method)
        request.add_header("Authorization", f"Bearer {bearer()}")
        request.add_header("Content-Type", "application/json")
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                text = response.read()
        except urllib.error.HTTPError as error:
            raise ApiError(error.code, error.read().decode(errors="replace")) from None
        return json.loads(text) if text else None

    return send


class ApiError(Exception):
    def __init__(self, status: int, body: str):
        super().__init__(f"App Store Connect answered {status}: {body}")
        self.status = status


@dataclass
class Build:
    id: str
    processing: str


def query(**parameters: str) -> str:
    return "?" + urllib.parse.urlencode(parameters)


def app_id(send: Request, bundle_id: str) -> str:
    apps = send("GET", "/apps" + query(**{"filter[bundleId]": bundle_id}))["data"]
    if not apps:
        raise DistributionError(f"No app with the bundle identifier {bundle_id} in App Store Connect.")
    return apps[0]["id"]


def find_build(send: Request, app: str, version: str, build_number: str, platform: str) -> Build | None:
    builds = send(
        "GET",
        "/builds"
        + query(
            **{
                "filter[app]": app,
                "filter[version]": build_number,
                "filter[preReleaseVersion.version]": version,
                "filter[preReleaseVersion.platform]": PLATFORMS[platform],
            }
        ),
    )["data"]
    if not builds:
        return None
    return Build(id=builds[0]["id"], processing=builds[0]["attributes"]["processingState"])


def wait_for_build(
    send: Request,
    app: str,
    version: str,
    build_number: str,
    platform: str,
    timeout: float,
    interval: float = 30,
    sleep: Callable[[float], None] = time.sleep,
    clock: Callable[[], float] = time.monotonic,
) -> Build:
    """The build once App Store Connect processed it; it shows up a while after the upload."""
    deadline = clock() + timeout
    while True:
        build = find_build(send, app, version, build_number, platform)
        if build and build.processing == "VALID":
            return build
        if build and build.processing in ("FAILED", "INVALID"):
            raise DistributionError(f"App Store Connect couldn't process {version} ({build_number}): {build.processing}.")
        if clock() >= deadline:
            state = build.processing if build else "not there yet"
            raise DistributionError(f"{version} ({build_number}) for {platform} is still {state} after {timeout:.0f} s.")
        sleep(interval)


def group(send: Request, app: str, name: str) -> dict:
    groups = send("GET", "/betaGroups" + query(**{"filter[app]": app}))["data"]
    for candidate in groups:
        if candidate["attributes"]["name"] == name:
            return candidate
    names = ", ".join(sorted(g["attributes"]["name"] for g in groups)) or "none"
    raise DistributionError(f"No TestFlight group named {name!r}; the app has: {names}.")


def describe(send: Request, build: Build, notes: str, locale: str = "en-US") -> None:
    """Sets what testers see under What to Test."""
    existing = send("GET", f"/builds/{build.id}/betaBuildLocalizations")["data"]
    for localization in existing:
        if localization["attributes"]["locale"] == locale:
            send(
                "PATCH",
                f"/betaBuildLocalizations/{localization['id']}",
                {"data": {"type": "betaBuildLocalizations", "id": localization["id"], "attributes": {"whatsNew": notes}}},
            )
            return
    send(
        "POST",
        "/betaBuildLocalizations",
        {
            "data": {
                "type": "betaBuildLocalizations",
                "attributes": {"locale": locale, "whatsNew": notes},
                "relationships": {"build": {"data": {"type": "builds", "id": build.id}}},
            }
        },
    )


def distribute(send: Request, build: Build, target: dict) -> str:
    """Adds the build to the group; an external group's build also goes to beta review."""
    send(
        "POST",
        f"/betaGroups/{target['id']}/relationships/builds",
        {"data": [{"type": "builds", "id": build.id}]},
    )
    if target["attributes"].get("isInternalGroup"):
        return "added"
    try:
        send(
            "POST",
            "/betaAppReviewSubmissions",
            {"data": {"type": "betaAppReviewSubmissions", "relationships": {"build": {"data": {"type": "builds", "id": build.id}}}}},
        )
    except ApiError as error:
        # The build was submitted before, by an earlier run or for another external group.
        if error.status != 409:
            raise
    return "submitted for beta review"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle-id", required=True)
    parser.add_argument("--version", required=True)
    parser.add_argument("--build-number", required=True)
    parser.add_argument("--platform", required=True, choices=sorted(PLATFORMS))
    parser.add_argument("--group", required=True)
    parser.add_argument("--notes", default="")
    parser.add_argument("--key-id", required=True)
    parser.add_argument("--issuer-id", required=True)
    parser.add_argument("--key-path", required=True, type=Path)
    parser.add_argument("--timeout", type=float, default=2700)
    arguments = parser.parse_args(argv)

    send = http_request(lambda: token(arguments.key_id, arguments.issuer_id, arguments.key_path))
    try:
        app = app_id(send, arguments.bundle_id)
        target = group(send, app, arguments.group)
        build = wait_for_build(send, app, arguments.version, arguments.build_number, arguments.platform, arguments.timeout)
        if arguments.notes:
            describe(send, build, arguments.notes)
        outcome = distribute(send, build, target)
    except (DistributionError, ApiError) as error:
        print(f"::error::{error}")
        return 1
    print(f"{arguments.version} ({arguments.build_number}) for {arguments.platform}: {outcome} to {arguments.group}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
