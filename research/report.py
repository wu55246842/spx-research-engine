from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from jinja2 import Environment, FileSystemLoader, select_autoescape


def render_markdown_report(data: Dict[str, Any], template_path: str) -> str:
    """Render a human-readable report (Markdown) from a Jinja template."""
    template_file = Path(template_path)
    env = Environment(
        loader=FileSystemLoader(str(template_file.parent)),
        autoescape=select_autoescape(default_for_string=False, enabled_extensions=()),
        trim_blocks=True,
        lstrip_blocks=True,
    )
    tmpl = env.get_template(template_file.name)
    return tmpl.render(**data)
