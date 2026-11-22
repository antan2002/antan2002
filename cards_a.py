"""Hero, heatmap and activity cards."""
from pathlib import Path

from card_style import (W, STATIC, INK, MUTED, BLUE, PAPER, LINE, header,
                        footer, text, anim, esc)


def hero(d):
    h = 432
    parts = [header(W, h, "Antan Roy. Full stack engineer and AI builder.")]
    parts.append(f'<rect width="{W}" height="{h}" rx="14" fill="{PAPER}"/>')
    parts.append(f'<rect x="40" y="42" width="8" height="8" rx="2" fill="{BLUE}"/>')
    parts.append(text(56, 51, "FULL STACK ENGINEER  ·  AI BUILDER", 12, MUTED,
                      "GeistMono", spacing=1.4, cls="r", delay=0.1))
    parts.append(text(38, 158, "Antan", 78, INK, "Geist600", cls="r", delay=0.2))
    parts.append(text(38, 238, "Roy", 78, BLUE, "SerifItalic", cls="r", delay=0.3))
    parts.append(text(42, 296, "I build scalable web apps, AI-powered systems", 19, INK,
                      cls="r", delay=0.45))
    parts.append(text(42, 322, "& real-time platforms people actually use.", 19, INK,
                      cls="r", delay=0.55))
    parts.append(text(42, 372, "antanroy.vercel.app  ↗", 13, BLUE,
                      "GeistMono", cls="r", delay=0.7))
    parts.append(text(42, 404, "KOLKATA, INDIA  ·  OPEN TO WORK", 10, MUTED,
                      "GeistMono", spacing=1.1, cls="r", delay=0.8))
    art = Path(__file__).parent.joinpath("avatar_ascii.txt")
    if art.exists():
        lines = art.read_text(encoding="utf-8").splitlines()
        parts.append(f'<g class="r" {anim(0.5)}>')
        parts.append('<text x="468" y="70" font-size="5.4" fill="' + BLUE +
                     '" font-family="\'Geist Mono\', monospace" xml:space="preserve">')
        for i, line in enumerate(lines):
            parts.append(f'<tspan x="468" dy="7.4">{esc(line)}</tspan>')
        parts.append("</text></g>")
    parts.append(footer())
    return "".join(parts)


def heatmap(d):
    from datetime import datetime, timedelta
    h = 257
    parts = [header(W, h, f"Contribution heatmap: {d['total_contributions_year']} contributions")]
    parts.append(f'<rect width="{W}" height="{h}" rx="14" fill="{PAPER}"/>')
    parts.append(f'<text x="42" y="62" font-size="34" fill="{INK}" class="r" {anim(0.1)} '
                 f'font-family="\'Instrument Serif\',Georgia,serif">Every day, '
                 f'<tspan font-style="italic" fill="{BLUE}">in blue</tspan></text>')
    parts.append(text(836, 60, f"{d['total_contributions_year']} CONTRIBUTIONS", 11,
                      MUTED, "GeistMono", anchor="end", cls="f", delay=0.2))
    days = d.get("days", [])
    counts = {r["date"]: r["count"] for r in days}
    mx = max((r["count"] for r in days), default=1) or 1
    ramp = ["#e6e8f2", "#b9c6ff", "#7f97ff", "#5274ff", BLUE]
    start = datetime.fromisoformat(days[0]["date"]).date() if days else datetime.now().date()
    for i in range(52 * 7):
        w, row = divmod(i, 7)
        date = start + timedelta(days=i)
        c = counts.get(date.isoformat(), 0)
        fill = ramp[0] if c == 0 else ramp[min(4, max(1, int(c / mx * 4) + 1))]
        a = anim(0.2 + i * 0.004)
        parts.append(f'<rect x="{50 + w * 15}" y="{100 + row * 15}" width="11" height="11" '
                     f'rx="2.5" fill="{fill}" class="p" {a}/>')
    parts.append(text(50, 236, "JAN", 10, MUTED, "GeistMono", cls="f", delay=0.9))
    parts.append(text(830, 236, "DEC", 10, MUTED, "GeistMono", anchor="end", cls="f", delay=0.9))
    parts.append(text(690, 236, "Less", 10, MUTED, "GeistMono", cls="f", delay=0.9))
    for i, col in enumerate(ramp):
        parts.append(f'<rect x="{726 + i * 14}" y="226" width="10" height="10" rx="2" fill="{col}"/>')
    parts.append(text(800, 236, "More", 10, MUTED, "GeistMono", cls="f", delay=0.9))
    parts.append(footer())
    return "".join(parts)


def activity(d):
    from datetime import datetime
    h = 352
    months = d.get("months", [])[-12:]
    year = d.get("year", 2026)
    total = d["total_contributions_year"]
    parts = [header(W, h, f"{total} contributions in {year}")]
    parts.append(f'<rect width="{W}" height="340" rx="14" fill="{PAPER}"/>')
    parts.append(text(40, 58, "THE LAST 12 MONTHS ON GITHUB", 11, MUTED,
                      "GeistMono", spacing=1.2, cls="f", delay=0.2))
    parts.append(f'<text x="40" y="110" font-size="38" fill="{INK}" class="r" {anim(0.3)} '
                 f'font-family="\'Instrument Serif\',Georgia,serif">{total} contributions '
                 f'<tspan font-style="italic" fill="{BLUE}">this year</tspan></text>')
    if not months:
        parts.append(footer())
        return "".join(parts)
    mx = max(m["count"] for m in months) or 1
    slot = 780 / len(months)
    bw = min(44, slot * 0.62)
    base = 268
    for i, m in enumerate(months):
        bh = max(2, m["count"] / mx * 116)
        x = 50 + i * slot + (slot - bw) / 2
        y = base - bh
        a = anim(0.5 + i * 0.055)
        parts.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{bw:.1f}" height="{bh:.1f}" '
                     f'rx="4" fill="{BLUE if i % 2 == 0 else "#5274ff"}" class="g" {a}/>')
        name = datetime.strptime(m["month"], "%Y-%m").strftime("%b")
        parts.append(text(x + bw / 2, 290, name, 11, MUTED, "GeistMono",
                          anchor="middle", cls="f", delay=0.9 + i * 0.03))
    days = d.get("days", [])
    busiest = max((r["count"] for r in days), default=0)
    active = d.get("active_days", 0)
    span = len(days) or 365
    stats = [
        (f"{d['streak_days']} day", "current streak", 500, 40),
        (f"{active} / {span}", "days with a commit", 500, 330),
        (str(busiest), "on the busiest day", 500, 620),
    ]
    for value, label, delay, x in stats:
        parts.append(text(x, 322, value, 20, INK, "Geist600", cls="r", delay=delay / 1000))
        parts.append(text(x, 338, label, 11, MUTED, cls="f", delay=delay / 1000))
    parts.append(footer())
    return "".join(parts)
