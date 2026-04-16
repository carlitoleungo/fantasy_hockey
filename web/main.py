from fastapi import FastAPI

from web.routes.health import router as health_router

app = FastAPI()

app.include_router(health_router)
