import sqlite3
from contextlib import asynccontextmanager

import requests
from dotenv import load_dotenv

load_dotenv()
from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse

from db.connection import get_db, init_db
from web.middleware.session import RequiresLogin
from web.routes.auth import router as auth_router
from web.routes.health import router as health_router
from web.routes.home import router as home_router
from web.routes.overview import router as overview_router
from web.routes.waiver import public_router as waiver_public_router
from web.routes.waiver import router as waiver_router
from web.templates import templates


@asynccontextmanager
async def lifespan(app: FastAPI):
    conn = get_db()
    try:
        init_db(conn)
        try:
            conn.execute("ALTER TABLE user_sessions ADD COLUMN league_key TEXT")
            conn.commit()
        except sqlite3.OperationalError:
            pass  # column already exists
    finally:
        conn.close()
    yield


app = FastAPI(lifespan=lifespan)


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
app.include_router(home_router)
app.include_router(overview_router)
app.include_router(waiver_public_router)
app.include_router(waiver_router)
