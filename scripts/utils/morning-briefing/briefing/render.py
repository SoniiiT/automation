"""Ausgabe des Briefings als Terminaltext und als lokale HTML-Datei."""

from __future__ import annotations

import html
from pathlib import Path

from .models import Briefing, Bucket, PlannedTask
from .normalize import source_label
from .privacy import Redactor

_TITLES = {
    Bucket.NOW: "SOFORT",
    Bucket.TODAY: "HEUTE",
    Bucket.TODAY_OPTIONAL: "HEUTE WENN ZEIT BLEIBT",
    Bucket.TOMORROW: "KANN AUF MORGEN",
    Bucket.INFO: "NUR INFORMATION",
}


def render_text(briefing: Briefing, redactor: Redactor) -> str:
    lines: list[str] = []
    stamp = briefing.generated_at.strftime("%d.%m.%Y %H:%M")
    lines.append(f"MORGENBRIEFING - {stamp} ({briefing.timezone})")
    lines.append("=" * 60)

    for bucket in (Bucket.NOW, Bucket.TODAY, Bucket.TODAY_OPTIONAL, Bucket.TOMORROW, Bucket.INFO):
        tasks = briefing.bucket(bucket)
        if not tasks:
            continue
        lines.append("")
        lines.append(_TITLES[bucket])
        for number, task in enumerate(tasks, start=1):
            lines.extend(_text_task(number, task, redactor))

    if briefing.calendar:
        lines.append("")
        lines.append("TERMINE")
        for meeting in briefing.calendar:
            start = meeting.starts_at.strftime("%H:%M") if meeting.starts_at else "--:--"
            kind = "extern" if meeting.is_external else "intern"
            lines.append(f"  {start}  {redactor.restore(meeting.title)} ({kind})")

    if briefing.conflicts:
        lines.append("")
        lines.append("HINWEISE")
        for conflict in briefing.conflicts:
            lines.append(f"  - {redactor.restore(conflict)}")

    lines.append("")
    lines.append("QUELLEN")
    for status in briefing.statuses:
        marker = "ok" if status.ok else "FEHLT"
        lines.append(f"  [{marker}] {source_label(status.source)}: {status.label}")

    lines.append("")
    lines.append(f"KI-Zusammenfassung: {'aktiv' if briefing.ai_used else 'nicht verwendet'}")
    for note in briefing.notes:
        lines.append(f"  Hinweis: {note}")
    return "\n".join(lines)


def _text_task(number: int, task: PlannedTask, redactor: Redactor) -> list[str]:
    time_prefix = f"{task.suggested_time} " if task.suggested_time else ""
    lines = [f"  {number}. {time_prefix}{redactor.restore(task.summary)}"]
    if task.actions:
        lines.append(f"       Aktion: {', '.join(redactor.restore(a) for a in task.actions)}")
    if task.reason:
        lines.append(f"       Grund: {redactor.restore(task.reason)}")
    origin = " + ".join(task.source_labels)
    link = redactor.restore(task.link)
    lines.append(f"       Quelle: {origin}{(' | ' + link) if link else ''}")
    return lines


def render_html(briefing: Briefing, redactor: Redactor) -> str:
    def esc(value: str) -> str:
        return html.escape(redactor.restore(value or ""))

    parts = [
        "<!DOCTYPE html><html lang='de'><head><meta charset='utf-8'>",
        "<title>Morgenbriefing</title><style>",
        "body{font-family:Segoe UI,Arial,sans-serif;margin:2rem auto;max-width:52rem;",
        "background:#f7f7f8;color:#1b1b1f}h1{font-size:1.4rem}h2{margin-top:2rem;",
        "font-size:1rem;letter-spacing:.08em;text-transform:uppercase;color:#55555f}",
        "li{background:#fff;border:1px solid #e2e2e8;border-radius:8px;padding:.8rem 1rem;",
        "margin-bottom:.6rem;list-style:none}.meta{color:#66666f;font-size:.85rem}",
        ".critical{border-left:4px solid #c62828}.high{border-left:4px solid #ef6c00}",
        ".normal{border-left:4px solid #1565c0}.info{border-left:4px solid #9e9e9e}",
        "ul{padding:0}.time{font-weight:600;margin-right:.4rem}</style></head><body>",
        f"<h1>Morgenbriefing {esc(briefing.generated_at.strftime('%d.%m.%Y %H:%M'))}</h1>",
    ]

    for bucket in (Bucket.NOW, Bucket.TODAY, Bucket.TODAY_OPTIONAL, Bucket.TOMORROW, Bucket.INFO):
        tasks = briefing.bucket(bucket)
        if not tasks:
            continue
        parts.append(f"<h2>{_TITLES[bucket]}</h2><ul>")
        for task in tasks:
            css = task.priority.value if task.priority.value in {"critical", "high", "info"} else "normal"
            time_html = f"<span class='time'>{esc(task.suggested_time)}</span>" if task.suggested_time else ""
            link_html = (
                f" &middot; <a href='{esc(task.link)}'>Original</a>" if task.link else ""
            )
            parts.append(
                f"<li class='{css}'>{time_html}{esc(task.summary)}"
                f"<div class='meta'>{esc(', '.join(task.actions))}</div>"
                f"<div class='meta'>{esc(task.reason)} &middot; "
                f"{html.escape(' + '.join(task.source_labels))}{link_html}</div></li>"
            )
        parts.append("</ul>")

    if briefing.calendar:
        parts.append("<h2>Termine</h2><ul>")
        for meeting in briefing.calendar:
            start = meeting.starts_at.strftime("%H:%M") if meeting.starts_at else "--:--"
            parts.append(
                f"<li class='normal'><span class='time'>{start}</span>{esc(meeting.title)}"
                f"<div class='meta'>{'extern' if meeting.is_external else 'intern'}</div></li>"
            )
        parts.append("</ul>")

    if briefing.conflicts:
        parts.append("<h2>Hinweise</h2><ul>")
        parts.extend(f"<li class='high'>{esc(c)}</li>" for c in briefing.conflicts)
        parts.append("</ul>")

    parts.append("<h2>Quellen</h2><ul>")
    for status in briefing.statuses:
        state = "ok" if status.ok else "nicht verfuegbar"
        parts.append(
            f"<li class='{'normal' if status.ok else 'high'}'>"
            f"{source_label(status.source)}: {html.escape(status.label)} ({state})</li>"
        )
    parts.append("</ul>")
    parts.append(
        f"<p class='meta'>KI-Zusammenfassung: {'aktiv' if briefing.ai_used else 'nicht verwendet'}</p>"
    )
    for note in briefing.notes:
        parts.append(f"<p class='meta'>{esc(note)}</p>")
    parts.append("</body></html>")
    return "".join(parts)


def write_html(briefing: Briefing, redactor: Redactor, output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    target = output_dir / f"briefing-{briefing.generated_at:%Y-%m-%d}.html"
    target.write_text(render_html(briefing, redactor), encoding="utf-8")
    return target
