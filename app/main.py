from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
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

app.include_router(public.router, prefix="/api")
app.include_router(places.router, prefix="/api")


@app.get("/")
def root():
    return {"status": "ok", "message": "Jyotish AI Backend is running"}


@app.get("/health")
def health():
    return {"status": "healthy"}
