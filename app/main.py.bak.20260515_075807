from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.api import public, places
from app.core.config import settings

app = FastAPI(
    title="Jyotish AI",
    description="Vedic Astrology App with AI-powered insights",
    version="2.0.0",
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
)

origins = [o.strip() for o in settings.ALLOWED_ORIGINS.split(",")]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)

app.mount("/static", StaticFiles(directory="static"), name="static")

app.include_router(public.router, prefix="/api")

from app.services.features.today_deep import today_deep_router
from app.services.features.chart_overview import chart_overview_router
from app.services.features.compatibility_deep import compatibility_deep_router
from app.services.features.core_chart import core_chart_router
from app.services.features.media_manifest import media_manifest_router
app.include_router(media_manifest_router, prefix="/api")
app.include_router(core_chart_router, prefix="/api")
app.include_router(compatibility_deep_router, prefix="/api")
app.include_router(chart_overview_router, prefix="/api")
from app.services.features.compatibility_deep import compatibility_deep_router
from app.services.features.core_chart import core_chart_router
from app.services.features.media_manifest import media_manifest_router
app.include_router(media_manifest_router, prefix="/api")
app.include_router(core_chart_router, prefix="/api")
app.include_router(compatibility_deep_router, prefix="/api")
app.include_router(today_deep_router, prefix="/api")
from app.services.features.chart_overview import chart_overview_router
from app.services.features.compatibility_deep import compatibility_deep_router
from app.services.features.core_chart import core_chart_router
from app.services.features.media_manifest import media_manifest_router
app.include_router(media_manifest_router, prefix="/api")
app.include_router(core_chart_router, prefix="/api")
app.include_router(compatibility_deep_router, prefix="/api")
app.include_router(chart_overview_router, prefix="/api")
from app.services.features.compatibility_deep import compatibility_deep_router
from app.services.features.core_chart import core_chart_router
from app.services.features.media_manifest import media_manifest_router
app.include_router(media_manifest_router, prefix="/api")
app.include_router(core_chart_router, prefix="/api")
app.include_router(compatibility_deep_router, prefix="/api")
app.include_router(places.router, prefix="/api")


@app.get("/")
def root():
    return {"status": "ok", "message": "Jyotish AI Backend is running"}


@app.get("/health")
def health():
    return {"status": "healthy"}
