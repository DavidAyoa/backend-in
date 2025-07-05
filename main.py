from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import auth, agents, sessions, websocket
from database import engine, Base

# Import all models to ensure they are registered with SQLAlchemy
from models import user, agent, session, conversation_history

# Create database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="LiveKit Agents Server",
    description="A server that abstracts LiveKit using the LiveKit Agents Python framework",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure this properly for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router, prefix="/auth", tags=["Authentication"])
app.include_router(agents.router, prefix="/agents", tags=["Agents"])
app.include_router(sessions.router, prefix="/sessions", tags=["Sessions"])
app.include_router(websocket.router, tags=["WebSocket"])

@app.get("/")
async def root():
    return {"message": "LiveKit Agents Server is running!"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"} 