"""Design tokens and the one stylesheet for the dashboard.

Colours are also set in `.streamlit/config.toml` [theme], so native Streamlit widgets match these tokens. The CSS below
styles only our own `sl-` classes, plus the app font; it never reaches into Streamlit's internal DOM structure.
"""
from __future__ import annotations

TOKENS = {
    "bg": "#0E1621",          # application shell: deep graphite navy
    "surface": "#152131",     # panels and cards
    "raised": "#1C2B3E",      # hover and nested surfaces
    "border": "#26374C",
    "text": "#E6EDF5",
    "muted": "#91A3B8",
    "faint": "#5F738A",
    "teal": "#2CC7B4",        # healthy states, primary actions
    "amber": "#E8A33D",       # warnings, pending review
    "orange": "#EE7B3E",      # high severity
    "red": "#E5484D",         # urgent, critical
    "steel": "#7A9CC6",       # watch: informational
    "radius": "10px",
    "radius_sm": "6px",
}

# Severity order and presentation. The labels are the rule table's own severities (agent.SEVERITY_ORDER); each carries
# a text label and a glyph so status never depends on colour alone.
SEVERITY = {
    "CRITICAL": {"label": "Critical", "color": TOKENS["red"], "glyph": "▲"},
    "HIGH": {"label": "High", "color": TOKENS["orange"], "glyph": "▲"},
    "MEDIUM": {"label": "Medium", "color": TOKENS["amber"], "glyph": "◆"},
    "WATCH": {"label": "Watch", "color": TOKENS["steel"], "glyph": "●"},
    "NONE": {"label": "Healthy", "color": TOKENS["teal"], "glyph": "●"},
}
SEVERITY_RANK = {"NONE": 0, "WATCH": 1, "MEDIUM": 2, "HIGH": 3, "CRITICAL": 4}

FONT = "'IBM Plex Sans', -apple-system, 'Segoe UI', Roboto, sans-serif"

CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600;700&display=swap');
/* the one rule on a Streamlit test id: trim the default top padding of the main column (harmless if the id changes) */
[data-testid="stMainBlockContainer"] {{ padding-top: 2.25rem; }}
.sl-header {{ margin: 0 0 1.25rem 0; }}
.sl-header h1 {{ font-family: {FONT}; font-size: 1.75rem; font-weight: 600; letter-spacing: -0.01em; margin: 0 0 .35rem 0;
  color: {TOKENS['text']}; line-height: 1.2; }}
.sl-header p {{ color: {TOKENS['muted']}; margin: 0; max-width: 72ch; font-size: .95rem; line-height: 1.5; }}
.sl-pill {{ display: inline-block; font-size: .78rem; font-weight: 500; padding: .15rem .55rem; border-radius: 999px;
  border: 1px solid {TOKENS['border']}; color: {TOKENS['muted']}; margin: .6rem .4rem 0 0; white-space: nowrap; }}
.sl-kpis {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: .75rem; margin: .25rem 0 .5rem; }}
.sl-kpi {{ background: {TOKENS['surface']}; border: 1px solid {TOKENS['border']}; border-radius: {TOKENS['radius']};
  padding: .9rem 1rem .85rem; height: 100%; min-height: 118px; }}
.sl-kpi .label {{ color: {TOKENS['muted']}; font-size: .82rem; font-weight: 500; margin-bottom: .35rem; }}
.sl-kpi .value {{ color: {TOKENS['text']}; font-size: 1.6rem; font-weight: 600; font-variant-numeric: tabular-nums;
  line-height: 1.15; overflow-wrap: anywhere; }}
.sl-kpi .unit {{ color: {TOKENS['muted']}; font-size: .9rem; font-weight: 500; margin-left: .2rem; }}
.sl-kpi .note {{ color: {TOKENS['faint']}; font-size: .78rem; margin-top: .4rem; line-height: 1.35; }}
.sl-kpi.accent-red {{ border-left: 3px solid {TOKENS['red']}; }}
.sl-kpi.accent-amber {{ border-left: 3px solid {TOKENS['amber']}; }}
.sl-kpi.accent-teal {{ border-left: 3px solid {TOKENS['teal']}; }}
.sl-badge {{ display: inline-flex; align-items: center; gap: .3rem; font-size: .8rem; font-weight: 600;
  padding: .12rem .5rem; border-radius: {TOKENS['radius_sm']}; white-space: nowrap; }}
.sl-section {{ margin: 1.6rem 0 .6rem 0; }}
.sl-section h3 {{ font-family: {FONT}; font-size: 1.05rem; font-weight: 600; color: {TOKENS['text']}; margin: 0 0 .2rem 0; }}
.sl-section p {{ color: {TOKENS['muted']}; font-size: .88rem; margin: 0; max-width: 78ch; line-height: 1.45; }}
.sl-alert {{ border: 1px solid {TOKENS['border']}; border-left-width: 3px; border-radius: {TOKENS['radius_sm']};
  background: {TOKENS['surface']}; padding: .7rem .9rem; margin: .4rem 0; color: {TOKENS['text']}; font-size: .9rem; line-height: 1.45; }}
.sl-alert strong {{ font-weight: 600; }}
.sl-alert .sub {{ color: {TOKENS['muted']}; font-size: .84rem; display: block; margin-top: .15rem; }}
.sl-empty {{ border: 1px dashed {TOKENS['border']}; border-radius: {TOKENS['radius']}; padding: 1.4rem 1.2rem;
  color: {TOKENS['muted']}; text-align: left; font-size: .92rem; }}
.sl-empty strong {{ color: {TOKENS['text']}; display: block; margin-bottom: .2rem; }}
.sl-kv {{ display: grid; grid-template-columns: minmax(9rem, max-content) 1fr; gap: .35rem 1rem; font-size: .9rem; }}
.sl-kv dt {{ color: {TOKENS['muted']}; }}
.sl-kv dd {{ margin: 0; color: {TOKENS['text']}; font-variant-numeric: tabular-nums; overflow-wrap: anywhere; }}
.sl-reason {{ margin: .15rem 0; color: {TOKENS['text']}; font-size: .9rem; }}
.sl-reason .rid {{ color: {TOKENS['faint']}; font-size: .78rem; margin-left: .35rem; }}
.sl-brand {{ font-family: {FONT}; font-weight: 600; font-size: 1.05rem; color: {TOKENS['text']}; }}
.sl-foot {{ color: {TOKENS['faint']}; font-size: .76rem; line-height: 1.45; margin-top: .5rem; }}
@media (max-width: 640px) {{
  .sl-header h1 {{ font-size: 1.4rem; }}
  .sl-kpi {{ min-height: 0; }}
  .sl-kpi .value {{ font-size: 1.35rem; }}
  .sl-kv {{ grid-template-columns: 1fr; gap: .1rem; }}
  .sl-kv dd {{ margin-bottom: .45rem; }}
}}
</style>
"""


def plotly_layout(height: int = 320, **overrides) -> dict:
    """Shared Plotly layout: transparent background, theme text colours, quiet grid, readable hover labels."""
    layout = dict(
        height=height, margin=dict(l=8, r=8, t=12, b=8), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family=FONT, color=TOKENS["muted"], size=12),
        xaxis=dict(gridcolor=TOKENS["border"], zerolinecolor=TOKENS["border"], linecolor=TOKENS["border"], title_font=dict(size=12)),
        yaxis=dict(gridcolor=TOKENS["border"], zerolinecolor=TOKENS["border"], linecolor=TOKENS["border"], title_font=dict(size=12)),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0, font=dict(size=12)),
        hoverlabel=dict(bgcolor=TOKENS["raised"], bordercolor=TOKENS["border"], font=dict(family=FONT, color=TOKENS["text"])),
    )
    layout.update(overrides)
    return layout
