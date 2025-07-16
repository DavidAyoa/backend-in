"""
Main application entry point for Voice Agent Backend
Using FastAPI and websockets for interaction
"""
import asyncio
import structlog
from fastapi import FastAPI

from .pipeline import pipeline
from .config import config

logger = structlog.get_logger()

app = FastAPI()

@app.on_event("startup")
async def startup_event():
    """Initialize and start pipeline on startup"""
    logger.info("Starting up FastAPI application")
    if config.validate():
        asyncio.create_task(pipeline.run())
    else:
        logger.error("Configuration validation failed on startup")

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanly shutdown pipeline on app shutdown"""
    logger.info("Shutting down FastAPI application")
    await pipeline.stop()

@app.get("/")
async def root():
    """Root endpoint to verify server is running"""
    return {"message": "Welcome to the Voice Agent Backend!"}
