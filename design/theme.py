from __future__ import annotations

import streamlit as st

from design.modern_css import LIQUID_GLASS_ULTRA_CSS


def apply_liquid_glass_theme() -> None:
    st.markdown(LIQUID_GLASS_ULTRA_CSS, unsafe_allow_html=True)


def render_page_header(title: str, subtitle: str = "", eyebrow: str = "Monitoring") -> None:
    st.markdown(
        f"""
        <section class="lg-page-header">
            <div class="lg-page-title-wrap">
                <span class="lg-page-dot"></span>
                <h1 class="lg-page-title">{title}</h1>
            </div>
        </section>
        """,
        unsafe_allow_html=True,
    )


def render_callout(message: str) -> None:
    st.markdown(f'<div class="lg-callout">{message}</div>', unsafe_allow_html=True)


def render_section_title(title: str) -> None:
    st.markdown(f'<div class="lg-section-title">{title}</div>', unsafe_allow_html=True)


def open_panel() -> None:
    return None


def close_panel() -> None:
    return None
