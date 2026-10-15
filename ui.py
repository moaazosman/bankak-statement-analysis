"""مكوّنات الواجهة: أيقونات SVG، الثيم، وCSS متجاوب."""
import html

ICONS = {
    "down": '<path d="M17 7 7 17"/><path d="M17 17H7V7"/>',
    "up": '<path d="M7 7h10v10"/><path d="M7 17 17 7"/>',
    "receipt": '<path d="M4 2v20l2-1 2 1 2-1 2 1 2-1 2 1 2-1 2 1V2l-2 1-2-1-2 1-2-1-2 1-2-1-2 1Z"/><path d="M16 8h-6a2 2 0 1 0 0 4h4a2 2 0 1 1 0 4H8"/><path d="M12 17.5v-11"/>',
    "wallet": '<path d="M19 7V4a1 1 0 0 0-1-1H5a2 2 0 0 0 0 4h15a1 1 0 0 1 1 1v4h-3a2 2 0 0 0 0 4h3a1 1 0 0 0 1-1v-2a1 1 0 0 0-1-1"/><path d="M3 5v14a2 2 0 0 0 2 2h15a1 1 0 0 0 1-1v-4"/>',
    "chart": '<path d="M3 3v16a2 2 0 0 0 2 2h16"/><path d="M18 17V9"/><path d="M13 17V5"/><path d="M8 17v-3"/>',
    "bulb": '<path d="M15 14c.2-1 .7-1.7 1.5-2.5 1-.9 1.5-2.2 1.5-3.5A6 6 0 0 0 6 8c0 1 .2 2.2 1.5 3.5.7.7 1.3 1.5 1.5 2.5"/><path d="M9 18h6"/><path d="M10 22h4"/>',
    "calendar": '<path d="M8 2v4"/><path d="M16 2v4"/><rect width="18" height="18" x="3" y="4" rx="2"/><path d="M3 10h18"/>',
    "pie": '<path d="M21.21 15.89A10 10 0 1 1 8 2.83"/><path d="M22 12A10 10 0 0 0 12 2v10z"/>',
    "layers": '<path d="m12.83 2.18a2 2 0 0 0-1.66 0L2.6 6.08a1 1 0 0 0 0 1.83l8.58 3.91a2 2 0 0 0 1.66 0l8.58-3.9a1 1 0 0 0 0-1.83Z"/><path d="m22 17.65-9.17 4.16a2 2 0 0 1-1.66 0L2 17.65"/><path d="m22 12.65-9.17 4.16a2 2 0 0 1-1.66 0L2 12.65"/>',
    "list": '<path d="M8 6h13"/><path d="M8 12h13"/><path d="M8 18h13"/><path d="M3 6h.01"/><path d="M3 12h.01"/><path d="M3 18h.01"/>',
    "shield": '<path d="M20 13c0 5-3.5 7.5-7.66 8.95a1 1 0 0 1-.67-.01C7.5 20.5 4 18 4 13V6a1 1 0 0 1 1-1c2 0 4.5-1.2 6.24-2.72a1.17 1.17 0 0 1 1.52 0C14.51 3.81 17 5 19 5a1 1 0 0 1 1 1z"/><path d="m9 12 2 2 4-4"/>',
    "file": '<path d="M15 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7Z"/><path d="M14 2v4a2 2 0 0 0 2 2h4"/><path d="M10 13h4"/><path d="M10 17h4"/>',
    "coins": '<circle cx="8" cy="8" r="6"/><path d="M18.09 10.37A6 6 0 1 1 10.34 18"/><path d="M7 6h1v4"/><path d="m16.71 13.88.7.71-2.82 2.82"/>',
    "user": '<path d="M19 21v-2a4 4 0 0 0-4-4H9a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/>',
    "download": '<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" x2="12" y1="15" y2="3"/>',
    "sliders": '<path d="M10 5H3"/><path d="M12 19H3"/><path d="M14 3v4"/><path d="M16 17v4"/><path d="M21 12h-9"/><path d="M21 19h-5"/><path d="M21 5h-7"/><path d="M8 10v4"/><path d="M8 12H3"/>',
    "trend": '<polyline points="22 7 13.5 15.5 8.5 10.5 2 17"/><polyline points="16 7 22 7 22 13"/>',
}


def svg(name, size=18, color="currentColor"):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" '
            f'viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" '
            f'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
            f'{ICONS[name]}</svg>')


LOGO = """<svg viewBox="0 0 64 64" xmlns="http://www.w3.org/2000/svg" class="logo" aria-hidden="true">
<defs><linearGradient id="lg" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#fff"/>
<stop offset="1" stop-color="#c7d2fe"/></linearGradient></defs>
<rect width="64" height="64" rx="18" fill="rgba(255,255,255,.16)" stroke="rgba(255,255,255,.38)"/>
<rect x="14" y="34" width="8" height="16" rx="3" fill="url(#lg)"/>
<rect x="28" y="25" width="8" height="25" rx="3" fill="url(#lg)"/>
<rect x="42" y="15" width="8" height="35" rx="3" fill="url(#lg)"/>
<path d="M14 27 28 18l14 4 10-12" stroke="#fde68a" stroke-width="3" fill="none"
 stroke-linecap="round" stroke-linejoin="round"/></svg>"""


def hero():
    badges = "".join(f'<span class="badge">{svg(i, 14)}{t}</span>' for i, t in [
        ("coins", "الجنيه السوداني SDG"), ("file", "كشف PDF من بنكك"),
        ("shield", "معالجة خاصة بلا حفظ")])
    return (f'<div class="hero"><div class="hero-top">{LOGO}<div>'
            f'<div class="hero-title">محلل كشف حساب بنكك</div>'
            f'<div class="hero-sub">حوّل كشف حسابك إلى صورة واضحة: الإرسال والاستلام، '
            f'الرسوم، وأكثر الأيام نشاطاً.</div></div></div>'
            f'<div class="badges">{badges}</div></div>')


def head(icon, title, sub=""):
    s = f'<div class="sec-sub">{sub}</div>' if sub else ""
    return (f'<div class="sec"><span class="chip">{svg(icon, 18)}</span>'
            f'<div><div class="sec-t">{title}</div>{s}</div></div>')


def kpis(items):
    """items: (icon, label, value, sub, tone)"""
    cards = "".join(
        f'<div class="kpi {tone}"><div class="kpi-top"><span class="kchip">{svg(icon, 18)}</span>'
        f'<span class="kl">{label}</span></div><div class="kv">{value}</div>'
        f'<div class="ks">{sub}</div></div>' for icon, label, value, sub, tone in items)
    return f'<div class="kpis">{cards}</div>'


def insights(notes):
    return "".join(f'<div class="insight"><span>{svg("trend", 16)}</span><div>{n}</div></div>'
                   for n in notes)


def table(df, escape=True):
    t = df.to_html(index=False, border=0, escape=escape).replace("\n", "")
    return f'<div class="tbl-wrap">{t}</div>'


def esc(s):
    return html.escape(str(s))


THEMES = {
    "dark": dict(bg="#0b1020", surface="#111827", surface2="#0f172a", border="rgba(255,255,255,.09)",
                 text="#e5e7eb", muted="#9ca3af", accent="#60a5fa", green="#34d399",
                 red="#f87171", amber="#fbbf24", chip="rgba(96,165,250,.14)",
                 shadow="0 8px 24px rgba(0,0,0,.28)"),
    "light": dict(bg="#f4f6fb", surface="#ffffff", surface2="#f8fafc", border="rgba(15,23,42,.09)",
                  text="#0f172a", muted="#64748b", accent="#3b82f6", green="#059669",
                  red="#dc2626", amber="#d97706", chip="rgba(59,130,246,.12)",
                  shadow="0 8px 24px rgba(15,23,42,.07)"),
}

STATIC_CSS = """
@import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;700;800&display=swap');
html, body, .stApp { font-family: 'Cairo', sans-serif; }
.stApp :is(p, label, li, summary, td, th, button, input, textarea, div):not([data-testid="stIconMaterial"]) { font-family: 'Cairo', sans-serif; }
[data-testid="stIconMaterial"], span[class*="material"] { font-family: 'Material Symbols Rounded', 'Material Icons' !important; }
.stApp { background: var(--bg); color: var(--text); }
[data-testid="stHeader"] { background: transparent; }
.block-container { direction: rtl; max-width: 1180px; padding: 4.6rem 1rem 4rem; }
@media (min-width: 900px) { .block-container { padding-top: 4rem; } }
.stApp p, .stApp label, .stApp span, .stApp li, .stApp summary { color: var(--text); }
.stCaption, [data-testid="stCaptionContainer"] { color: var(--muted) !important; }
.stPlotlyChart { direction: ltr; }
svg { flex: none; }

/* hero */
.hero { position: relative; overflow: hidden; border-radius: 24px; color: #fff;
  padding: clamp(18px, 4.5vw, 34px); margin: 4px 0 18px;
  background: linear-gradient(135deg, #1e3a8a 0%, #6d28d9 55%, #be185d 100%);
  box-shadow: 0 14px 40px rgba(109, 40, 217, .28); }
.hero:before { content: ""; position: absolute; width: 340px; height: 340px; top: -150px; left: -90px;
  background: radial-gradient(circle, rgba(255,255,255,.24), transparent 65%); }
.hero:after { content: ""; position: absolute; width: 260px; height: 260px; bottom: -130px; right: -60px;
  background: radial-gradient(circle, rgba(253,230,138,.22), transparent 65%); }
.hero-top { position: relative; z-index: 1; display: flex; align-items: center; gap: 14px; }
.logo { width: clamp(46px, 12vw, 66px); height: clamp(46px, 12vw, 66px); flex: none; }
.hero-title { font-size: clamp(1.35rem, 5.4vw, 2.2rem); font-weight: 800; line-height: 1.2; color: #fff !important; }
.hero-sub { margin-top: 6px; font-size: clamp(.82rem, 3.1vw, 1rem); line-height: 1.7;
  color: rgba(255,255,255,.88) !important; max-width: 62ch; }
.badges { position: relative; z-index: 1; display: flex; flex-wrap: wrap; gap: 8px; margin-top: 16px; }
.badge { display: inline-flex; align-items: center; gap: 6px; padding: 5px 12px; border-radius: 999px;
  font-size: .76rem; font-weight: 600; color: #fff !important; background: rgba(255,255,255,.14);
  border: 1px solid rgba(255,255,255,.28); backdrop-filter: blur(6px); }
.badge svg { stroke: #fff; }

/* KPI */
.kpis { display: grid; grid-template-columns: repeat(auto-fit, minmax(155px, 1fr)); gap: 12px; margin: 12px 0 6px; }
.kpi { background: var(--surface); border: 1px solid var(--border); border-radius: 18px;
  padding: 14px 16px; box-shadow: var(--shadow); }
.kpi-top { display: flex; align-items: center; gap: 8px; }
.kchip { display: inline-flex; width: 32px; height: 32px; border-radius: 10px; align-items: center;
  justify-content: center; background: var(--chip); }
.kl { color: var(--muted); font-size: .85rem; font-weight: 600; }
.kv { font-size: clamp(1.25rem, 5.2vw, 1.75rem); font-weight: 800; margin-top: 8px; line-height: 1.2; direction: ltr; text-align: right; }
.ks { color: var(--muted); font-size: .76rem; margin-top: 2px; }
.kpi.green .kv, .kpi.green .kchip { color: var(--green); }
.kpi.red .kv, .kpi.red .kchip { color: var(--red); }
.kpi.amber .kv, .kpi.amber .kchip { color: var(--amber); }
.kpi.blue .kv, .kpi.blue .kchip { color: var(--accent); }
.kpi.green .kchip { background: color-mix(in srgb, var(--green) 15%, transparent); }
.kpi.red .kchip { background: color-mix(in srgb, var(--red) 15%, transparent); }
.kpi.amber .kchip { background: color-mix(in srgb, var(--amber) 15%, transparent); }

/* section headers, insights */
.sec { display: flex; align-items: center; gap: 10px; margin: 2px 0 6px; }
.chip { display: inline-flex; width: 34px; height: 34px; border-radius: 11px; align-items: center;
  justify-content: center; background: var(--chip); color: var(--accent); }
.sec-t { font-weight: 700; font-size: 1.02rem; color: var(--text); }
.sec-sub { color: var(--muted); font-size: .78rem; }
.insight { display: flex; gap: 10px; align-items: flex-start; background: var(--surface);
  border: 1px solid var(--border); border-right: 4px solid var(--accent); border-radius: 12px;
  padding: 10px 14px; margin: 8px 0; font-size: .93rem; line-height: 1.7; }
.insight svg { stroke: var(--accent); margin-top: 4px; }
.meta { display: flex; flex-wrap: wrap; gap: 8px; margin: 4px 0 8px; }
.meta span { display: inline-flex; align-items: center; gap: 6px; background: var(--surface);
  border: 1px solid var(--border); border-radius: 999px; padding: 4px 12px; font-size: .78rem; color: var(--muted); }

/* tables */
.tbl-wrap { overflow-x: auto; border: 1px solid var(--border); border-radius: 14px; background: var(--surface); }
.tbl-wrap table { width: 100%; border-collapse: collapse; font-size: .85rem; }
.tbl-wrap th { background: var(--surface2); color: var(--muted); font-weight: 600; text-align: right;
  padding: 9px 12px; white-space: nowrap; }
.tbl-wrap td { padding: 8px 12px; border-top: 1px solid var(--border); color: var(--text); white-space: nowrap; text-align: right; }
.pill { padding: 2px 10px; border-radius: 999px; font-size: .75rem; font-weight: 700; }
.pill.in { background: color-mix(in srgb, var(--green) 16%, transparent); color: var(--green); }
.pill.out { background: color-mix(in srgb, var(--red) 16%, transparent); color: var(--red); }

/* Streamlit widgets */
[data-testid="stVerticalBlockBorderWrapper"]:has(> div > [data-testid="stVerticalBlock"] .sec) {
  background: var(--surface); border: 1px solid var(--border) !important; border-radius: 18px; box-shadow: var(--shadow); }
[data-testid="stFileUploaderDropzone"], [data-testid="stFileUploaderFile"] { background: var(--surface) !important;
  border: 1px dashed var(--border); border-radius: 16px; }
[data-testid="stFileUploaderDropzone"] *, [data-testid="stFileUploaderFile"] * { color: var(--text) !important; }
[data-testid="stExpander"] details { background: var(--surface); border: 1px solid var(--border) !important; border-radius: 14px; }
[data-baseweb="select"] > div, [data-baseweb="input"], [data-baseweb="base-input"], .stDateInput input {
  background: var(--surface2) !important; color: var(--text) !important; border-color: var(--border) !important; }
button[data-baseweb="tab"] { color: var(--muted) !important; font-weight: 600; padding: 8px 14px; }
button[data-baseweb="tab"][aria-selected="true"] { color: var(--accent) !important; }
[data-baseweb="tab-list"] { gap: 2px; border-bottom: 1px solid var(--border); overflow-x: auto; }
[data-baseweb="tab-highlight"] { background: var(--accent) !important; }
.stButton button, .stDownloadButton button, [data-testid="stBaseButton-secondary"] {
  background: var(--surface) !important; color: var(--text) !important; border: 1px solid var(--border) !important;
  border-radius: 12px; font-weight: 600; }
[data-testid="stAlert"] { border-radius: 14px; }
"""


def css(mode):
    t = THEMES[mode]
    vars_ = ";".join(f"--{k}:{v}" for k, v in t.items())
    return f"<style>:root{{{vars_}}}{STATIC_CSS}</style>"
