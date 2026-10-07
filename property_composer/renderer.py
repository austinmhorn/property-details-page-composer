from __future__ import annotations

from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from .config import OUTPUT_DIR, TEMPLATE_DIR, ensure_runtime_dirs
from .property_data import Property


def _environment() -> Environment:
    return Environment(
        loader=FileSystemLoader(TEMPLATE_DIR),
        autoescape=select_autoescape(default_for_string=True, default=True),
        trim_blocks=True,
        lstrip_blocks=True,
    )


def render_portfolio(
    properties: list[Property],
    *,
    selected_key: str | None = None,
    page_title: str = "Property Details",
) -> str:
    if not properties:
        raise ValueError("Cannot render a portfolio page with no properties")

    selected_key = selected_key or properties[0].key
    template = _environment().get_template("portfolio_details.html")
    return template.render(
        properties=properties,
        selected_key=selected_key,
        page_title=page_title,
    )


def write_preview(html: str, filename: str = "portfolio_details.html") -> Path:
    ensure_runtime_dirs()
    output_path = OUTPUT_DIR / filename
    output_path.write_text(html, encoding="utf-8")
    return output_path
