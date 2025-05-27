"""
Main FastAPI Application
========================

Entry point untuk aplikasi KTP Detection
"""

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from decouple import config
import os

from app.api.endpoints import router

# Create FastAPI app
app = FastAPI(
    title="KTP Detection API",
    description="API untuk deteksi dan verifikasi KTP Indonesia menggunakan AI",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create directories if they don't exist
os.makedirs("static", exist_ok=True)
os.makedirs("uploads", exist_ok=True)
os.makedirs("templates", exist_ok=True)
os.makedirs("face_images", exist_ok=True)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/face_images", StaticFiles(directory="face_images"), name="face_images")

# Setup templates
templates = Jinja2Templates(directory="templates")

# Include API routes
app.include_router(router, prefix="/api", tags=["KTP Detection"])

@app.get("/")
async def root(request: Request):
    """Homepage dengan form upload KTP"""
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "KTP Detection API",
        "version": "1.0.0"
    }

if __name__ == "__main__":
    import uvicorn
    
    host = config("HOST", default="0.0.0.0")
    port = config("PORT", default=8000, cast=int)
    debug = config("DEBUG", default=True, cast=bool)
    
    uvicorn.run(
        "app.main:app",
        host=host,
        port=port,
        reload=debug
    )
