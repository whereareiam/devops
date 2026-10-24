import base64
import json
import subprocess
from pathlib import Path

import pytest

from release.app_store import testflight
from release.app_store.testflight import ApiError, Build, DistributionError


class FakeApi:
    """App Store Connect as canned answers per method and path, recording what was sent."""

    def __init__(self, answers: dict):
        self.answers = answers
        self.sent: list[tuple[str, str, object]] = []

    def __call__(self, method, path, body=None):
        self.sent.append((method, path, body))
        for (expected_method, prefix), answer in self.answers.items():
            if method == expected_method and path.startswith(prefix):
                if isinstance(answer, Exception):
                    raise answer
                return answer() if callable(answer) else answer
        raise AssertionError(f"unexpected {method} {path}")


def test_turns_a_der_signature_into_raw_r_and_s():
    r = b"\x00" + b"\x81" * 32
    s = b"\x01" * 31
    der = bytes([0x30, 4 + len(r) + len(s), 0x02, len(r)]) + r + bytes([0x02, len(s)]) + s

    raw = testflight.raw_signature(der)

    assert raw == b"\x81" * 32 + b"\x00" + b"\x01" * 31


def test_signs_a_token_for_app_store_connect(tmp_path: Path):
    key = tmp_path / "key.p8"
    subprocess.run(["openssl", "ecparam", "-name", "prime256v1", "-genkey", "-noout", "-out", str(key)], check=True)

    token = testflight.token("KEY", "ISSUER", key, now=1000)
    header, payload, signature = token.split(".")
    decode = lambda part: base64.urlsafe_b64decode(part + "=" * (-len(part) % 4))

    assert json.loads(decode(header)) == {"alg": "ES256", "kid": "KEY", "typ": "JWT"}
    assert json.loads(decode(payload))["exp"] == 1900
    assert len(decode(signature)) == 64


def test_waits_until_the_build_is_processed():
    states = iter(["PROCESSING", "PROCESSING", "VALID"])
    api = FakeApi({("GET", "/builds"): lambda: {"data": [{"id": "b1", "attributes": {"processingState": next(states)}}]}})
    slept = []

    build = testflight.wait_for_build(api, "app", "1.2.0", "42", "iOS", timeout=600, sleep=slept.append, clock=lambda: 0)

    assert build == Build(id="b1", processing="VALID")
    assert len(slept) == 2
    assert "filter%5BpreReleaseVersion.platform%5D=IOS" in api.sent[0][1]


def test_gives_up_on_a_build_that_never_shows():
    api = FakeApi({("GET", "/builds"): {"data": []}})
    times = iter([0, 700])

    with pytest.raises(DistributionError, match="not there yet"):
        testflight.wait_for_build(api, "app", "1.2.0", "42", "macOS", timeout=600, sleep=lambda _: None, clock=lambda: next(times))


def test_names_the_groups_there_are_when_one_is_missing():
    api = FakeApi({("GET", "/betaGroups"): {"data": [{"id": "g", "attributes": {"name": "Friends"}}]}})

    with pytest.raises(DistributionError, match="Friends"):
        testflight.group(api, "app", "Family")


def test_an_internal_group_only_gets_the_build():
    api = FakeApi({("POST", "/betaGroups/g/relationships/builds"): None})

    outcome = testflight.distribute(api, Build("b1", "VALID"), {"id": "g", "attributes": {"isInternalGroup": True}})

    assert outcome == "added"
    assert [path for _, path, _ in api.sent] == ["/betaGroups/g/relationships/builds"]


def test_an_external_group_sends_the_build_to_beta_review_once():
    api = FakeApi({
        ("POST", "/betaGroups/g/relationships/builds"): None,
        ("POST", "/betaAppReviewSubmissions"): ApiError(409, "already submitted"),
    })

    outcome = testflight.distribute(api, Build("b1", "VALID"), {"id": "g", "attributes": {"isInternalGroup": False}})

    assert outcome == "submitted for beta review"


def test_sets_what_to_test_on_a_build_without_notes():
    api = FakeApi({("GET", "/builds/b1/betaBuildLocalizations"): {"data": []}, ("POST", "/betaBuildLocalizations"): None})

    testflight.describe(api, Build("b1", "VALID"), "Try the new library.")

    method, _, body = api.sent[-1]
    assert method == "POST"
    assert body["data"]["attributes"] == {"locale": "en-US", "whatsNew": "Try the new library."}
