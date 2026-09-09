"""Export every registered instrument to JSON for the React demo.

The React app (``demo-react/``) never imports Python -- it needs its own copy
of each instrument's items, labels, and subscale structure. Rather than
hand-typing that data a second time in TypeScript (and risking it silently
drifting from ``registry.py``), this script serializes the actual registered
``Questionnaire`` objects, so the Python registry stays the one place item
text, labels, and subscale definitions are authored.

The scoring *arithmetic* is still a separate, hand-written TypeScript port
(``demo-react/src/scoring.ts``) -- there is no way around that without running
Python in the browser, which ``docs/design.md`` explains was tried and ruled
out. Only the data shape is generated; the JSON is checked in like
``docs/assets/logo.png`` is, not regenerated on every build, so the React app
has no Python dependency at build or run time.

Run with ``make export-instruments`` after changing any instrument in
``personality_questionnaire/instruments/``. ``tests/demo_react/test_instruments_export.py``
fails CI if the checked-in JSON drifts from what this script would produce now.
"""

from __future__ import annotations

import json
from pathlib import Path

import personality_questionnaire as pq

OUTPUT_PATH = Path("demo-react/src/instruments.json")
"""Where the generated JSON is written, relative to the repository root."""


def export_instrument(key: str) -> dict:
    """Serialize one registered instrument to a JSON-compatible dict.

    Args:
        key: Registry key of the instrument.

    Returns:
        A plain dict matching the schema documented in
        ``demo-react/src/instruments.ts``.
    """
    q = pq.get(key)
    return {
        "key": q.key,
        "name": q.name,
        "abbreviation": q.abbreviation,
        "scale": q.scale.value,
        "minimum": q.minimum,
        "maximum": q.maximum,
        "citation": q.citation,
        "labels": q.labels,
        "paired": q.paired,
        "normalize": q.normalize,
        "items": [
            {
                "number": item.number,
                "text": item.text,
                "prompt": item.prompt,
                "lowAnchor": item.low_anchor,
                "highAnchor": item.high_anchor,
                "sourceNumber": item.source_number,
            }
            for item in q.items
        ],
        "subscales": [
            {
                "name": s.name,
                "items": list(s.items),
                "reverse": sorted(s.reverse),
                "level": s.level,
                "parent": s.parent,
                "higherIs": s.higher_is,
                "aggregation": s.aggregation.value,
            }
            for s in q.subscales
        ],
    }


def export_all() -> dict[str, dict]:
    """Serialize every registered instrument.

    Returns:
        Registry key to its serialized instrument.
    """
    return {key: export_instrument(key) for key in pq.keys()}


def main() -> None:
    """Write the generated JSON to :data:`OUTPUT_PATH`."""
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    data = export_all()
    OUTPUT_PATH.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"wrote {OUTPUT_PATH} ({len(data)} instruments)")


if __name__ == "__main__":
    main()
