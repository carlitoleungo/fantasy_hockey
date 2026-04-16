from fastapi import FastAPI

from web.routes.auth import router as auth_router
from web.routes.health import router as health_router

app = FastAPI()

app.include_router(health_router)
app.include_router(auth_router)
