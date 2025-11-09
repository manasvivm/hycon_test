# backend/run.py
import uvicorn
from app.main import app
from mock_data import create_mock_data

if __name__ == "__main__":
    # Create mock data before starting the server
    create_mock_data()
    
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )