from __future__ import annotations

import argparse
from pathlib import Path

from release.groupers.title_prefix import DEFAULT_DEVELOPER_TITLE
from release.notes import format_release_notes, parse_prefixes


def main() -> None:
    parser = argparse.ArgumentParser(description="Format release notes for external platforms.")
    parser.add_argument("--format", dest="release_format", required=True)
    parser.add_argument("--grouping", default="")
    parser.add_argument("--developer-prefixes", default="")
    parser.add_argument("--developer-title", default=DEFAULT_DEVELOPER_TITLE)
    parser.add_argument("--notes-file", default="")
    parser.add_argument("--version", default="")
    parser.add_argument("--input-file", required=True, type=Path)
    parser.add_argument("--output-file", required=True, type=Path)
    args = parser.parse_args()

    release_body = args.input_file.read_text(encoding="utf-8")
    notes_path = Path(args.notes_file) if args.notes_file else None
    notes = notes_path.read_text(encoding="utf-8") if notes_path and notes_path.is_file() else None
    formatted = format_release_notes(
        release_body,
        args.release_format,
        args.grouping,
        parse_prefixes(args.developer_prefixes),
        args.developer_title,
        notes,
        args.version,
    )

    args.output_file.parent.mkdir(parents=True, exist_ok=True)
    args.output_file.write_text(formatted, encoding="utf-8")


if __name__ == "__main__":
    main()
