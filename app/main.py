from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from app.routers import pdf
import os

# Create necessary directories if they don't exist
os.makedirs("uploads", exist_ok=True)
os.makedirs("static", exist_ok=True)

app = FastAPI(
    title="AI Agent Support Service",
    description="A service to provide various utilities for AI agents, starting with PDF processing.",
    version="1.0.0"
)

# Mount the static directory to serve generated images
app.mount("/static", StaticFiles(directory="static"), name="static")

# Include the PDF processing router
app.include_router(pdf.router, prefix="/api/v1", tags=["PDF Processing"])

@app.get("/", tags=["Root"])
async def read_root():
    """A simple endpoint to check if the service is running."""
    return {"message": "Welcome to the AI Agent Support Service!"} 