import os
import asyncio
import httpx
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from app.database import engine, SessionLocal
from app.models import Base
from app.routers import clients, sessions, rag
from app.routers.auth import router as auth_router

load_dotenv()

# Create tables
Base.metadata.create_all(bind=engine)


# Keep-alive: 10분마다 자기 자신을 ping하여 슬립 방지
async def keep_alive_task():
    """Render 슬립 방지 + Supabase 비활성 방지"""
    service_url = os.getenv("RENDER_EXTERNAL_URL", "http://localhost:8000")
    while True:
        await asyncio.sleep(600)  # 10분마다
        try:
            async with httpx.AsyncClient() as client:
                # Render 슬립 방지
                await client.get(f"{service_url}/api/health", timeout=10)
                # Supabase 비활성 방지 (간단한 쿼리)
                db = SessionLocal()
                db.execute("SELECT 1")
                db.close()
        except Exception:
            pass


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    task = asyncio.create_task(keep_alive_task())
    yield
    # Shutdown
    task.cancel()


app = FastAPI(
    title="Healthcare AI Counseling Assistant API",
    version="1.0.0",
    lifespan=lifespan,
)

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
