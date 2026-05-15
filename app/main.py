from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api import public, places
from app.core.config import settings

from app.services.features.chart_overview import chart_overview_router
from app.services.features.compatibility_deep import compatibility_deep_router
from app.services.features.core_chart import core_chart_router
from app.services.features.media_manifest import media_manifest_router
from app.services.features.blunt_seer import blunt_seer_router
from app.services.features.business_name import business_name_router
from app.services.features.core_numbers import core_numbers_router
from app.services.features.mobile_number import mobile_number_router
from app.services.features.five_elements import five_elements_router
from app.services.features.four_pillars import four_pillars_router
from app.services.features.name_correction import name_correction_router
from app.services.features.the_zoo import the_zoo_router
from app.services.features.the_word import the_word_router
from app.services.features.time_reading import time_reading_router
from app.services.features.today_sky import today_sky_router
from app.services.features.kp_horary_feature import kp_horary_router
from app.services.features.life_story import life_story_router
from app.services.features.chat import chat_router
from app.services.features.strings import strings_router
from app.services.features.catalog import catalog_router
from app.services.features.match import match_router
from app.services.features.panchanga import panchanga_router
from app.services.features.past_life import past_life_router
from app.services.features.today_deep import today_deep_router


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

# Core API
app.include_router(public.router, prefix="/api")
app.include_router(places.router, prefix="/api")

# Feature routers
app.include_router(media_manifest_router, prefix="/api")
app.include_router(core_chart_router, prefix="/api")
app.include_router(chart_overview_router, prefix="/api")
app.include_router(today_deep_router, prefix="/api")
app.include_router(compatibility_deep_router, prefix="/api")
app.include_router(past_life_router, prefix="/api")
app.include_router(business_name_router, prefix="/api")
app.include_router(core_numbers_router, prefix="/api")
app.include_router(mobile_number_router, prefix="/api")
app.include_router(name_correction_router, prefix="/api")
app.include_router(blunt_seer_router, prefix="/api")
app.include_router(five_elements_router, prefix="/api")
app.include_router(four_pillars_router, prefix="/api")
app.include_router(the_zoo_router, prefix="/api")
app.include_router(the_word_router, prefix="/api")
app.include_router(time_reading_router, prefix="/api")
app.include_router(today_sky_router, prefix="/api")
app.include_router(kp_horary_router, prefix="/api")
app.include_router(life_story_router, prefix="/api")
app.include_router(chat_router, prefix="/api")
app.include_router(strings_router, prefix="/api")
app.include_router(catalog_router, prefix="/api")
app.include_router(match_router, prefix="/api")
app.include_router(panchanga_router, prefix="/api")


@app.get("/")
def root():
    return {"status": "ok", "message": "Jyotish AI Backend is running"}


@app.get("/health")
def health():
    return {"status": "healthy"}
