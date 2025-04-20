from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from app.api.v1.routes import router as api_router
from app.db.mongodb import MongoDB
from app.core.config import settings
import os

app = FastAPI(
    title=settings.PROJECT_NAME,
    description=settings.PROJECT_DESCRIPTION,
    version=settings.PROJECT_VERSION,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For production, specify the actual frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(api_router, prefix="/api/v1")

# Initialize MongoDB connection
@app.on_event("startup")
async def startup_db_client():
    try:
        await MongoDB.connect(os.environ.get("MONGODB_URI"))
    except Exception as e:
        print(f"Failed to connect to MongoDB: {e}")

@app.on_event("shutdown")
async def shutdown_db_client():
    try:
        await MongoDB.close()
    except Exception as e:
        print(f"Error closing MongoDB connection: {e}")

# Root endpoint for health check
@app.get("/")
async def root():
    return {
        "message": "SmartFin AI API is running",
        "docs": "/docs",
        "version": settings.PROJECT_VERSION
    }