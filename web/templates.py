import hashlib
from pathlib import Path

from fastapi.templating import Jinja2Templates

templates = Jinja2Templates(directory="web/templates")

_APP_CSS = Path(__file__).parent / "static" / "app.css"


def _static_version() -> str:
    """Short content hash of the built stylesheet, used to bust browser caches."""
    try:
        return hashlib.sha256(_APP_CSS.read_bytes()).hexdigest()[:10]
    except OSError:
        return "dev"


templates.env.globals["static_version"] = _static_version()

