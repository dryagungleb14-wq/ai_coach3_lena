from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, Boolean, ForeignKey, JSON, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
from config import DATABASE_URL
import logging

logger = logging.getLogger(__name__)

try:
    engine = create_engine(DATABASE_URL, pool_pre_ping=True)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
except Exception as e:
    logger.error(f"Ошибка создания engine: {e}")
    raise

Base = declarative_base()

class Call(Base):
    __tablename__ = "calls"
    
    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String, nullable=False)
    audio_url = Column(String)
    transcription = Column(Text)
    duration = Column(Float)
    manager = Column(String)
    call_date = Column(DateTime)
    call_identifier = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    status = Column(String, default="pending")
    progress = Column(Integer, default=0)
    
    evaluations = relationship("Evaluation", back_populates="call")

class Evaluation(Base):
    __tablename__ = "evaluations"
    
    id = Column(Integer, primary_key=True, index=True)
    call_id = Column(Integer, ForeignKey("calls.id"), nullable=False)
    scores = Column(JSON)
    итоговая_оценка = Column(Integer)
    нарушения = Column(Boolean, default=False)
    комментарии = Column(Text)
    is_retest = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    call = relationship("Call", back_populates="evaluations")

def migrate_db():
    from sqlalchemy import text, inspect
    
    try:
        inspector = inspect(engine)
        columns = [col['name'] for col in inspector.get_columns('calls')]
        
        with engine.begin() as conn:
            if 'status' not in columns:
                logger.info("Добавление колонки status в таблицу calls")
                conn.execute(text("ALTER TABLE calls ADD COLUMN status TEXT DEFAULT 'pending'"))
            
            if 'progress' not in columns:
                logger.info("Добавление колонки progress в таблицу calls")
                conn.execute(text("ALTER TABLE calls ADD COLUMN progress INTEGER DEFAULT 0"))
    except Exception as e:
        logger.error(f"Ошибка при проверке структуры таблицы: {e}")
        raise

def init_db():
    Base.metadata.create_all(bind=engine)
    try:
        migrate_db()
    except Exception as e:
        logger.warning(f"Ошибка при миграции БД (возможно таблица не существует): {e}")

