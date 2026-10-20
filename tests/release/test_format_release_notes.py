import pytest

from release.notes import format_release_notes


def test_format_release_notes_builds_bbcode() -> None:
    release_body = """# Update 2.2.0 - Packed for Everyone

Identica now ships as a universal plugin jar, simplifying installation and platform support.

# Changelog

## What’s new

* Platform: Introduce universal plugin jar in [#76](https://github.com/whereareiam/Identica/pull/76)

# Support

If you need help, join us on [Discord](https://discord.arcadeya.com).
"""

    assert format_release_notes(release_body, "bbcode") == """[SIZE=6][B]Update 2.2.0 - Packed for Everyone[/B][/SIZE]

Identica now ships as a universal plugin jar, simplifying installation and platform support.

[SIZE=6][B]Changelog[/B][/SIZE]

[SIZE=5][B]What’s new[/B][/SIZE]

[LIST]
[*]Platform: Introduce universal plugin jar in [URL='https://github.com/whereareiam/Identica/pull/76']#76[/URL]
[/LIST]

[SIZE=6][B]Support[/B][/SIZE]

If you need help, join us on [URL='https://discord.arcadeya.com']Discord[/URL].
"""


def test_format_release_notes_groups_markdown_by_prefix() -> None:
    release_body = """# Update 2.3.0 - [Short subtitle]

[1-2 sentence summary of the release.]

# Changelog

* API: Introduce scenario events in [#89](https://github.com/whereareiam/Identica/pull/89)
* Configuration: Improve config file structure in [#100](https://github.com/whereareiam/Identica/pull/100)
* API: Optimize event listener dispatch in [#101](https://github.com/whereareiam/Identica/pull/101)

# Support

Support text
"""

    assert format_release_notes(release_body, "markdown", "title-prefix") == """# Update 2.3.0 - [Short subtitle]

[1-2 sentence summary of the release.]

# Changelog

* API: Introduce scenario events in [#89](https://github.com/whereareiam/Identica/pull/89)
* API: Optimize event listener dispatch in [#101](https://github.com/whereareiam/Identica/pull/101)
* Configuration: Improve config file structure in [#100](https://github.com/whereareiam/Identica/pull/100)

# Support

Support text
"""


def test_format_release_notes_rejects_unknown_format() -> None:
    with pytest.raises(ValueError, match="Unsupported release note format: unknown"):
        format_release_notes("# Title", "unknown")


def test_format_release_notes_rejects_unknown_grouping() -> None:
    with pytest.raises(ValueError, match="Unsupported release note grouping: unknown"):
        format_release_notes("# Title", "markdown", "unknown")


def test_format_release_notes_moves_developer_changes_apart() -> None:
    release_body = """# Update 3.0.0 - [Short subtitle]

[1-2 sentence summary of the release.]

# Changelog

* Configuration: Improved the config file structure in [#100](https://github.com/whereareiam/Identica/pull/100)
## What’s new

* API: Introduced scenario events in [#89](https://github.com/whereareiam/Identica/pull/89)
* Routing: Introduced forced hosts in [#145](https://github.com/whereareiam/Identica/pull/145)
* Premium: Introduced client profile detection in [#134](https://github.com/whereareiam/Identica/pull/134)
## Fixes

* Premium: Fixed the handshake in [#161](https://github.com/whereareiam/Identica/pull/161)
* Credential: Fixed admin register in [#108](https://github.com/whereareiam/Identica/pull/108)
* premium: Fixed seamless mode in [#109](https://github.com/whereareiam/Identica/pull/109)
* api: Fixed listener order in [#110](https://github.com/whereareiam/Identica/pull/110)
* A change without an area in [#111](https://github.com/whereareiam/Identica/pull/111)
# Support

Support text
"""

    assert format_release_notes(release_body, "markdown", "title-prefix", ["API"]) == """# Update 3.0.0 - [Short subtitle]

[1-2 sentence summary of the release.]

# Changelog

* Configuration: Improved the config file structure in [#100](https://github.com/whereareiam/Identica/pull/100)

## What’s new

* Premium: Introduced client profile detection in [#134](https://github.com/whereareiam/Identica/pull/134)
* Routing: Introduced forced hosts in [#145](https://github.com/whereareiam/Identica/pull/145)

## Fixes

* A change without an area in [#111](https://github.com/whereareiam/Identica/pull/111)
* Credential: Fixed admin register in [#108](https://github.com/whereareiam/Identica/pull/108)
* Premium: Fixed the handshake in [#161](https://github.com/whereareiam/Identica/pull/161)
* premium: Fixed seamless mode in [#109](https://github.com/whereareiam/Identica/pull/109)

## For developers

* API: Introduced scenario events in [#89](https://github.com/whereareiam/Identica/pull/89)
* api: Fixed listener order in [#110](https://github.com/whereareiam/Identica/pull/110)

# Support

Support text
"""


def test_format_release_notes_keeps_a_body_without_changes() -> None:
    release_body = "# Title\n\n* No changes\n"

    assert format_release_notes(release_body, "markdown", "title-prefix", ["API"]) == "# Title\n\n* No changes\n"


def test_format_release_notes_converts_bold_to_bbcode() -> None:
    release_body = "**Full Changelog**: https://github.com/whereareiam/Identica/compare/2.2.1...3.0.0\n"

    assert format_release_notes(release_body, "bbcode") == (
        "[B]Full Changelog[/B]: https://github.com/whereareiam/Identica/compare/2.2.1...3.0.0\n"
    )
