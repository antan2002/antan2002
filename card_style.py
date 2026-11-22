"""Palette, fonts and animation helpers for the profile cards."""
import base64
import os
from pathlib import Path

W = 880
STATIC = os.environ.get("STATIC", "0") == "1"
INK, MUTED, LINE, PAPER = "#111111", "#6e6e73", "#dcdcd7", "#f3f3f1"
BLUE, RED, YELLOW, NIGHT, MOON = "#2f55ff", "#ef3b2d", "#ffc81a", "#111111", "#e6edf3"
FONTS = {"Geist": "geist-400.woff2", "Geist600": "geist-600.woff2",
         "GeistMono": "geistmono-400.woff2", "Serif": "instrument-serif-400.woff2",
         "SerifItalic": "instrument-serif-italic-400.woff2"}


def font_css():
    out = []
    for fam, fn in FONTS.items():
        p = Path(__file__).parent / "fonts" / fn
        if not p.exists():
            continue
        b = base64.b64encode(p.read_bytes()).decode()
        style = "italic" if "Italic" in fam else "normal"
        weight = "600" if fam == "Geist600" else "400"
        name = fam.replace("600", "")
        out.append(f"@font-face{{font-family:'{name}';font-style:{style};"
                   f"font-weight:{weight};src:url(data:font/woff2;base64,{b}) format('woff2')}}")
    return "".join(out)


CSS = """@keyframes rise{from{opacity:0;transform:translateY(16px)}to{opacity:1;transform:none}}
@keyframes fade{from{opacity:0}to{opacity:1}}
@keyframes grow{from{transform:scaleY(0)}to{transform:scaleY(1)}}
@keyframes pop{0%{opacity:0;transform:scale(.4)}70%{opacity:1;transform:scale(1.12)}100%{opacity:1;transform:none}}
@keyframes pulse{0%,100%{opacity:1}50%{opacity:.25}}
@keyframes slidein{from{opacity:0;transform:translateX(-24px)}to{opacity:1;transform:none}}
.r{opacity:0;animation:rise .8s cubic-bezier(.2,.7,.2,1) both;transform-box:fill-box}
.f{opacity:0;animation:fade .9s ease-out both}
.g{transform-box:fill-box;transform-origin:bottom;transform:scaleY(0);animation:grow .8s cubic-bezier(.2,.7,.2,1) both}
.p{opacity:0;transform-box:fill-box;transform-origin:center;animation:pop .5s ease-out both}
.s{opacity:0;transform-box:fill-box;animation:slidein .7s cubic-bezier(.2,.7,.2,1) both}
.live{animation:pulse 1.8s ease-in-out infinite}
@media (prefers-reduced-motion:reduce){.r,.f,.g,.p,.s,.live{animation:none!important;opacity:1!important;transform:none!important}}
"""


def esc(s):
    return (str(s).replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))


def anim(delay, extra=""):
    if STATIC:
        return ""
    return f'style="animation-delay:{delay:.2f}s;{extra}"'


def header(width, height, label, extra_css=""):
    static_css = "*{animation:none!important;opacity:1!important;transform:none!important}" if STATIC else ""
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{width:.3f}" height="{height}" '
            f'viewBox="0 0 {width:.3f} {height}" role="img" aria-label="{esc(label)}">'
            f'<title>{esc(label)}</title><style>{font_css()}{CSS}{extra_css}{static_css}</style>')


def footer():
    return "</svg>"


def text(x, y, value, size=14, fill=INK, family="Geist", weight=None,
         anchor=None, spacing=None, cls="", delay=0, italic=False, extra=""):
    attrs = [f'x="{x}"', f'y="{y}"', f'font-size="{size}"', f'fill="{fill}"']
    fam = {"Geist": "Geist, system-ui, sans-serif", "Geist600": "Geist, system-ui, sans-serif",
           "GeistMono": "'Geist Mono', ui-monospace, monospace",
           "Serif": "'Instrument Serif', Georgia, serif",
           "SerifItalic": "'Instrument Serif', Georgia, serif"}[family]
    attrs.append(f'font-family="{fam}"')
    if weight or family == "Geist600":
        attrs.append('font-weight="600"')
    if italic or family == "SerifItalic":
        attrs.append('font-style="italic"')
    if anchor:
        attrs.append(f'text-anchor="{anchor}"')
    if spacing is not None:
        attrs.append(f'letter-spacing="{spacing}"')
    a = anim(delay, extra)
    if a:
        attrs.append(a)
    cls_attr = f'class="{cls}"' if cls else ""
    return f"<text {' '.join(attrs)} {cls_attr}>{esc(value)}</text>"
