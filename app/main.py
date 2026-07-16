from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.core.config import settings
from app.routers import health, detect, detect_image

app = FastAPI(title=settings.APP_NAME)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(detect.router)
app.include_router(detect_image.router)

# Serve the frontend - index.html at "/", any other static assets alongside it
app.mount("/", StaticFiles(directory="app/static", html=True), name="static")
