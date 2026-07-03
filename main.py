from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from app.database import engine
from app.models import Base
from app.routers import clients, sessions, rag
from app.routers.auth import router as auth_router

load_dotenv()

# Create tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Healthcare AI Counseling Assistant API", version="1.0.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(auth_router)
app.include_router(clients.router)
app.include_router(sessions.router)
app.include_router(rag.router)


@app.get("/api/health")
def health_check():
    return {"status": "ok", "service": "healthcare-ai-counseling-assistant"}
