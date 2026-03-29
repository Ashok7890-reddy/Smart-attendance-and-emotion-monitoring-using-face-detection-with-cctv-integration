"""
Main FastAPI application for Smart Attendance System.
"""

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer
import logging
from contextlib import asynccontextmanager

from ..core.config import Config
from .routers import attendance, students, sessions, auth, face_recognition
from .middleware import AuthMiddleware, RateLimitMiddleware
from .dependencies import get_config, get_database_manager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Security
security = HTTPBearer()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    logger.info("Starting Smart Attendance System API")
    
    # Initialize configuration
    config = get_config()
    logger.info(f"Running in {config.ENV} environment")
    
    # Initialize WebSocket integration (if available)
    try:
        from .websocket import connection_manager
        from ..services.websocket_integration_service import get_websocket_integration
        websocket_integration = get_websocket_integration()
        websocket_integration.set_connection_manager(connection_manager)
        logger.info("WebSocket integration initialized")
    except Exception as e:
        logger.warning(f"WebSocket integration not available: {e}")
    
    yield
    
    # Cleanup
    logger.info("Shutting down Smart Attendance System API")


def create_app() -> FastAPI:
    """Create and configure FastAPI application."""
    config = get_config()
    
    app = FastAPI(
        title="Smart Attendance System API",
        description="AI-powered attendance tracking with facial recognition and emotion analysis",
        version="1.0.0",
        docs_url="/api/v1/docs",
        redoc_url="/api/v1/redoc",
        openapi_url="/api/v1/openapi.json",
        lifespan=lifespan
    )
    
    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"] if config.is_development() else ["http://localhost:3000"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Custom middleware
    app.add_middleware(AuthMiddleware)
    app.add_middleware(RateLimitMiddleware)
    
    # Include routers
    app.include_router(auth.router, prefix="/api/v1/auth", tags=["Authentication"])
    app.include_router(students.router, prefix="/api/v1/students", tags=["Students"])
    app.include_router(sessions.router, prefix="/api/v1/sessions", tags=["Sessions"])
    app.include_router(attendance.router, prefix="/api/v1/attendance", tags=["Attendance"])
    app.include_router(face_recognition.router, prefix="/api/v1/face-recognition", tags=["Face Recognition"])
    
    # DeepFace emotion analysis (Facenet512 + retinaface)
    try:
        from .routers.deepface_emotion import router as deepface_router
        app.include_router(deepface_router, tags=["DeepFace Emotion"])
        logger.info("✅ DeepFace emotion analysis enabled (Facenet512 + retinaface)")
    except Exception as e:
        logger.warning(f"⚠️ DeepFace not available, falling back to face-api.js: {e}")
    
    # Include WebSocket router
    from .websocket import websocket_router
    app.include_router(websocket_router, prefix="/api/v1", tags=["WebSocket"])
    
    @app.get("/api/v1/health")
    async def health_check():
        """Health check endpoint."""
        return {
            "status": "healthy",
            "service": "Smart Attendance System API",
            "version": "1.0.0"
        }
    
    @app.get("/")
    async def root():
        """Root endpoint - serves frontend in production."""
        return {
            "message": "Smart Attendance System API",
            "docs": "/api/v1/docs"
        }
    
    # Serve frontend static files in production
    import os
    from pathlib import Path
    from fastapi.staticfiles import StaticFiles
    from fastapi.responses import FileResponse
    
    frontend_dist = Path(__file__).parent.parent.parent / "frontend" / "dist"
    
    if frontend_dist.exists() and os.getenv("ENVIRONMENT") == "production":
        logger.info(f"Serving frontend from {frontend_dist}")
        
        # Serve static assets
        app.mount("/assets", StaticFiles(directory=str(frontend_dist / "assets")), name="assets")
        
        # Catch-all route for SPA - must be last
        @app.get("/{full_path:path}")
        async def serve_spa(full_path: str):
            """Serve React SPA for all non-API routes."""
            if full_path.startswith("api/"):
                raise HTTPException(status_code=404, detail="API endpoint not found")
            
            index_file = frontend_dist / "index.html"
            if index_file.exists():
                return FileResponse(index_file)
            raise HTTPException(status_code=404, detail="Frontend not built")
    
    return app


# Create app instance
app = create_app()