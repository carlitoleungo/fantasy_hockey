import requests
from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse

from web.middleware.session import RequiresLogin
from web.routes.auth import router as auth_router
from web.routes.health import router as health_router
from web.templates import templates

app = FastAPI()


@app.exception_handler(RequiresLogin)
def requires_login_handler(request: Request, exc: RequiresLogin) -> RedirectResponse:
    return RedirectResponse("/auth/login", status_code=302)


@app.exception_handler(requests.HTTPError)
def http_error_handler(request: Request, exc: requests.HTTPError):
    return templates.TemplateResponse(
        request,
        "error.html",
        {"detail": "Yahoo API request failed. Please try again."},
        status_code=502,
    )


@app.exception_handler(500)
def internal_error_handler(request: Request, exc: Exception):
    return templates.TemplateResponse(
        request,
        "error.html",
        {"detail": "Something went wrong."},
        status_code=500,
    )


app.include_router(health_router)
app.include_router(auth_router)
