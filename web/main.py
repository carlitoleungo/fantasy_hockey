from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse

from web.middleware.session import RequiresLogin
from web.routes.auth import router as auth_router
from web.routes.health import router as health_router

app = FastAPI()


@app.exception_handler(RequiresLogin)
def requires_login_handler(request: Request, exc: RequiresLogin) -> RedirectResponse:
    return RedirectResponse("/auth/login", status_code=302)


app.include_router(health_router)
app.include_router(auth_router)
