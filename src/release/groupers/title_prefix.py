from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass, field

from release.notes_file import END_MARKER as NOTES_END_MARKER


BULLET_PATTERN = re.compile(r"^\* (?P<entry>.+)$")
PREFIX_PATTERN = re.compile(r"^(?P<prefix>[^:\[\]()]+):\s+(?P<rest>.+)$")
CATEGORY_PATTERN = re.compile(r"^## (?P<title>.+)$")

DEFAULT_DEVELOPER_TITLE = "For developers"


@dataclass
class _Entry:
    area: str | None
    line: str


@dataclass
class _Category:
    title: str | None
    entries: list[_Entry] = field(default_factory=list)


def group_by_title_prefix(
    body: str,
    developer_prefixes: Iterable[str] = (),
    developer_title: str = DEFAULT_DEVELOPER_TITLE,
) -> str:
    """Sorts the changes of every category by the area in their ``Area: Description`` title prefix.

    The changes are the bullets and ``## Category`` headings that release-drafter renders for
    ``$CHANGES``. Inside each category, changes keep their prefix and are ordered by area, and changes of
    one area keep their original order; changes without a prefix come first. Changes whose area is one
    of ``developer_prefixes`` leave their category and close the changes in a ``## developer_title``
    section, in the order of the categories they came from.
    """
    lines = body.splitlines()
    developer_areas = {prefix.strip().lower() for prefix in developer_prefixes if prefix.strip()}

    start, end = _changes_range(lines)
    if start is None:
        return body.rstrip() + "\n"

    categories = _parse_categories(lines[start:end])
    rendered = _render(categories, developer_areas, developer_title)

    before = _trim_trailing_blank(lines[:start])
    after = _trim_leading_blank(lines[end:])
    output = before + ([""] if before else []) + rendered + ([""] + after if after else [])
    return "\n".join(output).rstrip() + "\n"


def _changes_range(lines: list[str]) -> tuple[int | None, int]:
    # Bullets of the release notes file are not changes.
    search_from = next((index + 1 for index, line in enumerate(lines) if line.strip() == NOTES_END_MARKER), 0)
    first_bullet = next(
        (index for index in range(search_from, len(lines)) if BULLET_PATTERN.match(lines[index].strip())),
        None,
    )
    if first_bullet is None:
        return None, len(lines)

    start = first_bullet
    while start > search_from and (not lines[start - 1].strip() or CATEGORY_PATTERN.match(lines[start - 1].strip())):
        start -= 1
    while start < first_bullet and not lines[start].strip():
        start += 1

    last_bullet = first_bullet
    for index in range(first_bullet, len(lines)):
        stripped = lines[index].strip()
        if BULLET_PATTERN.match(stripped):
            last_bullet = index
            continue
        if not stripped or CATEGORY_PATTERN.match(stripped):
            continue
        break
    return start, last_bullet + 1


def _parse_categories(lines: list[str]) -> list[_Category]:
    categories: list[_Category] = [_Category(title=None)]
    for line in lines:
        stripped = line.strip()
        heading = CATEGORY_PATTERN.match(stripped)
        if heading:
            categories.append(_Category(title=heading.group("title").strip()))
            continue

        bullet = BULLET_PATTERN.match(stripped)
        if not bullet:
            continue

        prefix = PREFIX_PATTERN.match(bullet.group("entry"))
        area = prefix.group("prefix").strip() if prefix else None
        categories[-1].entries.append(_Entry(area=area, line=f"* {bullet.group('entry')}"))
    return [category for category in categories if category.entries]


def _render(categories: list[_Category], developer_areas: set[str], developer_title: str) -> list[str]:
    output: list[str] = []
    developer_entries: list[_Entry] = []

    for category in categories:
        user_entries = [entry for entry in category.entries if not _is_developer(entry, developer_areas)]
        developer_entries.extend(entry for entry in category.entries if _is_developer(entry, developer_areas))
        if not user_entries:
            continue

        if category.title is not None:
            _append_block(output, [f"## {category.title}"])
        _append_block(output, [entry.line for entry in _sort_by_area(user_entries)])

    if developer_entries:
        _append_block(output, [f"## {developer_title}"])
        _append_block(output, [entry.line for entry in developer_entries])

    return output


def _sort_by_area(entries: list[_Entry]) -> list[_Entry]:
    return sorted(entries, key=lambda entry: (entry.area is not None, (entry.area or "").lower()))


def _is_developer(entry: _Entry, developer_areas: set[str]) -> bool:
    return entry.area is not None and entry.area.lower() in developer_areas


def _append_block(output: list[str], block: list[str]) -> None:
    if output:
        output.append("")
    output.extend(block)


def _trim_trailing_blank(lines: list[str]) -> list[str]:
    result = list(lines)
    while result and not result[-1].strip():
        result.pop()
    return result


def _trim_leading_blank(lines: list[str]) -> list[str]:
    result = list(lines)
    while result and not result[0].strip():
        result.pop(0)
    return result
