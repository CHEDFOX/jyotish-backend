from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.database import engine, Base
from app.api import auth, user, chat, matching, places, admin, public

# Create database tables
Base.metadata.create_all(bind=engine)

# Create FastAPI app
app = FastAPI(
    title="Jyotish AI",
    description="Vedic Astrology App with AI-powered insights",
    version="1.0.0"
)

# CORS middleware (allow mobile app to connect)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(public.router, prefix="/api")  # Public endpoints (no auth)
app.include_router(auth.router, prefix="/api")
app.include_router(user.router, prefix="/api")
app.include_router(chat.router, prefix="/api")
app.include_router(matching.router, prefix="/api")
app.include_router(places.router, prefix="/api")
app.include_router(admin.router, prefix="/api")

# Health check
@app.get("/")
def root():
    return {"status": "ok", "message": "Jyotish AI Backend is running"}

@app.get("/health")
def health():
    return {"status": "healthy"}
