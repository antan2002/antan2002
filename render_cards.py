#!/usr/bin/env python3
"""
render_cards.py — Antan Roy's GitHub README card renderer.

Generates animated SVG cards into cards/ from contributions.json.
Set STATIC=1 to freeze all animations (final frame, no motion).

Cards produced
--------------
cards/hero.svg          — name + tagline + avatar portrait
cards/links.svg         — three linked tiles (Portfolio / LinkedIn / LeetCode)
cards/chart.svg         — contributions-per-month bar chart + stats strip
cards/repo_{name}.svg   — one card per featured repo
cards/contrib_graph.svg — heatmap-style contribution graph

README.md is also regenerated to wire everything together.
"""

import base64
import json
import math
import os
import sys
import textwrap
import urllib.request
from pathlib import Path

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

STATIC = os.environ.get("STATIC", "0") == "1"      # freeze animations
DATA   = Path("contributions.json")
OUT    = Path("cards")
OUT.mkdir(exist_ok=True)

# Brand palette (matches #1e2327 GitHub dark + accent from readme typing SVG)
DARK_BG   = "#0d1117"
CARD_BG   = "#161b22"
BORDER    = "#30363d"
ACCENT    = "#3b82f6"          # blue — primary brand
ACCENT2   = "#10b981"          # emerald — secondary
TEXT_HI   = "#e6edf3"          # high-contrast text
TEXT_MID  = "#8b949e"          # mid-grey
TEXT_LOW  = "#484f58"
LANG_COLS = {"JavaScript": "#f7df1e", "TypeScript": "#3178c6",
             "Python": "#3572a5", "default": ACCENT}

W = 860   # card width  (all cards share the same width)

# ---------------------------------------------------------------------------
# Font subsetting helper
# ---------------------------------------------------------------------------

CHARS_NEEDED = (
    "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
    "0123456789 .,·/:@#!?-_|★⭐🔥"
)

_FONT_CACHE: dict[str, str] = {}


def _subset_and_encode(ttf_path: str | None, chars: str) -> str | None:
    """Return base64 WOFF2 data URI for a subset of a TTF, or None."""
    if ttf_path is None:
        return None
    key = ttf_path
    if key in _FONT_CACHE:
        return _FONT_CACHE[key]
    try:
        from fontTools.ttLib import TTFont           # type: ignore
        from fontTools.subset import Subsetter, Options  # type: ignore
        import io, tempfile
        opts = Options()
        opts.flavor = "woff2"
        opts.desubroutinize = True
        font = TTFont(ttf_path)
        sub  = Subsetter(options=opts)
        sub.populate(text=chars)
        sub.subset(font)
        buf = io.BytesIO()
        font.save(buf)
        b64 = base64.b64encode(buf.getvalue()).decode()
        uri = f"data:font/woff2;base64,{b64}"
        _FONT_CACHE[key] = uri
        return uri
    except Exception:
        return None


def _google_font_fallback(family: str) -> str:
    """Minimal @import for a Google font (network-unavailable in SVG img tags)."""
    # SVG rendered as <img> cannot fetch external resources.
    # We fall back to system fonts; this is here only as documentation.
    return ""


# ---------------------------------------------------------------------------
# Animation helpers
# ---------------------------------------------------------------------------

MOTION_WRAP_OPEN  = '<g class="motion">'
MOTION_WRAP_CLOSE = "</g>"

GLOBAL_CSS = (
    "<style>\n"
    "  @media (prefers-reduced-motion: reduce) {\n"
    "    * { animation: none !important; transition: none !important; }\n"
    "  }\n"
    "  text { font-family: -apple-system, 'Segoe UI', Helvetica, Arial, sans-serif; }\n"
    f"  .dim  {{ fill: {TEXT_MID}; }}\n"
    f"  .hi   {{ fill: {TEXT_HI}; }}\n"
    f"  .acc  {{ fill: {ACCENT}; }}\n"
    f"  .card {{ fill: {CARD_BG}; stroke: {BORDER}; stroke-width: 1; }}\n"
    "  @keyframes fadeUp {\n"
    "    from { opacity: 0; transform: translateY(14px); }\n"
    "    to   { opacity: 1; transform: translateY(0); }\n"
    "  }\n"
    "  @keyframes barGrow {\n"
    "    from { transform: scaleY(0); }\n"
    "    to   { transform: scaleY(1); }\n"
    "  }\n"
    "  @keyframes pulse {\n"
    "    0%,100% { opacity: 1; }\n"
    "    50%     { opacity: .5; }\n"
    "  }\n"
    "</style>\n"
)


def anim_attr(delay_s: float, dur_s: float = 0.55, fill: str = "forwards") -> str:
    """Return animation shorthand string, or empty string when STATIC."""
    if STATIC:
        return ""
    return (
        f'style="animation: fadeUp {dur_s}s ease {delay_s:.2f}s {fill} both;"'
    )


def smil_appear(delay_s: float, dur_s: float = 0.5) -> str:
    """SMIL animate for opacity 0→1 (works in <img> SVG)."""
    if STATIC:
        return ""
    begin = f"{delay_s:.2f}s"
    return (
        f'<animate attributeName="opacity" from="0" to="1" '
        f'begin="{begin}" dur="{dur_s}s" fill="freeze"/>'
    )


def smil_slide(delay_s: float, dy: int = 12, dur_s: float = 0.5) -> str:
    if STATIC:
        return ""
    begin = f"{delay_s:.2f}s"
    return (
        f'<animateTransform attributeName="transform" type="translate" '
        f'from="0,{dy}" to="0,0" begin="{begin}" dur="{dur_s}s" fill="freeze"/>'
    )


def svg_header(h: int, extra_css: str = "") -> str:
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{h}" '
        f'viewBox="0 0 {W} {h}" role="img">\n'
        f'{GLOBAL_CSS}{extra_css}'
        f'<rect width="{W}" height="{h}" rx="12" fill="{DARK_BG}"/>\n'
    )


def svg_footer() -> str:
    return "</svg>"


# ---------------------------------------------------------------------------
# Download avatar
# ---------------------------------------------------------------------------

def _fetch_avatar(url: str, size: int = 80) -> str | None:
    """Return base64 PNG data URI for the avatar, or None on failure."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "readme-bot/1.0"})
        with urllib.request.urlopen(req, timeout=10) as r:
            data = r.read()
        b64 = base64.b64encode(data).decode()
        return f"data:image/png;base64,{b64}"
    except Exception:
        return None


# ---------------------------------------------------------------------------
# CARD 1 — Hero
# ---------------------------------------------------------------------------

def card_hero(d: dict) -> str:
    H = 170
    avatar_uri = _fetch_avatar(d["avatar_url"])
    r = 44  # avatar radius
    ax, ay = W - 80, H // 2

    parts = [svg_header(H)]

    # avatar circle clip + image
    if avatar_uri:
        parts.append(
            f'<defs><clipPath id="av"><circle cx="{ax}" cy="{ay}" r="{r}"/></clipPath></defs>'
        )
        # ring
        g = '<g opacity="0">' if not STATIC else '<g>'
        sa = smil_appear(0.05, 0.4)
        st = smil_slide(0.05, 10, 0.4)
        parts.append(
            f'{g}<circle cx="{ax}" cy="{ay}" r="{r+3}" '
            f'fill="none" stroke="{ACCENT}" stroke-width="2" stroke-dasharray="6 4">'
            + (sa if not STATIC else "")
            + f'</circle>'
            f'<image href="{avatar_uri}" x="{ax-r}" y="{ay-r}" '
            f'width="{r*2}" height="{r*2}" clip-path="url(#av)">'
            + (sa if not STATIC else "")
            + f'</image></g>'
        )
        if not STATIC:
            # pulse ring
            parts.append(
                f'<circle cx="{ax}" cy="{ay}" r="{r+3}" '
                f'fill="none" stroke="{ACCENT}" stroke-width="1.5" opacity="0">'
                f'<animate attributeName="opacity" values="0;0.6;0" dur="2.4s" begin="1s" repeatCount="indefinite"/>'
                f'<animate attributeName="r" values="{r+3};{r+12}" dur="2.4s" begin="1s" repeatCount="indefinite"/>'
                f'</circle>'
            )

    # name
    g = '<g opacity="0">' if not STATIC else '<g>'
    sa0 = smil_appear(0.0, 0.5)
    parts.append(
        f'{g}<text x="36" y="58" font-size="30" font-weight="700" fill="{TEXT_HI}">'
        + (sa0 if not STATIC else "")
        + 'Antan Roy</text></g>'
    )

    # tagline
    g = '<g opacity="0">' if not STATIC else '<g>'
    sa1 = smil_appear(0.15, 0.5)
    st1 = smil_slide(0.15, 8, 0.45)
    parts.append(
        f'{g}<text x="36" y="90" font-size="14" fill="{ACCENT}">'
        + (sa1 if not STATIC else "")
        + 'Full Stack Engineer · AI Builder · Open Source Contributor</text></g>'
    )

    # sub-line
    g = '<g opacity="0">' if not STATIC else '<g>'
    sa2 = smil_appear(0.28, 0.5)
    parts.append(
        f'{g}<text x="36" y="116" font-size="13" fill="{TEXT_MID}">'
        + (sa2 if not STATIC else "")
        + 'Building scalable web apps, AI-powered systems &amp; real-time platforms.</text></g>'
    )

    # location + status badge
    g = '<g opacity="0">' if not STATIC else '<g>'
    sa3 = smil_appear(0.38, 0.5)
    parts.append(
        f'{g}<rect x="36" y="130" width="140" height="22" rx="11" fill="{BORDER}"/>'
        f'<text x="52" y="145" font-size="12" fill="{TEXT_MID}">📍 Kolkata, India</text>'
        f'<rect x="192" y="130" width="136" height="22" rx="11" fill="{BORDER}"/>'
        f'<circle cx="208" cy="141" r="5" fill="{ACCENT2}">'
        + ('' if STATIC else
            f'<animate attributeName="opacity" values="1;0.3;1" dur="2s" repeatCount="indefinite"/>')
        + f'</circle>'
        f'<text x="218" y="145" font-size="12" fill="{TEXT_MID}">Open to work</text>'
        + (sa3 if not STATIC else "")
        + '</g>'
    )

    parts.append(svg_footer())
    return "".join(parts)


# ---------------------------------------------------------------------------
# CARD 2 — Links (three tiles)
# ---------------------------------------------------------------------------

ICONS = {
    "globe": (
        'M12 2a10 10 0 1 0 0 20A10 10 0 0 0 12 2zm0 18c-4.42 0-8-3.58-8-8s3.58-8 8-8 8 3.58 8 8-3.58 8-8 8z'
        'M12 6a6 6 0 1 1 0 12A6 6 0 0 1 12 6zm0 2a4 4 0 1 0 0 8 4 4 0 0 0 0-8z'
    ),
    "linkedin": (
        'M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.445-2.136 2.939v5.667H9.351V9h3.414v1.561h.046c.477-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286zM5.337 7.433a2.062 2.062 0 0 1-2.063-2.065 2.064 2.064 0 1 1 2.063 2.065zm1.782 13.019H3.555V9h3.564v11.452zM22.225 0H1.771C.792 0 0 .774 0 1.729v20.542C0 23.227.792 24 1.771 24h20.451C23.2 24 24 23.227 24 22.271V1.729C24 .774 23.2 0 22.222 0h.003z'
    ),
    "code": (
        'M9.4 16.6L4.8 12l4.6-4.6L8 6l-6 6 6 6 1.4-1.4zm5.2 0l4.6-4.6-4.6-4.6L16 6l6 6-6 6-1.4-1.4z'
    ),
}


def _icon_svg(key: str, x: float, y: float, sz: int = 24, col: str = TEXT_MID) -> str:
    path = ICONS.get(key, ICONS["globe"])
    # scale from 24x24 viewBox to sz
    scale = sz / 24
    tx = x - sz / 2
    ty = y - sz / 2
    return (
        f'<g transform="translate({tx:.1f},{ty:.1f}) scale({scale:.4f})">'
        f'<path d="{path}" fill="{col}"/></g>'
    )


def card_links(d: dict) -> str:
    links = d["links"]
    H = 100
    tile_w = (W - 48) // 3  # three tiles with gaps
    gap = 16
    total = tile_w * 3 + gap * 2
    start_x = (W - total) // 2

    parts = [svg_header(H)]

    for i, lnk in enumerate(links[:3]):
        tx = start_x + i * (tile_w + gap)
        ty = 12
        th = H - 24
        delay = 0.1 + i * 0.12

        g_open = '<g opacity="0">' if not STATIC else '<g>'
        sa = smil_appear(delay, 0.45)

        parts.append(
            f'{g_open}'
            f'<a href="{lnk["url"]}" target="_blank" rel="noopener">'
            f'<rect x="{tx}" y="{ty}" width="{tile_w}" height="{th}" rx="10" '
            f'fill="{CARD_BG}" stroke="{BORDER}" stroke-width="1"/>'
            + (sa if not STATIC else "")
            + f'</a>'
        )
        # icon
        parts.append(_icon_svg(lnk["icon"], tx + 36, ty + th // 2, 22, ACCENT))
        # label
        parts.append(
            f'<text x="{tx + 64}" y="{ty + th // 2 + 5}" '
            f'font-size="14" font-weight="600" fill="{TEXT_HI}">{lnk["label"]}</text>'
            f'</g>'
        )

    parts.append(svg_footer())
    return "".join(parts)


# ---------------------------------------------------------------------------
# CARD 3 — Contributions chart + stats
# ---------------------------------------------------------------------------

def card_chart(d: dict) -> str:
    months  = d["months"][-12:]
    streak  = d["streak_days"]
    active  = d["active_days"]
    busiest = d["busiest_day"]

    H       = 230
    PAD_L   = 40
    PAD_R   = 24
    PAD_T   = 44
    PAD_B   = 70   # room for x-labels + stats strip
    chart_w = W - PAD_L - PAD_R
    chart_h = H - PAD_T - PAD_B

    max_c = max(m["count"] for m in months) or 1
    bar_w = chart_w / len(months)
    bar_gap = bar_w * 0.25

    parts = [
        svg_header(H),
        f'<text x="24" y="28" font-size="14" font-weight="700" fill="{TEXT_HI}">Contribution Activity</text>',
        # grid lines
    ]

    # horizontal grid
    for pct in [0.25, 0.5, 0.75, 1.0]:
        gy = PAD_T + chart_h - chart_h * pct
        val = int(max_c * pct)
        parts.append(
            f'<line x1="{PAD_L}" y1="{gy:.1f}" x2="{W - PAD_R}" y2="{gy:.1f}" '
            f'stroke="{BORDER}" stroke-width="1"/>'
            f'<text x="{PAD_L - 4}" y="{gy + 4:.1f}" text-anchor="end" '
            f'font-size="10" fill="{TEXT_LOW}">{val}</text>'
        )

    # bars
    for i, m in enumerate(months):
        bx = PAD_L + i * bar_w + bar_gap / 2
        bh = (m["count"] / max_c) * chart_h
        by = PAD_T + chart_h - bh
        bw = bar_w - bar_gap
        label = m["month"][5:]   # "MM"

        is_max = m["count"] == max_c
        fill   = ACCENT if not is_max else ACCENT2
        delay  = 0.05 + i * 0.045

        # bar (SMIL scaleY)
        pivot_y = PAD_T + chart_h
        if STATIC:
            parts.append(
                f'<rect x="{bx:.1f}" y="{by:.1f}" width="{bw:.1f}" height="{bh:.1f}" '
                f'rx="3" fill="{fill}"/>'
            )
        else:
            parts.append(
                f'<rect x="{bx:.1f}" y="{PAD_T + chart_h:.1f}" width="{bw:.1f}" height="0" '
                f'rx="3" fill="{fill}">'
                f'<animate attributeName="height" from="0" to="{bh:.2f}" '
                f'begin="{delay:.2f}s" dur="0.4s" fill="freeze"/>'
                f'<animate attributeName="y" from="{PAD_T + chart_h:.1f}" to="{by:.2f}" '
                f'begin="{delay:.2f}s" dur="0.4s" fill="freeze"/>'
                f'</rect>'
            )

        # tooltip count on hover — works via SVG title
        cx = bx + bw / 2
        parts.append(
            f'<text x="{cx:.1f}" y="{PAD_T + chart_h + 14:.1f}" text-anchor="middle" '
            f'font-size="10" fill="{TEXT_LOW}">{label}</text>'
        )
        if is_max:
            parts.append(
                f'<text x="{cx:.1f}" y="{by - 4:.1f}" text-anchor="middle" '
                f'font-size="10" fill="{ACCENT2}">▲</text>'
            )

    # stats strip
    stats = [
        (f"{streak}d", "streak"),
        (f"{d['total_contributions_year']}", "contributions"),
        (f"{active}d", "active"),
        (busiest, "busiest day"),
    ]
    sw = W / len(stats)
    sy = H - 36
    g_open = '<g opacity="0">' if not STATIC else '<g>'
    sa_st = smil_appear(0.7, 0.4)
    parts.append(g_open + (sa_st if not STATIC else ""))
    for j, (val, lbl) in enumerate(stats):
        sx = sw * j + sw / 2
        parts.append(
            f'<text x="{sx:.1f}" y="{sy}" text-anchor="middle" '
            f'font-size="16" font-weight="700" fill="{TEXT_HI}">{val}</text>'
            f'<text x="{sx:.1f}" y="{sy + 16}" text-anchor="middle" '
            f'font-size="11" fill="{TEXT_MID}">{lbl}</text>'
        )
        if j < len(stats) - 1:
            divx = sw * (j + 1)
            parts.append(
                f'<line x1="{divx:.1f}" y1="{sy - 14}" x2="{divx:.1f}" y2="{sy + 20}" '
                f'stroke="{BORDER}" stroke-width="1"/>'
            )
    parts.append("</g>")

    parts.append(svg_footer())
    return "".join(parts)


# ---------------------------------------------------------------------------
# CARD 4 — Repo card
# ---------------------------------------------------------------------------

def card_repo(repo: dict, delay_base: float = 0.1) -> str:
    H   = 130
    name = repo["name"]
    desc = repo["description"]
    lang = repo["language"]
    lang_col = repo.get("lang_color", LANG_COLS.get(lang, LANG_COLS["default"]))
    stars = repo["stars"]
    forks = repo["forks"]
    url   = repo["url"]

    # Wrap description
    wrapped = textwrap.wrap(desc, width=74)

    parts = [svg_header(H)]

    g_open = '<g opacity="0">' if not STATIC else '<g>'
    sa = smil_appear(delay_base, 0.5)

    parts.append(f'{g_open}' + (sa if not STATIC else ""))

    # card bg
    parts.append(
        f'<rect x="12" y="12" width="{W - 24}" height="{H - 24}" rx="10" '
        f'fill="{CARD_BG}" stroke="{BORDER}" stroke-width="1"/>'
    )

    # repo icon (book)
    parts.append(
        '<g transform="translate(28,28) scale(0.75)">'
        '<path d="M2 2.5A2.5 2.5 0 0 1 4.5 0h8.75a.75.75 0 0 1 .75.75v12.5a.75.75 0 0 1-.75.75h-2.5a.75.75 0 0 1 0-1.5H12v-2h-8a1 1 0 0 0-.717 1.7.75.75 0 1 1-1.071 1.05A2.495 2.495 0 0 1 2 11.5zm10.5-1h-8a1 1 0 0 0-1 1v6.708A2.486 2.486 0 0 1 4.5 9h8.5V1.5z" '
        f'fill="{ACCENT}"/></g>'
    )

    # repo name
    parts.append(
        f'<text x="52" y="38" font-size="15" font-weight="700" fill="{ACCENT}">{name}</text>'
    )

    # description lines
    for li, line in enumerate(wrapped[:2]):
        parts.append(
            f'<text x="28" y="{60 + li * 18}" font-size="13" fill="{TEXT_MID}">{line}</text>'
        )

    # lang dot + stars + forks
    dot_y = H - 28
    parts.append(
        f'<circle cx="30" cy="{dot_y}" r="6" fill="{lang_col}"/>'
        f'<text x="42" y="{dot_y + 4}" font-size="12" fill="{TEXT_MID}">{lang}</text>'
        f'<text x="{W//2 - 40}" y="{dot_y + 4}" font-size="12" fill="{TEXT_MID}">⭐ {stars}</text>'
        f'<text x="{W//2 + 20}" y="{dot_y + 4}" font-size="12" fill="{TEXT_MID}">🍴 {forks}</text>'
    )

    parts.append("</g>")
    parts.append(svg_footer())
    return "".join(parts)


# ---------------------------------------------------------------------------
# CARD 5 — Contribution graph (heatmap)
# ---------------------------------------------------------------------------

def card_contrib_graph(d: dict) -> str:
    """52-week dot-grid styled in brand blue."""
    H = 160
    WEEKS = 52
    DAYS  = 7
    cell  = 12
    gap   = 3
    step  = cell + gap
    grid_w = WEEKS * step
    grid_h = DAYS  * step
    ox = (W - grid_w) // 2
    oy = 44

    # day labels
    day_labels = ["Mon", "", "Wed", "", "Fri", "", "Sun"]

    parts = [
        svg_header(H),
        f'<text x="24" y="28" font-size="14" font-weight="700" fill="{TEXT_HI}">Contribution Graph</text>',
    ]

    # day labels on left
    for di, dl in enumerate(day_labels):
        if dl:
            parts.append(
                f'<text x="{ox - 6}" y="{oy + di * step + cell - 1}" '
                f'text-anchor="end" font-size="9" fill="{TEXT_LOW}">{dl}</text>'
            )

    # generate pseudo-random heat from monthly data
    months = d["months"][-12:]
    total_year = sum(m["count"] for m in months)
    avg_week = total_year / 52

    import hashlib

    def _heat(week: int, day: int) -> float:
        """0..1 heat — reproducible pseudo-random based on week+day."""
        seed = hashlib.md5(f"{week}-{day}".encode()).digest()[0]
        base = (seed / 255) ** 1.4
        # weight by monthly distribution
        # The current year may have fewer than 12 months of data (e.g. in November),
        # so clamp to the last available month instead of assuming index 11 exists.
        month_idx = min(int(week / 52 * 12), len(months) - 1) if months else 0
        m_weight  = months[month_idx]["count"] / (avg_week * DAYS) if (avg_week and months) else 0.5
        return min(1.0, base * m_weight * 2.2)

    for w in range(WEEKS):
        for day in range(DAYS):
            heat = _heat(w, day)
            if heat < 0.05:
                fill = BORDER
            else:
                # blue gradient
                alpha = int(40 + heat * 215)
                r_ = int(0x3b + heat * (0x93 - 0x3b))
                g_ = int(0x82 + heat * (0xc5 - 0x82))
                b_ = int(0xf6 + heat * (0xff - 0xf6))
                fill = f"#{r_:02x}{g_:02x}{b_:02x}"

            cx = ox + w * step
            cy = oy + day * step
            delay = 0.02 + (w * DAYS + day) * 0.0005

            if STATIC:
                parts.append(
                    f'<rect x="{cx}" y="{cy}" width="{cell}" height="{cell}" '
                    f'rx="2" fill="{fill}"/>'
                )
            else:
                parts.append(
                    f'<rect x="{cx}" y="{cy}" width="{cell}" height="{cell}" '
                    f'rx="2" fill="{fill}" opacity="0">'
                    f'<animate attributeName="opacity" from="0" to="1" '
                    f'begin="{delay:.3f}s" dur="0.3s" fill="freeze"/>'
                    f'</rect>'
                )

    # legend
    lx = W - 120
    ly = H - 18
    parts.append(f'<text x="{lx}" y="{ly}" font-size="10" fill="{TEXT_LOW}">Less</text>')
    for li, heat in enumerate([0.0, 0.25, 0.5, 0.75, 1.0]):
        if heat < 0.05:
            fill = BORDER
        else:
            r_ = int(0x3b + heat * (0x93 - 0x3b))
            g_ = int(0x82 + heat * (0xc5 - 0x82))
            b_ = int(0xf6 + heat * (0xff - 0xf6))
            fill = f"#{r_:02x}{g_:02x}{b_:02x}"
        parts.append(
            f'<rect x="{lx + 32 + li * 13}" y="{ly - 10}" '
            f'width="10" height="10" rx="2" fill="{fill}"/>'
        )
    parts.append(f'<text x="{lx + 32 + 5 * 13 + 4}" y="{ly}" font-size="10" fill="{TEXT_LOW}">More</text>')

    parts.append(svg_footer())
    return "".join(parts)


# ---------------------------------------------------------------------------
# README generator
# ---------------------------------------------------------------------------

README_TEMPLATE = """\
<!-- Auto-generated — do not edit by hand. Run render_cards.py to rebuild. -->

<p align="center">
  <img src="cards/hero.svg" alt="Antan Roy — hero card" width="860"/>
</p>

<p align="center">
  <img src="cards/links.svg" alt="links" width="32.5%"/>
</p>

<p align="center">
  <img src="cards/chart.svg" alt="Contribution Activity" width="860"/>
</p>

{repo_rows}

<p align="center">
  <img src="cards/contrib_graph.svg" alt="Contribution Graph" width="860"/>
</p>
"""


def _repo_rows(repos: list[dict]) -> str:
    lines = []
    # Three repos → one row of three; more → rows of three
    row: list[str] = []
    for i, repo in enumerate(repos):
        name = repo["name"]
        row.append(f'  <img src="cards/repo_{name}.svg" alt="{name}" width="32.5%"/>')
        if len(row) == 3 or i == len(repos) - 1:
            lines.append('<p align="center">')
            lines.extend(row)
            lines.append("</p>")
            row = []
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    if not DATA.exists():
        print(f"ERROR: {DATA} not found. Create it or run the GitHub Action first.", file=sys.stderr)
        sys.exit(1)

    d = json.loads(DATA.read_text())
    mode = "STATIC (final frame)" if STATIC else "animated"
    print(f"Rendering cards [{mode}]…")

    # Hero
    p = OUT / "hero.svg"
    p.write_text(card_hero(d), encoding="utf-8")
    print(f"  ✓  {p}")

    # Links
    p = OUT / "links.svg"
    p.write_text(card_links(d), encoding="utf-8")
    print(f"  ✓  {p}")

    # Chart
    p = OUT / "chart.svg"
    p.write_text(card_chart(d), encoding="utf-8")
    print(f"  ✓  {p}")

    # Repo cards
    for i, repo in enumerate(d.get("repos", [])):
        delay = 0.08 + i * 0.1
        p = OUT / f"repo_{repo['name']}.svg"
        p.write_text(card_repo(repo, delay_base=delay), encoding="utf-8")
        print(f"  ✓  {p}")

    # Contribution graph
    p = OUT / "contrib_graph.svg"
    p.write_text(card_contrib_graph(d), encoding="utf-8")
    print(f"  ✓  {p}")

    # README
    rp = Path("README.md")
    repo_section = _repo_rows(d.get("repos", []))
    rp.write_text(README_TEMPLATE.format(repo_rows=repo_section), encoding="utf-8")
    print(f"  ✓  README.md")

    print(f"\nDone. {len(list(OUT.glob('*.svg')))} SVG cards in {OUT}/")
    if STATIC:
        print("Tip: open any .svg in a browser to screenshot it before pushing.")


if __name__ == "__main__":
    main()
