"""
HYCON Backend Server
Start the FastAPI application with Uvicorn.
Works on Windows, macOS, and Linux.
"""

import uvicorn
from app.database import engine
from app import models
from mock_data import create_mock_data

if __name__ == "__main__":
    # Create database tables
    models.Base.metadata.create_all(bind=engine)
    
    # Create mock data
    create_mock_data()
    
    # Run the FastAPI server
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
