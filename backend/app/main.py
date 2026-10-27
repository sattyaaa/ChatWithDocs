"""
Main FastAPI entrypoint for QADoc.
Provides REST API endpoints for user auth, chat sessions, document ingestion, and ReAct agent QA.
"""

from contextlib import asynccontextmanager
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import auth, chats, documents
from qadoc.database.connection import initialize_database

logger = logging.getLogger("qadoc.api")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application startup and shutdown lifecycle management.
    """
    logger.info("Starting QADoc API service...")
    try:
        initialize_database()
        logger.info("MongoDB database connection and indexes verified successfully.")
    except Exception as e:
        logger.error(f"Failed to initialize database on startup: {e}")
    yield
    logger.info("Shutting down QADoc API service...")


app = FastAPI(
    title="QADoc REST API",
    description="Backend API for Document QA Assistant powered by MongoDB Atlas Vector Search, Jina AI, and Groq ReAct Agent.",
    version="0.2.0",
    lifespan=lifespan,
)

# Enable CORS for React frontend (Vite runs on port 5173 by default)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "*",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(auth.router)
app.include_router(chats.router)
app.include_router(documents.router)


@app.get("/api/health")
def healthcheck():
    """Healthcheck endpoint for monitoring and readiness probes."""
    return {"status": "ok", "service": "qadoc-api"}
