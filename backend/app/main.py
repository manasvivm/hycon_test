# backend/app/main.py
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from .database import create_tables, engine, check_connection_pool_health
from .routes import auth, equipment, sessions, analytics, samples
import logging
import time
import os
from dotenv import load_dotenv

load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create FastAPI app with optimizations
app = FastAPI(
    title="HyCON Labs Equipment Management System",
    description="Digital equipment usage tracking and analytics system",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    # Enable response compression
    compress_response=True
)

# Add GZip compression middleware for better performance
app.add_middleware(GZipMiddleware, minimum_size=1000)

# Configure CORS - Get frontend URL from environment variable
frontend_url = os.getenv("FRONTEND_URL", "http://localhost:5173")
allowed_origins = [
    frontend_url,
    "http://localhost:5173",
    "http://localhost:3000",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:3000"
]

# Configure CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"]
)

# Request timing middleware for monitoring
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    
    # Log slow requests
    if process_time > 1.0:  # More than 1 second
        logger.warning(
            f"Slow request: {request.method} {request.url.path} "
            f"took {process_time:.2f}s"
        )
    
    return response

# Create database tables on startup and setup scheduler
from apscheduler.schedulers.background import BackgroundScheduler
from .session_scheduler import check_and_end_expired_sessions
from .database import SessionLocal

scheduler = BackgroundScheduler()

@app.on_event("startup")
async def startup_event():
    """Initialize database and background tasks"""
    logger.info("Starting HyCON Equipment Management System...")
    
    # Create database tables
    create_tables()
    logger.info("Database tables initialized")
    
    # Start background scheduler for session management
    scheduler.add_job(
        lambda: check_and_end_expired_sessions(SessionLocal()),
        'interval',
        minutes=1,
        id='check_expired_sessions',
        replace_existing=True
    )
    scheduler.start()
    logger.info("Background scheduler started")

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on application shutdown"""
    logger.info("Shutting down application...")
    scheduler.shutdown()
    logger.info("Scheduler stopped")

# Include routers
app.include_router(auth.router)
app.include_router(equipment.router)
app.include_router(sessions.router)
app.include_router(analytics.router)
app.include_router(samples.router)

# Root endpoint
@app.get("/")
async def read_root():
    return {
        "message": "HyCON Labs Equipment Management System API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health"
    }

# Health check endpoint with database connection pool status
@app.get("/health")
async def health_check():
    """
    Health check endpoint with database pool status.
    Returns detailed health information for monitoring.
    """
    try:
        # Check database connection
        from sqlalchemy import text
        with SessionLocal() as db:
            db.execute(text("SELECT 1"))
        
        # Get connection pool stats
        pool_stats = check_connection_pool_health(engine)
        
        return {
            "status": "healthy",
            "timestamp": time.time(),
            "database": "connected",
            "connection_pool": pool_stats
        }
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "timestamp": time.time(),
                "error": str(e)
            }
        )