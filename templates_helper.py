import os
from jinja2 import Environment, FileSystemLoader
from fastapi.responses import HTMLResponse

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
_env = Environment(loader=FileSystemLoader(os.path.join(BASE_DIR, "templates")))


def render(name: str, context: dict) -> HTMLResponse:
    """Render a Jinja2 template and return an HTMLResponse."""
    template = _env.get_template(name)
    html = template.render(context)
    return HTMLResponse(content=html)
