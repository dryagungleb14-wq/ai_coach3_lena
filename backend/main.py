import sys
import os
import logging
import logging.config
import json
import time
from fastapi import Request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from api.routes import router
from models import init_db
from services.websocket_service import manager
from config import GEMINI_API_KEY, DATABASE_URL

config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logging_config.json")
with open(config_path, "r") as f:
    log_config = json.load(f)
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    log_config["root"]["level"] = log_level
    for logger_name in log_config.get("loggers", {}):
        log_config["loggers"][logger_name]["level"] = log_level
    logging.config.dictConfig(log_config)

logger = logging.getLogger(__name__)

app = FastAPI(title="AI Coach API", version="1.0.0")

@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    origin = request.headers.get("origin", "не указан")
    logger.info(f"Входящий запрос: {request.method} {request.url.path} | Origin: {origin}")
    response = await call_next(request)
    process_time = time.time() - start_time
    logger.info(f"Запрос {request.method} {request.url.path} выполнен за {process_time:.2f}с, статус: {response.status_code}")
    return response

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api", tags=["api"])

@app.websocket("/ws/analyze/{call_id}")
async def websocket_analyze(websocket: WebSocket, call_id: int):
    await manager.connect(websocket, call_id)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket, call_id)

@app.on_event("startup")
async def startup_event():
    try:
        if not GEMINI_API_KEY or GEMINI_API_KEY.strip() == "":
            logger.warning("GEMINI_API_KEY не установлен или пустой. Транскрипция и оценка не будут работать.")
        else:
            logger.info("GEMINI_API_KEY настроен")
        
        if not DATABASE_URL or DATABASE_URL.strip() == "":
            logger.warning("DATABASE_URL не установлен. Используется значение по умолчанию.")
        else:
            logger.info("DATABASE_URL настроен")
        
        init_db()
        logger.info("База данных инициализирована")
        import asyncio
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = asyncio.get_event_loop()
        manager.set_event_loop(loop)
    except Exception as e:
        logger.error(f"Ошибка инициализации БД: {e}")
        raise

@app.get("/")
def read_root():
    return {"message": "AI Coach API", "status": "ok"}

@app.get("/health")
def health_check():
    return {"status": "healthy"}

@app.get("/api/health")
def api_health_check():
    return {"status": "healthy", "message": "AI Coach API is running"}

@app.get("/api/config/check")
def check_config():
    config_status = {
        "gemini_api_key": "configured" if GEMINI_API_KEY and GEMINI_API_KEY.strip() != "" else "missing",
        "database_url": "configured" if DATABASE_URL and DATABASE_URL.strip() != "" else "missing",
        "status": "ok" if (GEMINI_API_KEY and GEMINI_API_KEY.strip() != "") and (DATABASE_URL and DATABASE_URL.strip() != "") else "incomplete"
    }
    return config_status

