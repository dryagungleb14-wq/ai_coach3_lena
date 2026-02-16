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
    telphin_sync_id = Column(Integer, ForeignKey("telphin_syncs.id"), nullable=True)

    evaluations = relationship("Evaluation", back_populates="call")
    telphin_sync = relationship("TelphinSync", backref="calls")

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


class TelphinExtension(Base):
    __tablename__ = "telphin_extensions"

    id = Column(Integer, primary_key=True, index=True)
    extension_id = Column(String, unique=True, nullable=False)
    extension_name = Column(String)
    extension_type = Column(String)
    manager_name = Column(String)
    is_monitored = Column(Boolean, default=False)


class Manager(Base):
    __tablename__ = "managers"

    id = Column(Integer, primary_key=True, index=True)
    extension = Column(String, unique=True, nullable=False, index=True)
    full_name = Column(String, nullable=False)
    position = Column(String)
    is_active = Column(Boolean, default=True)


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

            if 'telphin_sync_id' not in columns:
                logger.info("Добавление колонки telphin_sync_id в таблицу calls")
                conn.execute(text("ALTER TABLE calls ADD COLUMN telphin_sync_id INTEGER"))
        
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

def seed_managers():
    """Заполнение справочника менеджеров"""
    db = SessionLocal()
    try:
        # Проверяем, есть ли уже данные
        existing_count = db.query(Manager).count()
        if existing_count > 0:
            logger.info(f"Справочник менеджеров уже содержит {existing_count} записей, пропускаем заполнение")
            return

        managers_data = [
            {"extension": "101", "full_name": "Линдоренко Татьяна", "position": "Менеджер по записи на пробные уроки / индивидуальное ведение"},
            {"extension": "102", "full_name": "Слизунова Диана", "position": "Менеджер по записи на пробные уроки / индивидуальное ведение"},
            {"extension": "104", "full_name": "Рената Латыпова", "position": "Менеджер по записи на пробные уроки / индивидуальное ведение"},
            {"extension": "117", "full_name": "Козячая Екатерина", "position": "Менеджер по записи на пробные уроки / индивидуальное ведение"},
            {"extension": "108", "full_name": "Певень Анна", "position": "Менеджер по записи на пробные уроки / индивидуальное ведение"},
            {"extension": "115", "full_name": "Татьяна Королькова", "position": "Менеджер по записи на пробные уроки / индивидуальное ведение"},
            {"extension": "112", "full_name": "Даугерт Елизавета", "position": "Менеджер по записи на пробные уроки / индивидуальное ведение"},
            {"extension": "109", "full_name": "Меликова Эльвира", "position": "Менеджер по записи на пробные уроки / индивидуальное ведение"},
            {"extension": "106", "full_name": "Дригваль Михаил", "position": "Менеджер по записи на пробные уроки / индивидуальное ведение"},
            {"extension": "107", "full_name": "Платова Анна", "position": "Менеджер по записи на пробные уроки / индивидуальное ведение"},
            {"extension": "121", "full_name": "Александра Слюнина", "position": "Менеджер по записи на пробные уроки / индивидуальное ведение"},
            {"extension": "169", "full_name": "Карпенко Никита (Ника)", "position": "Менеджер по записи на пробные уроки / индивидуальное ведение"},
            {"extension": "172", "full_name": "Некрашевич Евгений", "position": "Менеджер по записи на пробные уроки / индивидуальное ведение"},
            {"extension": "175", "full_name": "Сарафинович Карина", "position": "Менеджер по записи на пробные уроки / индивидуальное ведение"},
            {"extension": "201", "full_name": "Кузьмук Александра", "position": "Менеджер по записи на пробные уроки / индивидуальное ведение"},
            {"extension": "194", "full_name": "Криволап Полина", "position": "Менеджер по записи на пробные уроки / индивидуальное ведение"},
            {"extension": "195", "full_name": "Василевская Дарья", "position": "Менеджер по записи на пробные уроки / индивидуальное ведение"},
            {"extension": "120", "full_name": "Гончарова Наталья", "position": "Менеджер по записи на пробные уроки / индивидуальное ведение"},
            {"extension": "204", "full_name": "Кирилл Жигунов", "position": "Менеджер по записи на пробные уроки / индивидуальное ведение"},
            {"extension": "123", "full_name": "Судникович Диана", "position": "Менеджер по записи на пробные уроки / индивидуальное ведение"},
            {"extension": "177", "full_name": "Жирнова Ольга", "position": "Менеджер по записи на пробные уроки / индивидуальное ведение"},
            {"extension": "114", "full_name": "Баршинов Илья", "position": "Менеджер по записи на пробные уроки / индивидуальное ведение"},
            {"extension": "196", "full_name": "Гучек Калина (чатовик)", "position": "Администратор / Администратор чатов (допробники)"},
            {"extension": "193", "full_name": "Данилкина Алина (чатовик)", "position": "Администратор / Администратор чатов (допробники)"},
            {"extension": "197", "full_name": "Ефимович Виктория (чатовик)", "position": "Администратор / Администратор чатов (допробники)"},
            {"extension": "202", "full_name": "Горбачева Марта (чатовик)", "position": "Администратор / Администратор чатов (допробники)"},
            {"extension": "167", "full_name": "Пятачкова Алина (чатовик)", "position": "Администратор / Администратор чатов (допробники)"},
            {"extension": "179", "full_name": "Голодко (Костянко) Анастасия (чатовик)", "position": "Администратор / Администратор чатов (допробники)"},
            {"extension": "168", "full_name": "Дарья Экгардт", "position": "Руководитель: Холодные продажи"},
            {"extension": "161", "full_name": "Татьяна Кулик", "position": "Менеджер по холодным продажам / индивидуальное ведение"},
            {"extension": "174", "full_name": "Полина Эймонтас", "position": "Менеджер по холодным продажам / индивидуальное ведение"},
            {"extension": "187", "full_name": "Бачинина Яна", "position": "Менеджер по холодным продажам / индивидуальное ведение"},
            {"extension": "188", "full_name": "Трапенок Елизавета", "position": "Менеджер по холодным продажам / индивидуальное ведение"},
            {"extension": "198", "full_name": "Михасёва Анна", "position": "Менеджер по холодным продажам / индивидуальное ведение"},
            {"extension": "113", "full_name": "Печерская Юлия", "position": "Менеджер отдела послепробников / индивидуальное ведение"},
            {"extension": "119", "full_name": "Леонюк Илья", "position": "Менеджер отдела послепробников / индивидуальное ведение"},
            {"extension": "118", "full_name": "Шатилова Ольга", "position": "Менеджер отдела послепробников / индивидуальное ведение"},
            {"extension": "111", "full_name": "Панковец Кристина", "position": "Менеджер отдела послепробников / индивидуальное ведение"},
            {"extension": "162", "full_name": "Лихтарович Евгения", "position": "Менеджер отдела послепробников / индивидуальное ведение"},
            {"extension": "110", "full_name": "Харланчук Екатерина", "position": "Менеджер по записи на пробные уроки / индивидуальное ведение"},
            {"extension": "105", "full_name": "Антонишина Дарья", "position": "Менеджеры по обучению/ индивидуальное ведение"},
            {"extension": "103", "full_name": "Лисовская Алина", "position": "Менеджеры по обучению/ индивидуальное ведение"},
            {"extension": "183", "full_name": "Крюк Дарья", "position": "Менеджеры по обучению/ индивидуальное ведение"},
            {"extension": "129", "full_name": "Бахар Ольга", "position": "Менеджеры по обучению/ индивидуальное ведение"},
            {"extension": "192", "full_name": "Лапёнок Владислав", "position": "Менеджеры по обучению/ индивидуальное ведение"},
            {"extension": "122", "full_name": "Банель Арсений", "position": "Менеджеры по обучению/ индивидуальное ведение"},
            {"extension": "205", "full_name": "Корхов Павел", "position": "Менеджеры по обучению/ индивидуальное ведение"},
            {"extension": "158", "full_name": "Шарендо Александра", "position": "Менеджеры по обучению/ индивидуальное ведение"},
            {"extension": "191", "full_name": "Елизавета Скадрински", "position": "Менеджеры по обучению/ индивидуальное ведение"},
            {"extension": "131", "full_name": "Войтеховская Татьяна", "position": "Менеджеры по обучению/ индивидуальное ведение"},
            {"extension": "178", "full_name": "Акулова Александра", "position": "Менеджеры по обучению/ индивидуальное ведение"},
            {"extension": "173", "full_name": "Караян Валерий", "position": "Менеджеры по обучению/ индивидуальное ведение"},
            {"extension": "189", "full_name": "Казимиренко Полина", "position": "Менеджеры по обучению/ индивидуальное ведение"},
            {"extension": "190", "full_name": "Скамьин Виктор", "position": "Менеджеры по обучению/ индивидуальное ведение"},
            {"extension": "206", "full_name": "Садошенко Елисавета", "position": "Менеджеры по обучению/ индивидуальное ведение"},
            {"extension": "171", "full_name": "Хвойницкая Надежда", "position": "Менеджеры по обучению/ индивидуальное ведение"},
        ]

        for data in managers_data:
            manager = Manager(**data)
            db.add(manager)

        db.commit()
        logger.info(f"Успешно добавлено {len(managers_data)} менеджеров в справочник")
    except Exception as e:
        logger.error(f"Ошибка при заполнении справочника менеджеров: {e}")
        db.rollback()
    finally:
        db.close()


def init_db():
    Base.metadata.create_all(bind=engine)
    try:
        migrate_db()
    except Exception as e:
        logger.warning(f"Ошибка при миграции БД (возможно таблица не существует): {e}")

    # Заполняем справочник менеджеров
    try:
        seed_managers()
    except Exception as e:
        logger.warning(f"Ошибка при заполнении справочника менеджеров: {e}")

