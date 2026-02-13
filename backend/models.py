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
    error_details = Column(Text)
    requires_review = Column(Boolean, default=False)
    
    evaluations = relationship("Evaluation", back_populates="call")

class Evaluation(Base):
    __tablename__ = "evaluations"
    
    id = Column(Integer, primary_key=True, index=True)
    call_id = Column(Integer, ForeignKey("calls.id"), nullable=False)
    scores = Column(JSON)
    итоговая_оценка = Column(Float)
    max_score = Column(Float)
    score_percent = Column(Float)
    нарушения = Column(Boolean, default=False)
    комментарии = Column(Text)
    is_retest = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    call = relationship("Call", back_populates="evaluations")


class TelphinSync(Base):
    __tablename__ = "telphin_syncs"

    id = Column(Integer, primary_key=True, index=True)
    started_at = Column(DateTime, default=datetime.utcnow)
    finished_at = Column(DateTime)
    status = Column(String, default="running")
    calls_found = Column(Integer, default=0)
    calls_imported = Column(Integer, default=0)
    calls_skipped = Column(Integer, default=0)
    error_message = Column(Text)
    filter_start = Column(DateTime)
    filter_end = Column(DateTime)
    filter_min_duration = Column(Integer)


def migrate_db():
    from sqlalchemy import text, inspect
    
    try:
        inspector = inspect(engine)
        columns = [col['name'] for col in inspector.get_columns('calls')]
        
        with engine.begin() as conn:
            db_type = engine.dialect.name
            
            if 'status' not in columns:
                logger.info("Добавление колонки status в таблицу calls")
                conn.execute(text("ALTER TABLE calls ADD COLUMN status TEXT DEFAULT 'pending'"))
            
            if 'progress' not in columns:
                logger.info("Добавление колонки progress в таблицу calls")
                conn.execute(text("ALTER TABLE calls ADD COLUMN progress INTEGER DEFAULT 0"))
            
            if 'error_details' not in columns:
                logger.info("Добавление колонки error_details в таблицу calls")
                conn.execute(text("ALTER TABLE calls ADD COLUMN error_details TEXT"))
            
            if 'requires_review' not in columns:
                logger.info("Добавление колонки requires_review в таблицу calls")
                if db_type == 'postgresql':
                    conn.execute(text("ALTER TABLE calls ADD COLUMN requires_review BOOLEAN DEFAULT FALSE"))
                else:
                    conn.execute(text("ALTER TABLE calls ADD COLUMN requires_review BOOLEAN DEFAULT 0"))
        
        try:
            eval_columns = [col['name'] for col in inspector.get_columns('evaluations')]
            
            with engine.begin() as conn:
                db_type = engine.dialect.name
                
                if 'итоговая_оценка' in eval_columns:
                    try:
                        if db_type == 'postgresql':
                            conn.execute(text("ALTER TABLE evaluations ALTER COLUMN итоговая_оценка TYPE REAL"))
                            logger.info("Изменение типа итоговая_оценка с Integer на Float (PostgreSQL)")
                        elif db_type == 'sqlite':
                            logger.info("SQLite не требует изменения типа колонки (динамическая типизация)")
                        else:
                            logger.warning(f"Неизвестный тип БД {db_type}, пропуск изменения типа колонки")
                    except Exception as e:
                        logger.warning(f"Не удалось изменить тип итоговая_оценка: {e}")
                
                if 'max_score' not in eval_columns:
                    logger.info("Добавление колонки max_score в таблицу evaluations")
                    conn.execute(text("ALTER TABLE evaluations ADD COLUMN max_score REAL"))
                
                if 'score_percent' not in eval_columns:
                    logger.info("Добавление колонки score_percent в таблицу evaluations")
                    conn.execute(text("ALTER TABLE evaluations ADD COLUMN score_percent REAL"))
        except Exception as e:
            logger.warning(f"Таблица evaluations не существует или ошибка при миграции: {e}")
    except Exception as e:
        logger.error(f"Ошибка при проверке структуры таблицы: {e}")
        raise

def init_db():
    Base.metadata.create_all(bind=engine)
    try:
        migrate_db()
    except Exception as e:
        logger.warning(f"Ошибка при миграции БД (возможно таблица не существует): {e}")

