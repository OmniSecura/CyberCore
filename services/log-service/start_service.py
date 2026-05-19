"""
Entry point: python start_service.py
Starts the log-service FastAPI app on port 8083.
"""
import uvicorn

if __name__ == "__main__":
    uvicorn.run("src.server:app", host="0.0.0.0", port=8083, reload=False)
