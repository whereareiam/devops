
import pytest

from release.notes import format_release_notes


DRAFT = """<!-- release-notes:start -->
# Update 3.0.0 - [Short subtitle]

[1-2 sentence summary of the release.]
<!-- release-notes:end -->

# Changelog

## Fixes

* Sessions: Fixed a session in [#1](https://example.invalid/1)
* API: Fixed an event in [#2](https://example.invalid/2)
* Commands: Fixed a command in [#3](https://example.invalid/3)

# Support

Support text
"""

NOTES = """---
version: 3.0.0
---

# Update 3.0.0 - Shared Proxies

Proxies now share their sessions.

## Upgrading

* Update from 2.2.1; older versions are not supported.
* Back up the plugin folder first.
"""


def test_notes_file_replaces_the_text_between_the_markers() -> None:
    assert format_release_notes(DRAFT, "markdown", "title-prefix", ["API"], notes=NOTES, version="3.0.0") == """<!-- release-notes:start -->
# Update 3.0.0 - Shared Proxies

Proxies now share their sessions.

## Upgrading

* Update from 2.2.1; older versions are not supported.
* Back up the plugin folder first.
<!-- release-notes:end -->

# Changelog

## Fixes

* Commands: Fixed a command in [#3](https://example.invalid/3)
* Sessions: Fixed a session in [#1](https://example.invalid/1)

## For developers

* API: Fixed an event in [#2](https://example.invalid/2)

# Support

Support text
"""


def test_notes_file_of_another_version_leaves_the_draft() -> None:
    assert format_release_notes(DRAFT, "markdown", notes=NOTES, version="v3.0.1") == DRAFT


def test_notes_file_matches_a_tag_with_a_v_prefix() -> None:
    assert "Shared Proxies" in format_release_notes(DRAFT, "markdown", notes=NOTES, version="v3.0.0")


def test_grouping_skips_the_bullets_of_applied_notes() -> None:
    noted = format_release_notes(DRAFT, "markdown", notes=NOTES, version="3.0.0")

    assert format_release_notes(noted, "markdown", "title-prefix", ["API"]) == format_release_notes(
        DRAFT, "markdown", "title-prefix", ["API"], notes=NOTES, version="3.0.0"
    )


def test_notes_file_converts_to_bbcode_without_markers() -> None:
    bbcode = format_release_notes(DRAFT, "bbcode", notes=NOTES, version="3.0.0")

    assert "release-notes" not in bbcode
    assert bbcode.startswith("[SIZE=6][B]Update 3.0.0 - Shared Proxies[/B][/SIZE]")


def test_notes_file_requires_a_version() -> None:
    with pytest.raises(ValueError, match="front matter"):
        format_release_notes(DRAFT, "markdown", notes="# No front matter\n", version="3.0.0")


def test_notes_file_requires_the_markers() -> None:
    with pytest.raises(ValueError, match="release-notes:start"):
        format_release_notes("# Changelog\n", "markdown", notes=NOTES, version="3.0.0")
