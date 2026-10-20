from __future__ import annotations

import re
import sys

import yaml


START_MARKER = "<!-- release-notes:start -->"
END_MARKER = "<!-- release-notes:end -->"
FRONT_MATTER_PATTERN = re.compile(r"\A---\s*\n(?P<meta>.*?)\n---\s*(?:\n|\Z)", re.DOTALL)


def apply_notes_file(body: str, notes: str, version: str) -> str:
    """Replaces the text between the release notes markers of a draft with a notes file.

    The notes file starts with front matter that names the release it belongs to, for example
    ``version: 3.0.0``. The draft keeps its own text when that version is not ``version``, so notes
    of a published release stay out of the next draft. The markers stay in the draft, so the notes can
    be applied again to a rebuilt draft.
    """
    match = FRONT_MATTER_PATTERN.match(notes)
    if not match:
        raise ValueError("Release notes file must start with front matter that names its version")

    meta = yaml.safe_load(match.group("meta")) or {}
    if not isinstance(meta, dict) or not str(meta.get("version") or "").strip():
        raise ValueError("Release notes file front matter must define version")

    notes_version = _normalize(str(meta["version"]))
    if notes_version != _normalize(version):
        print(f"Release notes file is for {notes_version}, not {version}; the draft keeps its own text", file=sys.stderr)
        return body

    start = body.find(START_MARKER)
    end = body.find(END_MARKER)
    if start < 0 or end < start:
        raise ValueError(f"Release body must contain {START_MARKER} followed by {END_MARKER}")

    content = notes[match.end():].strip()
    return body[: start + len(START_MARKER)] + "\n" + content + "\n" + body[end:]


def _normalize(version: str) -> str:
    version = version.strip()
    return version[1:] if version.startswith("v") else version
