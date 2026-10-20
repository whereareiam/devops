from __future__ import annotations

import re


LINK_PATTERN = re.compile(r"\[([^\]]+)]\(([^)]+)\)")
BOLD_PATTERN = re.compile(r"\*\*(.+?)\*\*")


def format_bbcode(markdown: str) -> str:
    lines = markdown.splitlines()
    output: list[str] = []
    in_list = False

    def close_list() -> None:
        nonlocal in_list
        if not in_list:
            return

        output.append("[/LIST]")
        output.append("")
        in_list = False

    for raw_line in lines:
        stripped = raw_line.strip()

        if not stripped:
            close_list()
            if output and output[-1] != "":
                output.append("")
            continue

        if stripped.startswith("<!--") and stripped.endswith("-->"):
            continue

        heading_match = re.fullmatch(r"(#{1,6})\s+(.+)", stripped)
        if heading_match:
            close_list()
            level = len(heading_match.group(1))
            text = _format_inline(heading_match.group(2).strip())
            output.append(f"[SIZE={_heading_size(level)}][B]{text}[/B][/SIZE]")
            output.append("")
            continue

        list_match = re.fullmatch(r"[*-]\s+(.+)", stripped)
        if list_match:
            if not in_list:
                output.append("[LIST]")
                in_list = True
            output.append(f"[*]{_format_inline(list_match.group(1).strip())}")
            continue

        close_list()
        output.append(_format_inline(stripped))
        output.append("")

    close_list()

    while output and output[-1] == "":
        output.pop()

    return "\n".join(output) + "\n"


def _format_inline(text: str) -> str:
    text = LINK_PATTERN.sub(lambda match: f"[URL='{match.group(2)}']{match.group(1)}[/URL]", text)
    return BOLD_PATTERN.sub(lambda match: f"[B]{match.group(1)}[/B]", text)


def _heading_size(level: int) -> int:
    if level == 1:
        return 6
    if level == 2:
        return 5
    if level == 3:
        return 4
    return 3
