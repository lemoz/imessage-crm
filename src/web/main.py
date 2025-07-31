#!/usr/bin/env python3
"""
iMessage CRM Web Dashboard
FastAPI server for the web-based interface
"""

import sys
from pathlib import Path
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from web.api import api_router

# Create FastAPI app
app = FastAPI(
    title="iMessage CRM Dashboard",
    description="Web interface for iMessage CRM with AI-powered conversation insights",
    version="0.1.0"
)

# Mount static files
static_path = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=static_path), name="static")

# Include API routes
app.include_router(api_router, prefix="/api/v1")

@app.get("/")
async def root():
    """Serve the main dashboard HTML"""
    return FileResponse(static_path / "index.html")

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "iMessage CRM Dashboard"}