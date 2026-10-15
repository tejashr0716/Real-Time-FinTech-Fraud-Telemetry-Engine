import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.config import settings
from app.services.redis_service import redis_service
from app.services.rabbitmq_service import rabbitmq_service
from app.services.database_service import db_service
from app.services.cosmos_service import cosmos_service
from app.services.cpp_engine import cpp_engine
from app.services.websocket_manager import ws_telemetry
from app.routers import (
    transactions_router,
    accounts_router,
    telemetry_router,
    ws_router,
)

current_dir = os.path.dirname(os.path.abspath(__file__))
templates_dir = os.path.join(current_dir, "templates")
templates = Jinja2Templates(directory=templates_dir)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup sequence
    await db_service.connect()
    await redis_service.connect()
    await rabbitmq_service.connect()
    await cosmos_service.connect()
    await ws_telemetry.start_background_tasks()

    print("=" * 75)
    print("🛡️ REAL-TIME FINTECH FRAUD TELEMETRY & STREAM INGESTION ENGINE")
    print(f"🚀 C++ SIMD Native Heuristic Rule Engine: {'LOADED & ACCELERATED' if cpp_engine.is_loaded else 'PYTHON FALLBACK'}")
    print(f"📡 High-Frequency WebSocket Telemetry Stream: ws://localhost:{settings.PORT}/ws/telemetry")
    print(f"🐰 RabbitMQ Exchange: {settings.EXCHANGE_TRANSACTIONS}")
    print(f"🐘 Database: PostgreSQL / Azure SQL ({settings.POSTGRES_DB})")
    print("=" * 75)
    yield
    # Shutdown sequence
    await rabbitmq_service.close()
    await redis_service.close()
    await db_service.close()
    print("🛑 Fraud Engine Gateway shutdown cleanly.")

app = FastAPI(
    title=settings.APP_NAME,
    description="Sub-millisecond event-driven fraud detection engine with C++ SIMD acceleration, RabbitMQ, Redis, Apache Spark, and Azure SQL/Cosmos DB.",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(transactions_router)
app.include_router(accounts_router)
app.include_router(telemetry_router)
app.include_router(ws_router)

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "cpp_engine_accelerated": cpp_engine.is_loaded,
        "rabbitmq_connected": rabbitmq_service.is_connected,
        "database_connected": db_service.pool is not None,
        "redis_connected": redis_service.client is not None,
        "active_ws_clients": len(ws_telemetry.active_connections)
    }

@app.get("/", response_class=HTMLResponse)
async def serve_dashboard(request: Request):
    return templates.TemplateResponse(request=request, name="index.html")
