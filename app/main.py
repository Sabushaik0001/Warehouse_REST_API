"""
Main FastAPI application entry point
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.routers import warehouse, camera, chat
import logging

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize FastAPI application
app = FastAPI(
    title=settings.APP_TITLE,
    version=settings.APP_VERSION,
    description="RESTful API for warehouse management with AI-powered video analytics"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(warehouse.router)
app.include_router(camera.router)
app.include_router(chat.router)


@app.get("/")
@app.get("/health")
def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "message": "Warehouse API is running",
        "version": settings.APP_VERSION,
        "endpoints": {
            "warehouses": "GET /api/v1/warehouses - Get all warehouses with employees",
            "warehouse_by_id": "GET /api/v1/warehouses/{warehouse_id} - Get specific warehouse details",
            "camera_stream": "GET /api/v1/cameras/stream-url - Get HLS streaming URL for camera",
            "chunks": "GET /api/v1/warehouses/{warehouse_id}/cameras/{cam_id}/chunks - Get video chunks",
            "employee_logs": "GET /api/v1/warehouses/{warehouse_id}/cameras/{cam_id}/logs/employees - Get employee logs",
            "gunny_logs": "GET /api/v1/warehouses/{warehouse_id}/cameras/{cam_id}/logs/gunny-bags - Get gunny bag logs",
            "vehicle_logs": "GET /api/v1/warehouses/{warehouse_id}/cameras/{cam_id}/logs/vehicles - Get vehicle logs",
            "dashboard": "GET /api/v1/warehouses/{warehouse_id}/dashboard - Get dashboard analytics",
            "vehicle_gunny_analytics": "GET /api/v1/warehouses/{warehouse_id}/cameras/{cam_id}/analytics/vehicle-gunny-count - Get vehicle-wise gunny count",
            "chat": "POST /api/v1/warehouses/{warehouse_id}/cameras/{cam_id}/chunks/{chunk_id}/chat - Chat with AI about video"
        }
    }


if __name__ == "__main__":
    import uvicorn
    
    logger.info(f"Starting {settings.APP_TITLE} v{settings.APP_VERSION}")
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8081,
        reload=True,
        log_level=settings.LOG_LEVEL.lower()
    )
