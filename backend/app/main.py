# backend/app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .database import create_tables
from .routes import auth, equipment, sessions, analytics

# Create FastAPI app
app = FastAPI(
    title="HyCON Labs Equipment Management System",
    description="Digital equipment usage tracking and analytics system",
    version="1.0.0"
)

# Configure CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],  # React dev servers
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create database tables on startup
@app.on_event("startup")
def startup_event():
    create_tables()

# Include routers
app.include_router(auth.router)
app.include_router(equipment.router)
app.include_router(sessions.router)
app.include_router(analytics.router)

# Root endpoint
@app.get("/")
def read_root():
    return {
        "message": "HyCON Labs Equipment Management System API",
        "version": "1.0.0",
        "docs": "/docs"
    }

# Health check endpoint
@app.get("/health")
def health_check():
    return {"status": "healthy"}