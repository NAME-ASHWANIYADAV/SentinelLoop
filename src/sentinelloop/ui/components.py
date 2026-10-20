"""Small Streamlit rendering components built on the design tokens. All dynamic text is HTML-escaped."""
from __future__ import annotations

import html

import streamlit as st

from .format import fmt_num
from .theme import CSS, SEVERITY, TOKENS


def inject_css() -> None:
    st.markdown(CSS, unsafe_allow_html=True)


def _e(s) -> str:
    return html.escape("" if s is None else str(s))


def page_header(title: str, description: str, pills: list[str] | None = None) -> None:
    p = "".join(f'<span class="sl-pill">{_e(x)}</span>' for x in (pills or []))
    st.markdown(f'<div class="sl-header"><h1>{_e(title)}</h1><p>{_e(description)}</p>{p}</div>', unsafe_allow_html=True)


def section(title: str, description: str = "") -> None:
    d = f"<p>{_e(description)}</p>" if description else ""
    st.markdown(f'<div class="sl-section"><h3>{_e(title)}</h3>{d}</div>', unsafe_allow_html=True)


def badge_html(text: str, color: str, glyph: str = "") -> str:
    g = f"<span aria-hidden='true'>{_e(glyph)}</span>" if glyph else ""
    return (f'<span class="sl-badge" style="color:{color};background:{color}22;border:1px solid {color}55">{g}{_e(text)}</span>')


def severity_badge(sev: str) -> str:
    m = SEVERITY.get(str(sev), {"label": str(sev), "color": TOKENS["muted"], "glyph": ""})
    return badge_html(m["label"], m["color"], m["glyph"])


def status_badge(ok: bool | None, yes: str, no: str, unknown: str = "Not checked") -> str:
    if ok is None:
        return badge_html(unknown, TOKENS["muted"], "○")
    return badge_html(yes, TOKENS["teal"], "✓") if ok else badge_html(no, TOKENS["red"], "✕")


def kpi_card(label: str, value, unit: str = "", note: str = "", digits: int = 2, accent: str = "", help: str = "") -> str:
    """HTML for one KPI card. `value` may be a number (formatted with `digits`) or a ready string."""
    v = value if isinstance(value, str) else fmt_num(value, digits)
    u = f'<span class="unit">{_e(unit)}</span>' if unit and v != "–" else ""
    n = f'<div class="note">{_e(note)}</div>' if note else ""
    t = f' title="{_e(help)}"' if help else ""
    cls = f"sl-kpi accent-{accent}" if accent else "sl-kpi"
    return f'<div class="{cls}"{t}><div class="label">{_e(label)}</div><div class="value">{_e(v)}{u}</div>{n}</div>'


def kpi_row(cards: list[str]) -> None:
    """A row of KPI cards on a CSS grid that wraps onto new lines on narrow screens instead of squeezing the cards."""
    st.markdown(f'<div class="sl-kpis">{"".join(cards)}</div>', unsafe_allow_html=True)


def alert(kind: str, title: str, body: str = "") -> None:
    """kind: critical | warning | info | ok. The title states the fact; the body says what it means or what to do."""
    color = {"critical": TOKENS["red"], "warning": TOKENS["amber"], "info": TOKENS["steel"], "ok": TOKENS["teal"]}[kind]
    b = f'<span class="sub">{_e(body)}</span>' if body else ""
    st.markdown(f'<div class="sl-alert" style="border-left-color:{color}" role="status"><strong>{_e(title)}</strong>{b}</div>',
                unsafe_allow_html=True)


def empty_state(title: str, body: str) -> None:
    st.markdown(f'<div class="sl-empty"><strong>{_e(title)}</strong>{_e(body)}</div>', unsafe_allow_html=True)


def key_values(pairs: list[tuple[str, str]]) -> None:
    rows = "".join(f"<dt>{_e(k)}</dt><dd>{_e(v)}</dd>" for k, v in pairs)
    st.markdown(f'<dl class="sl-kv">{rows}</dl>', unsafe_allow_html=True)


def reasons(items: list[tuple[str, str]]) -> None:
    """Rule explanations with their rule ids, so an engineer can trace the sentence back to the rule table."""
    for rid, sentence in items:
        st.markdown(f'<div class="sl-reason">{_e(sentence)}<span class="rid">{_e(rid)}</span></div>', unsafe_allow_html=True)


def severity_style(series):
    """pandas Styler function: colour the Priority column text by severity (the text label carries the meaning too)."""
    out = []
    for v in series:
        color = next((m["color"] for m in SEVERITY.values() if str(v).endswith(m["label"])), TOKENS["text"])
        out.append(f"color: {color}; font-weight: 600")
    return out
