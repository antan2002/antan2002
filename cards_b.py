"""Stat tiles, section titles and repository cards."""
from card_style import (W, STATIC, INK, MUTED, BLUE, RED, YELLOW, NIGHT,
                        MOON, header, footer, text, anim, esc)


def tile(key, value, unit, caption_lines, color, fg="#ffffff"):
    w, h = 293.333, 222
    parts = [header(w, h, f"{key}: {value} {unit}")]
    parts.append(f'<rect x="4" y="6" width="285.333" height="210" rx="14" fill="{color}"/>')
    parts.append(text(24, 40, key, 12, fg, "GeistMono", spacing=1.6,
                      cls="sl", delay=0.2))
    parts.append(text(262, 40, "→", 20, fg, anchor="end", cls="sl", delay=0.3))
    steps = 18 if value <= 60 else 24
    for i in range(steps + 1):
        n = round(value * i / steps)
        if i < steps:
            vis = (f'<set attributeName="visibility" to="visible" '
                   f'begin="{0.6 + i * 0.045:.2f}s" dur="0.045s"/>')
        else:
            vis = ('<set attributeName="visibility" to="visible" '
                   'begin="{:.2f}s" fill="freeze"/>'.format(0.6 + steps * 0.045))
        shown = "visible" if STATIC else "hidden"
        parts.append(f'<text x="24" y="124" font-size="76" fill="{fg}" '
                     f'font-family="Geist, sans-serif" font-weight="600" '
                     f'visibility="{shown}">{n}{vis}</text>')
    parts.append(text(24, 150, unit, 11, fg, "GeistMono", cls="f", delay=0.5))
    for i, line in enumerate(caption_lines):
        parts.append(text(24, 180 + i * 17, line, 12, fg, cls="f", delay=0.9 + i * 0.08))
    parts.append(footer())
    return "".join(parts)


def title_card(dark=True):
    fg = MOON if dark else INK
    p = [header(W, 64, "What I'm coding")]
    p.append(f'<text x="2" y="46" font-size="34" fill="{fg}" class="r" {anim(0.1)} '
             f'font-family="\'Instrument Serif\',Georgia,serif">What I\'m '
             f'<tspan font-style="italic">coding</tspan></text>')
    p.append(footer())
    return "".join(p)


def repo_card(repo, delay=0.1):
    w, h = 293.333, 188
    name = repo.get("name", "repo")
    desc = repo.get("description") or ""
    lang = repo.get("language") or "Code"
    col = repo.get("lang_color") or BLUE
    stars = repo.get("stars", 0)
    parts = [header(w, h, f"{name}: {desc}")]
    parts.append(f'<rect x="4" y="6" width="285.333" height="176" rx="14" fill="#f3f3f1"/>')
    parts.append(f'<g class="r" {anim(delay)}>')
    parts.append(f'<rect x="24" y="30" width="8" height="8" rx="2" fill="{BLUE}"/>')
    parts.append(text(40, 39, name, 18, INK, "Geist600"))
    lines = []
    words = desc.split()
    cur = ""
    for word in words:
        if len(cur + " " + word) > 34:
            lines.append(cur.strip())
            cur = word
        else:
            cur = (cur + " " + word).strip()
    if cur:
        lines.append(cur)
    for i, line in enumerate(lines[:3]):
        parts.append(text(24, 64 + i * 18, line, 12.5, MUTED))
    parts.append(f'<line x1="24" y1="140" x2="261" y2="140" stroke="#dcdcd7"/>')
    parts.append(f'<circle cx="29" cy="158" r="5" fill="{col}"/>')
    parts.append(text(40, 162, lang, 11, MUTED))
    parts.append(text(261, 162, f"★ {stars}", 11, MUTED, "GeistMono", anchor="end"))
    parts.append("</g>")
    parts.append(footer())
    return "".join(parts)
