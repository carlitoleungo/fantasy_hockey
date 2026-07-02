#!/usr/bin/env python3
"""Report whether an audit checkpoint is due.

Counts completed non-audit tickets that no audit in .team/audits/ has covered
yet. Full-process tickets count 1.0 toward the threshold; `Process: light`
tickets count 0.5 (they carry less risk, but the next audit still covers them).
An audit is due when the weighted count reaches AUDIT_THRESHOLD.

Tickets are matched against audits by ID: the leading number of the ticket
filename (e.g. `020`, `019a`), or the whole slug for non-numeric tickets
(e.g. `bug-week23-all-zeroes`). Numeric tickets at or below the highest
audited ID are treated as covered even if no audit lists them explicitly
(pre-audit-era history is grandfathered).

Usage: python scripts/audit_due.py
Exit code: 1 if an audit is due, else 0.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

AUDIT_THRESHOLD = 5.0

ROOT = Path(__file__).resolve().parent.parent
TICKETS_DIR = ROOT / "tickets"
DONE_DIR = TICKETS_DIR / "done"
AUDITS_DIR = ROOT / ".team" / "audits"

ARTIFACT_SUFFIXES = ("-done", "-qa", "-review", "-fix", "-qa-review")
# Numeric tickets: artifacts are exactly `<id>-<suffix>` (e.g. 020-qa, 019a-done);
# a longer slug that merely ends in "-fix" is a spec, not an artifact.
ARTIFACT_RE = re.compile(r"^\d+[a-z]?-(done|qa|review|fix|qa-review)$")
COUNTED_TYPES = {"feature", "bug", "refactor"}


def read_section(text: str, name: str) -> str | None:
    """Return the body of a `## <name>` markdown section, or None."""
    m = re.search(rf"^## {name}\s*\n(.*?)(?=^## |\Z)", text, re.M | re.S)
    return m.group(1).strip() if m else None


def is_spec(path: Path) -> bool:
    """True if the file is a ticket spec, not a handoff artifact."""
    stem = path.stem
    if ARTIFACT_RE.match(stem):
        return False
    if not stem[0].isdigit():
        # non-numeric ticket (e.g. bug-week23-all-zeroes-qa): suffix check
        return not any(stem.endswith(s) for s in ARTIFACT_SUFFIXES)
    return True


def ticket_id(stem: str) -> str:
    """`020-demo-overview` -> `020`; `bug-week23-all-zeroes` -> itself."""
    m = re.match(r"^(\d+[a-z]?)-", stem)
    return m.group(1) if m else stem


def numeric_part(tid: str) -> int | None:
    m = re.match(r"^(\d+)", tid)
    return int(m.group(1)) if m else None


def audited_ids() -> set[str]:
    """Ticket IDs listed under 'Tickets reviewed' in any audit file."""
    ids: set[str] = set()
    if not AUDITS_DIR.is_dir():
        return ids
    for audit in AUDITS_DIR.glob("*-audit.md"):
        text = audit.read_text()
        m = re.search(r"^#{2,3} Tickets reviewed\s*\n(.*?)(?=^#|\Z)", text, re.M | re.S)
        if not m:
            continue
        for line in m.group(1).splitlines():
            bullet = re.match(r"\s*-\s+\**([A-Za-z0-9][\w-]*)", line)
            if bullet:
                ids.add(bullet.group(1))
    return ids


def completed_specs() -> list[Path]:
    """Ticket specs that are done: everything in done/, plus Status: done in tickets/."""
    specs = [p for p in sorted(DONE_DIR.glob("*.md")) if is_spec(p)]
    for p in sorted(TICKETS_DIR.glob("*.md")):
        if not is_spec(p):
            continue
        status = read_section(p.read_text(), "Status") or ""
        if status and status.split()[0].lower() == "done":
            specs.append(p)
    return specs


def main() -> int:
    covered = audited_ids()
    covered_numeric = [n for n in (numeric_part(t) for t in covered) if n is not None]
    high_water = max(covered_numeric, default=0)

    uncovered: list[tuple[str, float, str]] = []  # (id, weight, filename)
    skipped: list[str] = []
    for spec in completed_specs():
        tid = ticket_id(spec.stem)
        if tid in covered:
            continue
        n = numeric_part(tid)
        if n is not None and n <= high_water:
            continue  # pre-audit-era history, grandfathered
        text = spec.read_text()
        type_section = read_section(text, "Type") or ""
        ticket_type = type_section.split()[0].lower() if type_section else ""
        if ticket_type == "audit":
            continue
        if ticket_type not in COUNTED_TYPES:
            skipped.append(spec.name)
            continue
        process = (read_section(text, "Process") or "full").split()[0].lower()
        weight = 0.5 if process == "light" else 1.0
        uncovered.append((tid, weight, spec.name))

    total = sum(w for _, w, _ in uncovered)
    due = total >= AUDIT_THRESHOLD

    print(f"Audits found: {len(list(AUDITS_DIR.glob('*-audit.md')))} "
          f"(highest audited ticket: {high_water or 'none'})")
    print("Completed since last audit:")
    if uncovered:
        for tid, weight, name in uncovered:
            print(f"  {tid}  (weight {weight:g})  {name}")
    else:
        print("  (none)")
    if skipped:
        print(f"Skipped (no feature/bug/refactor Type): {len(skipped)}")
    print(f"Weighted count: {total:g} / {AUDIT_THRESHOLD:g}")
    print("AUDIT DUE" if due else "AUDIT NOT DUE")
    return 1 if due else 0


if __name__ == "__main__":
    sys.exit(main())
