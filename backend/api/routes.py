from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends
from fastapi.responses import FileResponse, Response
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from typing import List, Optional
from datetime import datetime
import os
import sys
import uuid
import csv
import io
import logging
import threading

logger = logging.getLogger(__name__)

try:
    from mutagen import File as MutagenFile
    from mutagen.mp3 import MP3
    from mutagen.wave import WAVE
    MUTAGEN_AVAILABLE = True
except ImportError:
    MUTAGEN_AVAILABLE = False
    logger.warning("mutagen не установлен, длительность аудио не будет извлекаться")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models import Call, Evaluation, SessionLocal, init_db
from services.transcription_service import transcribe_audio
from services.evaluation_service import evaluate_transcription
from services.websocket_service import manager
router = APIRouter()

def get_audio_duration(audio_path: str) -> Optional[float]:
    if not MUTAGEN_AVAILABLE:
        return None
    
    try:
        audio_file = MutagenFile(audio_path)
        if audio_file is None:
            return None
        
        duration = audio_file.info.length
        return duration
    except Exception as e:
        logger.warning(f"Не удалось извлечь длительность из {audio_path}: {e}")
        return None

def format_duration(seconds: Optional[float]) -> str:
    if seconds is None:
        return ""
    try:
        total = int(seconds)
        minutes = total // 60
        secs = total % 60
        return f"{minutes}:{secs:02d}"
    except Exception:
        return ""

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/upload")
async def upload_files(
    files: List[UploadFile] = File(...),
    manager: Optional[str] = Form(None),
    call_date: Optional[str] = Form(None),
    call_identifier: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    if not files:
        raise HTTPException(status_code=400, detail="Не указаны файлы для загрузки")
    
    uploaded_calls = []
    
    MAX_FILE_SIZE = 100 * 1024 * 1024
    
    for file in files:
        if not file.content_type or not file.content_type.startswith("audio/"):
            logger.warning(f"Файл {file.filename} пропущен: неверный тип контента {file.content_type}")
            continue
        
        try:
            content = await file.read()
            file_size = len(content)
            
            if file_size > MAX_FILE_SIZE:
                logger.warning(f"Файл {file.filename} пропущен: размер {file_size} байт превышает максимум {MAX_FILE_SIZE} байт")
                continue
            
            if file_size == 0:
                logger.warning(f"Файл {file.filename} пропущен: пустой файл")
                continue
            
            file_id = str(uuid.uuid4())
            filename = f"{file_id}_{file.filename}"
            backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            uploads_dir = os.path.join(backend_dir, "uploads")
            os.makedirs(uploads_dir, exist_ok=True)
            file_path = os.path.join(uploads_dir, filename)
            
            with open(file_path, "wb") as f:
                f.write(content)
            
            duration = get_audio_duration(file_path)
            
            call_date_obj = None
            if call_date:
                try:
                    call_date_obj = datetime.fromisoformat(call_date.replace("Z", "+00:00"))
                except:
                    pass
            
            call = Call(
                filename=file.filename,
                audio_url=file_path,
                manager=manager,
                call_date=call_date_obj,
                call_identifier=call_identifier,
                duration=duration
            )
            
            db.add(call)
            db.commit()
            db.refresh(call)
            
            uploaded_calls.append({
                "id": call.id,
                "filename": call.filename,
                "manager": call.manager,
                "call_date": call.call_date.isoformat() if call.call_date else None,
                "call_identifier": call.call_identifier,
                "requires_review": call.requires_review
            })
            
            thread = threading.Thread(target=analyze_in_background, args=(call.id, file_path), daemon=True)
            thread.start()
            logger.info(f"Автоматически запущен анализ для звонка {call.id}")
        except Exception as e:
            db.rollback()
            raise HTTPException(status_code=500, detail=f"Ошибка при загрузке файла {file.filename}: {str(e)}")
    
    if not uploaded_calls:
        raise HTTPException(status_code=400, detail="Не удалось загрузить ни один файл. Убедитесь, что файлы имеют аудио формат.")
    
    return {"calls": uploaded_calls}

def update_progress(call_id: int, progress: int, status: str = None, message: str = None):
    db_local = SessionLocal()
    try:
        call_local = db_local.query(Call).filter(Call.id == call_id).first()
        if call_local:
            call_local.progress = progress
            if status:
                call_local.status = status
            db_local.commit()
    except Exception as e:
        logger.error(f"Ошибка обновления прогресса: {e}")
    finally:
        db_local.close()
    
    manager.send_progress_sync(call_id, progress, status or "processing", message)

def analyze_in_background(call_id: int, audio_path: str):
    try:
        update_progress(call_id, 10, "processing", "Начало транскрипции...")
        logger.info(f"Начало транскрипции файла {audio_path}")
        
        transcription = transcribe_audio(audio_path)
        
        if not transcription or len(transcription.strip()) == 0:
            raise Exception("Транскрипция пустая. Невозможно провести оценку.")
        
        update_progress(call_id, 90, "processing", "Транскрипция завершена, сохранение...")
        logger.info(f"Транскрипция завершена, длина текста: {len(transcription)} символов")
        
        db_local = SessionLocal()
        try:
            call_local = db_local.query(Call).filter(Call.id == call_id).first()
            if call_local:
                call_local.transcription = transcription
                db_local.commit()
                logger.info("Транскрипция сохранена в БД")
        finally:
            db_local.close()
        
        update_progress(call_id, 95, "processing", "Начало оценки транскрипции...")
        logger.info("Начало оценки транскрипции")
        
        evaluation_result = evaluate_transcription(transcription)
        logger.info(f"Оценка завершена, итоговый балл: {evaluation_result.get('итоговая_оценка', 'N/A')}")
        
        db_local = SessionLocal()
        try:
            call_local = db_local.query(Call).filter(Call.id == call_id).first()
            if call_local:
                evaluation = Evaluation(
                    call_id=call_id,
                    scores=evaluation_result["scores"],
                    итоговая_оценка=evaluation_result["итоговая_оценка"],
                    max_score=evaluation_result.get("max_score"),
                    score_percent=evaluation_result.get("score_percent"),
                    нарушения=evaluation_result["нарушения"],
                    комментарии=evaluation_result["комментарии"],
                    is_retest=False
                )
                db_local.add(evaluation)
                call_local.status = "completed"
                call_local.progress = 100
                special = evaluation_result.get("special_circumstances") or {}
                has_special = any(
                    bool(special.get(key))
                    for key in [
                        "client_refused_questions",
                        "no_trainer",
                        "no_trainer_time",
                        "trainer_search",
                        "parent_child_discussion",
                        "conversation_interrupted",
                        "technical_issues",
                        "client_reaction",
                        "no_lesson_scheduled",
                    ]
                )
                score_percent = evaluation_result.get("score_percent") or 0
                if has_special or score_percent < 60:
                    call_local.requires_review = True
                db_local.commit()
                logger.info(f"Анализ звонка {call_id} успешно завершен")
        finally:
            db_local.close()
        
        update_progress(call_id, 100, "completed", "Анализ завершен")
        
        if os.path.exists(audio_path):
            try:
                os.remove(audio_path)
                logger.info(f"Аудио файл удален после успешного анализа: {audio_path}")
            except Exception as e:
                logger.warning(f"Не удалось удалить аудио файл {audio_path}: {e}")
            
    except Exception as e:
        import traceback
        error_traceback = traceback.format_exc()
        error_details = f"{str(e)}\n\n{error_traceback}"
        logger.error(f"Ошибка в фоновой задаче: {e}")
        logger.error(error_traceback)
        db_local = SessionLocal()
        try:
            call_local = db_local.query(Call).filter(Call.id == call_id).first()
            if call_local:
                call_local.status = "failed"
                call_local.error_details = error_details
                db_local.commit()
        finally:
            db_local.close()
        update_progress(call_id, 0, "failed", f"Ошибка: {str(e)}")
        
        if os.path.exists(audio_path):
            try:
                os.remove(audio_path)
                logger.info(f"Аудио файл удален после ошибки анализа: {audio_path}")
            except Exception as e:
                logger.warning(f"Не удалось удалить аудио файл {audio_path}: {e}")

@router.post("/analyze/{call_id}")
async def analyze_call(call_id: int, db: Session = Depends(get_db)):
    try:
        logger.info(f"Начало анализа звонка {call_id}")
        call = db.query(Call).filter(Call.id == call_id).first()
        if not call:
            logger.error(f"Звонок {call_id} не найден")
            raise HTTPException(status_code=404, detail="Call not found")
        
        if not call.audio_url:
            logger.error(f"У звонка {call_id} нет audio_url")
            raise HTTPException(status_code=400, detail="Audio file not found")
        
        audio_path = call.audio_url
        if not os.path.isabs(audio_path):
            backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            audio_path = os.path.join(backend_dir, audio_path)
        
        logger.info(f"Путь к аудио файлу: {audio_path}")
        
        if not os.path.exists(audio_path):
            logger.error(f"Аудио файл не найден по пути: {audio_path}")
            raise HTTPException(status_code=400, detail=f"Audio file not found at {audio_path}")
        
        if not os.path.isfile(audio_path):
            logger.error(f"Путь не является файлом: {audio_path}")
            raise HTTPException(status_code=400, detail=f"Audio path is not a file: {audio_path}")
        
        call.status = "processing"
        call.progress = 0
        db.commit()
        
        thread = threading.Thread(target=analyze_in_background, args=(call_id, audio_path), daemon=True)
        thread.start()
        
        return {
            "call_id": call_id,
            "status": "processing",
            "progress": 0,
            "message": "Анализ начат, проверяйте статус через /api/analyze/{call_id}/status"
        }
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        logger.error(f"Критическая ошибка при анализе звонка {call_id}: {e}")
        logger.error(traceback.format_exc())
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Ошибка при анализе: {str(e)}")

@router.get("/analyze/{call_id}/status")
async def get_analyze_status(call_id: int, db: Session = Depends(get_db)):
    call = db.query(Call).filter(Call.id == call_id).first()
    if not call:
        raise HTTPException(status_code=404, detail="Call not found")
    
    return {
        "call_id": call_id,
        "status": call.status or "pending",
        "progress": call.progress or 0
    }

@router.post("/analyze/{call_id}/retest")
async def retest_call(call_id: int, db: Session = Depends(get_db)):
    call = db.query(Call).filter(Call.id == call_id).first()
    if not call:
        raise HTTPException(status_code=404, detail="Call not found")
    
    if not call.transcription:
        raise HTTPException(status_code=400, detail="Transcription not found")
    
    evaluation_result = evaluate_transcription(call.transcription)
    
    evaluation = Evaluation(
        call_id=call_id,
        scores=evaluation_result["scores"],
        итоговая_оценка=evaluation_result["итоговая_оценка"],
        max_score=evaluation_result.get("max_score"),
        score_percent=evaluation_result.get("score_percent"),
        нарушения=evaluation_result["нарушения"],
        комментарии=evaluation_result["комментарии"],
        is_retest=True
    )
    
    db.add(evaluation)
    special = evaluation_result.get("special_circumstances") or {}
    has_special = any(
        bool(special.get(key))
        for key in [
            "client_refused_questions",
            "no_trainer",
            "no_trainer_time",
            "trainer_search",
            "parent_child_discussion",
            "conversation_interrupted",
            "technical_issues",
            "client_reaction",
            "no_lesson_scheduled",
        ]
    )
    score_percent = evaluation_result.get("score_percent") or 0
    if has_special or score_percent < 60:
        call.requires_review = True
    db.commit()
    db.refresh(evaluation)
    
    return {
        "call_id": call_id,
        "evaluation": {
            "id": evaluation.id,
            "scores": evaluation.scores,
            "итоговая_оценка": evaluation.итоговая_оценка,
            "max_score": evaluation.max_score,
            "score_percent": evaluation.score_percent,
            "нарушения": evaluation.нарушения,
            "комментарии": evaluation.комментарии,
            "is_retest": True
        }
    }

@router.get("/calls")
async def get_calls(
    manager: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    db: Session = Depends(get_db)
):
    query = db.query(Call)
    
    if manager:
        query = query.filter(Call.manager == manager)
    
    if start_date:
        try:
            start_dt = datetime.fromisoformat(start_date.replace("Z", "+00:00"))
            query = query.filter(Call.call_date >= start_dt)
        except:
            pass
    
    if end_date:
        try:
            end_dt = datetime.fromisoformat(end_date.replace("Z", "+00:00"))
            query = query.filter(Call.call_date <= end_dt)
        except:
            pass
    
    calls = query.order_by(Call.created_at.desc()).all()
    
    if not calls:
        return {"calls": []}
    
    call_ids = [call.id for call in calls]
    
    latest_eval_subq = db.query(
        Evaluation.call_id,
        func.max(Evaluation.created_at).label('max_created_at')
    ).filter(
        Evaluation.call_id.in_(call_ids)
    ).group_by(Evaluation.call_id).subquery()
    
    latest_evaluations = db.query(Evaluation).join(
        latest_eval_subq,
        (Evaluation.call_id == latest_eval_subq.c.call_id) &
        (Evaluation.created_at == latest_eval_subq.c.max_created_at)
    ).order_by(desc(Evaluation.id)).all()
    
    eval_dict = {}
    for ev in latest_evaluations:
        if ev.call_id not in eval_dict:
            eval_dict[ev.call_id] = ev
    
    result = []
    for call in calls:
        latest_evaluation = eval_dict.get(call.id)
        
        result.append({
            "id": call.id,
            "filename": call.filename,
            "manager": call.manager,
            "call_date": call.call_date.isoformat() if call.call_date else None,
            "call_identifier": call.call_identifier,
            "duration": call.duration,
            "created_at": call.created_at.isoformat(),
            "requires_review": call.requires_review,
            "evaluation": {
                "итоговая_оценка": latest_evaluation.итоговая_оценка if latest_evaluation else None,
                "max_score": latest_evaluation.max_score if latest_evaluation else None,
                "score_percent": latest_evaluation.score_percent if latest_evaluation else None,
                "нарушения": latest_evaluation.нарушения if latest_evaluation else False
            } if latest_evaluation else None
        })
    
    return {"calls": result}

@router.get("/calls/{call_id}")
async def get_call(call_id: int, db: Session = Depends(get_db)):
    call = db.query(Call).filter(Call.id == call_id).first()
    if not call:
        raise HTTPException(status_code=404, detail="Call not found")
    
    evaluations = db.query(Evaluation).filter(
        Evaluation.call_id == call_id
    ).order_by(Evaluation.created_at.desc()).all()
    
    return {
        "id": call.id,
        "filename": call.filename,
        "manager": call.manager,
        "call_date": call.call_date.isoformat() if call.call_date else None,
        "call_identifier": call.call_identifier,
        "transcription": call.transcription,
        "duration": call.duration,
        "created_at": call.created_at.isoformat(),
        "requires_review": call.requires_review,
        "evaluations": [
            {
                "id": ev.id,
                "scores": ev.scores,
                "итоговая_оценка": ev.итоговая_оценка,
                "max_score": ev.max_score,
                "score_percent": ev.score_percent,
                "нарушения": ev.нарушения,
                "комментарии": ev.комментарии,
                "is_retest": ev.is_retest,
                "created_at": ev.created_at.isoformat()
            }
            for ev in evaluations
        ]
    }

@router.get("/stats")
async def get_stats(
    manager: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    db: Session = Depends(get_db)
):
    query = db.query(Call)
    
    if manager:
        query = query.filter(Call.manager == manager)
    
    if start_date:
        try:
            start_dt = datetime.fromisoformat(start_date.replace("Z", "+00:00"))
            query = query.filter(Call.call_date >= start_dt)
        except:
            pass
    
    if end_date:
        try:
            end_dt = datetime.fromisoformat(end_date.replace("Z", "+00:00"))
            query = query.filter(Call.call_date <= end_dt)
        except:
            pass
    
    calls = query.all()
    call_ids = [call.id for call in calls]
    
    if not call_ids:
        return {
            "total_calls": 0,
            "avg_score": 0,
            "avg_percent": 0,
            "avg_duration": 0,
            "managers_stats": [],
            "parameter_stats": {},
            "time_series": []
        }
    
    latest_eval_subq = db.query(
        Evaluation.call_id,
        func.max(Evaluation.created_at).label('max_created_at')
    ).filter(
        Evaluation.call_id.in_(call_ids)
    ).group_by(Evaluation.call_id).subquery()
    
    latest_evaluations = db.query(Evaluation).join(
        latest_eval_subq,
        (Evaluation.call_id == latest_eval_subq.c.call_id) &
        (Evaluation.created_at == latest_eval_subq.c.max_created_at)
    ).all()
    
    total_calls = len([ev for ev in latest_evaluations if ev.итоговая_оценка is not None])
    
    scores = [ev.итоговая_оценка for ev in latest_evaluations if ev.итоговая_оценка is not None]
    percents = [ev.score_percent for ev in latest_evaluations if ev.score_percent is not None]
    durations = [call.duration for call in calls if call.duration is not None]
    
    avg_score = sum(scores) / len(scores) if scores else 0
    avg_percent = sum(percents) / len(percents) if percents else 0
    avg_duration = sum(durations) / len(durations) if durations else 0
    
    managers_dict = {}
    for call in calls:
        if not call.manager:
            continue
        manager_name = call.manager
        if manager_name not in managers_dict:
            managers_dict[manager_name] = {
                "manager": manager_name,
                "total_calls": 0,
                "avg_score": 0,
                "avg_percent": 0,
                "scores": [],
                "percents": []
            }
        managers_dict[manager_name]["total_calls"] += 1
    
    eval_dict = {ev.call_id: ev for ev in latest_evaluations}
    for call in calls:
        if not call.manager:
            continue
        manager_name = call.manager
        ev = eval_dict.get(call.id)
        if ev and ev.итоговая_оценка is not None:
            managers_dict[manager_name]["scores"].append(ev.итоговая_оценка)
            if ev.score_percent is not None:
                managers_dict[manager_name]["percents"].append(ev.score_percent)
    
    managers_stats = []
    for manager_name, data in managers_dict.items():
        if data["scores"]:
            data["avg_score"] = sum(data["scores"]) / len(data["scores"])
        if data["percents"]:
            data["avg_percent"] = sum(data["percents"]) / len(data["percents"])
        del data["scores"]
        del data["percents"]
        managers_stats.append(data)
    
    managers_stats.sort(key=lambda x: x["avg_percent"] if x["avg_percent"] > 0 else 0, reverse=True)
    
    parameter_stats = {}
    all_keys = ["1", "2", "3.1", "3.2", "3.3", "4.1", "4.2", "4.3", "4.4", "5", "6", "7.1", "7.2"]
    for key in all_keys:
        parameter_stats[key] = {
            "total": 0,
            "max": 0,
            "mid": 0,
            "min": 0,
            "na": 0,
            "avg_score": 0
        }
    
    for ev in latest_evaluations:
        if not ev.scores:
            continue
        for key in all_keys:
            score_data = ev.scores.get(key, {})
            score = score_data.get("score")
            if score == "N/A" or score == "n/a" or score is None:
                parameter_stats[key]["na"] += 1
            elif isinstance(score, (int, float)):
                parameter_stats[key]["total"] += 1
                if score == 1:
                    parameter_stats[key]["max"] += 1
                elif score == 0.5:
                    parameter_stats[key]["mid"] += 1
                elif score == 0:
                    parameter_stats[key]["min"] += 1
    
    for key in all_keys:
        stats = parameter_stats[key]
        if stats["total"] > 0:
            total_score = stats["max"] * 1 + stats["mid"] * 0.5 + stats["min"] * 0
            stats["avg_score"] = total_score / stats["total"]
    
    time_series = []
    for ev in latest_evaluations:
        if ev.created_at:
            date_str = ev.created_at.strftime("%Y-%m-%d")
            time_series.append({
                "date": date_str,
                "score": ev.итоговая_оценка if ev.итоговая_оценка is not None else 0,
                "percent": ev.score_percent if ev.score_percent is not None else 0
            })
    
    time_series.sort(key=lambda x: x["date"])
    
    return {
        "total_calls": total_calls,
        "avg_score": round(avg_score, 2),
        "avg_percent": round(avg_percent, 2),
        "avg_duration": round(avg_duration, 2),
        "managers_stats": managers_stats,
        "parameter_stats": parameter_stats,
        "time_series": time_series
    }

@router.get("/export")
async def export_calls(
    manager: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    db: Session = Depends(get_db)
):
    query = db.query(Call)
    
    if manager:
        query = query.filter(Call.manager == manager)
    
    if start_date:
        try:
            start_dt = datetime.fromisoformat(start_date.replace("Z", "+00:00"))
            query = query.filter(Call.call_date >= start_dt)
        except:
            pass
    
    if end_date:
        try:
            end_dt = datetime.fromisoformat(end_date.replace("Z", "+00:00"))
            query = query.filter(Call.call_date <= end_dt)
        except:
            pass
    
    calls = query.order_by(Call.created_at.desc()).all()
    
    if not calls:
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([
            "Номер", "Дата звонка", "Дата оценки", "Месяц оценки", "Длительность звонка", "Менеджер", "ID звонка",
            "Установление контакта", "Квалификация", "Выявление потребностей", "", "", "Презентация", "", "", "",
            "Работа с возражениями", "Завершение сделки", "Голосовые характеристики", "", "Итоговая оценка", "Итоговый процент"
        ])
        writer.writerow([
            "", "", "", "", "", "", "",
            "1 Приветствие", "2 Первичная квалификация",
            "3.1 Вопросы вторичной квалификации", "3.2 Вопрос о цели обучения", "3.3 Резюмирование потребности",
            "4.1 Презентация обучения из потребности", "4.2 Презентация формата обучения", "4.3 Презентация стоимости", "4.4 Озвучивание информации для пробного",
            "5 Уточнить сомнение клиента",
            "6 Завершение сделки",
            "7.1 Грамотность и формулировки", "7.2 Инициатива за ведение диалога",
            "", ""
        ])
        output.seek(0)
        csv_content = output.getvalue().encode("utf-8-sig")
        return Response(
            content=csv_content,
            media_type="text/csv; charset=utf-8-sig",
            headers={
                "Content-Disposition": f'attachment; filename="calls_export_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv"'
            }
        )
    
    call_ids = [call.id for call in calls]
    
    latest_eval_subq = db.query(
        Evaluation.call_id,
        func.max(Evaluation.created_at).label('max_created_at')
    ).filter(
        Evaluation.call_id.in_(call_ids)
    ).group_by(Evaluation.call_id).subquery()
    
    latest_evaluations = db.query(Evaluation).join(
        latest_eval_subq,
        (Evaluation.call_id == latest_eval_subq.c.call_id) &
        (Evaluation.created_at == latest_eval_subq.c.max_created_at)
    ).order_by(desc(Evaluation.id)).all()
    
    eval_dict = {}
    for ev in latest_evaluations:
        if ev.call_id not in eval_dict:
            eval_dict[ev.call_id] = ev
    
    output = io.StringIO()
    writer = csv.writer(output)
    
    writer.writerow([
        "Номер", "Дата звонка", "Дата оценки", "Месяц оценки", "Длительность звонка", "Менеджер", "ID звонка",
        "Установление контакта", "Квалификация", "Выявление потребностей", "", "", "Презентация", "", "", "",
        "Работа с возражениями", "Завершение сделки", "Голосовые характеристики", "", "Итоговая оценка", "Итоговый процент"
    ])
    
    writer.writerow([
        "", "", "", "", "", "", "",
        "1 Приветствие", "2 Первичная квалификация",
        "3.1 Вопросы вторичной квалификации", "3.2 Вопрос о цели обучения", "3.3 Резюмирование потребности",
        "4.1 Презентация обучения из потребности", "4.2 Презентация формата обучения", "4.3 Презентация стоимости", "4.4 Озвучивание информации для пробного",
        "5 Уточнить сомнение клиента",
        "6 Завершение сделки",
        "7.1 Грамотность и формулировки", "7.2 Инициатива за ведение диалога",
        "", ""
    ])
    
    for idx, call in enumerate(calls, 1):
        latest_evaluation = eval_dict.get(call.id)
        
        if not latest_evaluation:
            continue
        
        scores = latest_evaluation.scores or {}
        evaluation_date = latest_evaluation.created_at
        
        month_names = {
            1: "январь", 2: "февраль", 3: "март", 4: "апрель",
            5: "май", 6: "июнь", 7: "июль", 8: "август",
            9: "сентябрь", 10: "октябрь", 11: "ноябрь", 12: "декабрь"
        }
        month = ""
        if evaluation_date:
            month = month_names.get(evaluation_date.month, "")
        
        row = [
            idx,
            call.call_date.strftime("%Y-%m-%d") if call.call_date else "",
            evaluation_date.strftime("%Y-%m-%d %H:%M:%S") if evaluation_date else "",
            month,
            format_duration(call.duration),
            call.manager or "",
            call.call_identifier or "",
            scores.get("1", {}).get("score", ""),
            scores.get("2", {}).get("score", ""),
            scores.get("3.1", {}).get("score", ""),
            scores.get("3.2", {}).get("score", ""),
            scores.get("3.3", {}).get("score", ""),
            scores.get("4.1", {}).get("score", ""),
            scores.get("4.2", {}).get("score", ""),
            scores.get("4.3", {}).get("score", ""),
            scores.get("4.4", {}).get("score", ""),
            scores.get("5", {}).get("score", ""),
            scores.get("6", {}).get("score", ""),
            scores.get("7.1", {}).get("score", ""),
            scores.get("7.2", {}).get("score", ""),
            latest_evaluation.итоговая_оценка or "",
            latest_evaluation.score_percent if latest_evaluation.score_percent is not None else ""
        ]
        
        writer.writerow(row)
    
    output.seek(0)
    csv_content = output.getvalue().encode("utf-8-sig")
    
    return Response(
        content=csv_content,
        media_type="text/csv; charset=utf-8-sig",
        headers={
            "Content-Disposition": f'attachment; filename="calls_export_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv"'
        }
    )

@router.get("/export/{call_id}")
async def export_call(call_id: int, db: Session = Depends(get_db)):
    call = db.query(Call).filter(Call.id == call_id).first()
    if not call:
        raise HTTPException(status_code=404, detail="Call not found")
    
    latest_evaluation = db.query(Evaluation).filter(
        Evaluation.call_id == call_id
    ).order_by(Evaluation.created_at.desc()).first()
    
    if not latest_evaluation:
        raise HTTPException(status_code=400, detail="No evaluation found for this call")
    
    output = io.StringIO()
    writer = csv.writer(output)
    
    writer.writerow([
        "Номер", "Дата звонка", "Дата оценки", "Месяц оценки", "Длительность звонка", "Менеджер", "ID звонка",
        "Установление контакта", "Квалификация", "Выявление потребностей", "", "", "Презентация", "", "", "",
        "Работа с возражениями", "Завершение сделки", "Голосовые характеристики", "", "Итоговая оценка", "Итоговый процент"
    ])
    
    writer.writerow([
        "", "", "", "", "", "", "",
        "1 Приветствие", "2 Первичная квалификация",
        "3.1 Вопросы вторичной квалификации", "3.2 Вопрос о цели обучения", "3.3 Резюмирование потребности",
        "4.1 Презентация обучения из потребности", "4.2 Презентация формата обучения", "4.3 Презентация стоимости", "4.4 Озвучивание информации для пробного",
        "5 Уточнить сомнение клиента",
        "6 Завершение сделки",
        "7.1 Грамотность и формулировки", "7.2 Инициатива за ведение диалога",
        "", ""
    ])
    
    scores = latest_evaluation.scores or {}
    evaluation_date = latest_evaluation.created_at
    
    month_names = {
        1: "январь", 2: "февраль", 3: "март", 4: "апрель",
        5: "май", 6: "июнь", 7: "июль", 8: "август",
        9: "сентябрь", 10: "октябрь", 11: "ноябрь", 12: "декабрь"
    }
    month = ""
    if evaluation_date:
        month = month_names.get(evaluation_date.month, "")
    
    row = [
        1,
        call.call_date.strftime("%Y-%m-%d") if call.call_date else "",
        evaluation_date.strftime("%Y-%m-%d %H:%M:%S") if evaluation_date else "",
        month,
        format_duration(call.duration),
        call.manager or "",
        call.call_identifier or "",
        scores.get("1", {}).get("score", ""),
        scores.get("2", {}).get("score", ""),
        scores.get("3.1", {}).get("score", ""),
        scores.get("3.2", {}).get("score", ""),
        scores.get("3.3", {}).get("score", ""),
        scores.get("4.1", {}).get("score", ""),
        scores.get("4.2", {}).get("score", ""),
        scores.get("4.3", {}).get("score", ""),
        scores.get("4.4", {}).get("score", ""),
        scores.get("5", {}).get("score", ""),
        scores.get("6", {}).get("score", ""),
        scores.get("7.1", {}).get("score", ""),
        scores.get("7.2", {}).get("score", ""),
        latest_evaluation.итоговая_оценка or "",
        latest_evaluation.score_percent if latest_evaluation.score_percent is not None else ""
    ]
    
    writer.writerow(row)
    
    output.seek(0)
    csv_content = output.getvalue().encode("utf-8-sig")
    
    return Response(
        content=csv_content,
        media_type="text/csv; charset=utf-8-sig",
        headers={
            "Content-Disposition": f'attachment; filename="call_{call_id}_export_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv"'
        }
    )

