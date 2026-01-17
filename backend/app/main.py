# backend/app/main.py
from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from .database import create_tables, engine, check_connection_pool_health
from .routes import auth, equipment, sessions, analytics, samples
from .websocket_manager import manager
from .auth import verify_token
from .logging_config import setup_logging, cleanup_old_logs, get_log_stats
import logging
import time
import os
import asyncio
import json
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# Setup production-grade logging with rotation
logger = setup_logging()

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
    "http://localhost:8080",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:8080",
    "http://10.30.32.7:8080"
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
    logger.info("🚀 Starting HyCON Equipment Management System...")
    
    # Create database tables
    create_tables()
    logger.info("✅ Database tables initialized")
    
    # Start background scheduler for session management
    scheduler.add_job(
        lambda: check_and_end_expired_sessions(SessionLocal()),
        'interval',
        minutes=1,
        id='check_expired_sessions',
        replace_existing=True
    )
    
    # Add log cleanup job - runs daily at 3 AM
    scheduler.add_job(
        lambda: cleanup_old_logs(days_to_keep=30),
        'cron',
        hour=3,
        minute=0,
        id='cleanup_old_logs',
        replace_existing=True
    )
    
    scheduler.start()
    logger.info("✅ Background scheduler started (session checks + log cleanup)")
    
    # Log initial stats
    log_stats = get_log_stats()
    if log_stats:
        logger.info(f"📊 Current log size: {log_stats.get('total_size_mb', 0)} MB")

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on application shutdown"""
    logger.info("🛑 Shutting down application...")
    
    # Disconnect all WebSocket clients
    if manager.all_connections:
        logger.info(f"Disconnecting {len(manager.all_connections)} WebSocket clients...")
    
    scheduler.shutdown()
    logger.info("✅ Scheduler stopped")
    logger.info("👋 Shutdown complete")

# Include routers
app.include_router(auth.router)
app.include_router(equipment.router)
app.include_router(sessions.router)
app.include_router(analytics.router)
app.include_router(samples.router)

# WebSocket endpoint for real-time updates with comprehensive error handling
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for real-time updates
    
    Clients connect to receive live updates for:
    - Equipment status changes
    - Session start/end events
    - Sample submission updates
    - Notifications
    
    Features:
    - Automatic reconnection handling
    - Ping/pong keep-alive
    - Graceful degradation (falls back to polling on client side)
    """
    user_id = None
    websocket_logger = logging.getLogger('websocket')
    connection_start = time.time()
    
    try:
        # Accept connection
        await manager.connect(websocket)
        websocket_logger.info(f"🔌 New WebSocket connection established")
        
        # Optional: Extract user from token if provided
        # Clients can send: {"type": "auth", "token": "jwt_token"}
        try:
            initial_message = await asyncio.wait_for(
                websocket.receive_text(),
                timeout=10.0  # 10 second timeout for auth
            )
            import json
            auth_data = json.loads(initial_message)
            
            if auth_data.get("type") == "auth" and auth_data.get("token"):
                email = verify_token(auth_data["token"])
                if email:
                    # Get user_id from email
                    from .database import SessionLocal
                    from .models import User
                    db = SessionLocal()
                    try:
                        user = db.query(User).filter(User.email == email).first()
                        if user:
                            user_id = user.id
                            websocket_logger.info(f"✅ WebSocket authenticated | User: {email} (ID: {user_id})")
                            # Re-register with user_id
                            manager.disconnect(websocket)
                            await manager.connect(websocket, user_id)
                            # Send confirmation
                            await websocket.send_text(json.dumps({
                                "type": "auth_success",
                                "user_id": user_id,
                                "message": "WebSocket authenticated successfully",
                                "server_time": datetime.utcnow().isoformat()
                            }))
                        else:
                            websocket_logger.warning(f"⚠️ User not found for email: {email}")
                    finally:
                        db.close()
                else:
                    websocket_logger.warning(f"⚠️ Invalid token provided")
        except asyncio.TimeoutError:
            websocket_logger.info("⏱️ No authentication provided (timeout) - continuing as anonymous")
        except json.JSONDecodeError:
            websocket_logger.warning("⚠️ Invalid JSON in auth message - continuing as anonymous")
        except Exception as auth_error:
            websocket_logger.error(f"❌ WebSocket auth error: {str(auth_error)}", exc_info=True)
            # Continue with anonymous connection
        
        # Keep connection alive and handle incoming messages
        ping_count = 0
        while True:
            try:
                # Receive with timeout to detect stale connections
                data = await asyncio.wait_for(
                    websocket.receive_text(),
                    timeout=60.0  # 60 second timeout
                )
                message = json.loads(data)
                
                # Handle ping (keep-alive)
                if message.get("type") == "ping":
                    ping_count += 1
                    await websocket.send_text(json.dumps({
                        "type": "pong",
                        "timestamp": datetime.utcnow().isoformat(),
                        "ping_count": ping_count
                    }))
                    if ping_count % 10 == 0:  # Log every 10 pings
                        websocket_logger.debug(f"💓 Heartbeat | User: {user_id} | Pings: {ping_count}")
                    
            except asyncio.TimeoutError:
                # Send ping to check if client is alive
                try:
                    await websocket.send_text(json.dumps({"type": "ping"}))
                except Exception:
                    websocket_logger.warning(f"⚠️ Connection appears stale | User: {user_id}")
                    break
                    
            except WebSocketDisconnect:
                websocket_logger.info(f"👋 Client disconnected gracefully | User: {user_id}")
                break
                
            except json.JSONDecodeError as e:
                websocket_logger.warning(f"⚠️ Invalid JSON received | User: {user_id} | Error: {str(e)}")
                # Send error back to client
                try:
                    await websocket.send_text(json.dumps({
                        "type": "error",
                        "message": "Invalid JSON format"
                    }))
                except Exception:
                    break
                    
            except Exception as e:
                websocket_logger.error(f"❌ Error in WebSocket loop | User: {user_id} | Error: {str(e)}", exc_info=True)
                break
                
    except Exception as e:
        websocket_logger.error(f"❌ WebSocket connection error | User: {user_id} | Error: {str(e)}", exc_info=True)
        
    finally:
        # Cleanup
        connection_duration = time.time() - connection_start
        manager.disconnect(websocket, user_id)
        websocket_logger.info(
            f"🔌 WebSocket connection closed | User: {user_id} | "
            f"Duration: {connection_duration:.1f}s | Pings: {ping_count}"
        )
        
        # Send metrics to logger
        if connection_duration < 5:
            websocket_logger.warning(f"⚠️ Short-lived connection detected (< 5s) | User: {user_id}")

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