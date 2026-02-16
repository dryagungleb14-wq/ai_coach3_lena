import requests
import os
import time
import logging
from datetime import datetime, timedelta
from typing import Optional

from config import (
    TELPHIN_APP_ID,
    TELPHIN_APP_SECRET,
    TELPHIN_API_BASE,
    TELPHIN_MIN_DURATION,
    TELPHIN_DELAY_BETWEEN_CALLS,
)
from models import Call, TelphinSync, TelphinExtension, SessionLocal

logger = logging.getLogger(__name__)

_token_cache = {"token": None, "expires_at": 0}
_cancel_sync_flag = {"cancel": False}


def _get_token() -> str:
    now = time.time()
    if _token_cache["token"] and now < _token_cache["expires_at"]:
        return _token_cache["token"]

    if not TELPHIN_APP_ID or not TELPHIN_APP_SECRET:
        raise ValueError("TELPHIN_APP_ID и TELPHIN_APP_SECRET не заданы в переменных окружения")

    resp = requests.post(
        f"{TELPHIN_API_BASE}/oauth/token",
        data={
            "grant_type": "client_credentials",
            "client_id": TELPHIN_APP_ID,
            "client_secret": TELPHIN_APP_SECRET,
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        timeout=15,
    )
    resp.raise_for_status()
    data = resp.json()

    _token_cache["token"] = data["access_token"]
    _token_cache["expires_at"] = now + 3500

    return _token_cache["token"]


def request_cancel_sync():
    """Установить флаг отмены синхронизации"""
    _cancel_sync_flag["cancel"] = True
    logger.info("Запрошена отмена синхронизации")


def reset_cancel_flag():
    """Сбросить флаг отмены"""
    _cancel_sync_flag["cancel"] = False


def is_sync_cancelled() -> bool:
    """Проверить, запрошена ли отмена"""
    return _cancel_sync_flag["cancel"]


def _api_get(path: str):
    token = _get_token()
    resp = requests.get(
        f"{TELPHIN_API_BASE}/api/ver1.0/{path}",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()


def get_client_id() -> str:
    data = _api_get("user/")
    return data["client_id"]


def get_extensions(client_id: str) -> list:
    data = _api_get(f"client/{client_id}/extension/")
    return data if isinstance(data, list) else []


def fetch_call_history(
    client_id: str,
    start_date: datetime,
    end_date: datetime,
) -> list:
    start_str = start_date.strftime("%Y-%m-%d %H:%M:%S")
    end_str = end_date.strftime("%Y-%m-%d %H:%M:%S")

    path = (
        f"client/{client_id}/call_history/"
        f"?start_datetime={requests.utils.quote(start_str)}"
        f"&end_datetime={requests.utils.quote(end_str)}"
        f"&order=desc"
    )
    data = _api_get(path)
    return data.get("call_history", [])


def get_recording_url(extension_id: str, record_uuid: str) -> Optional[str]:
    try:
        data = _api_get(f"extension/{extension_id}/record/{record_uuid}/storage_url/")
        return data.get("record_url")
    except Exception as e:
        logger.warning(f"Не удалось получить URL записи {record_uuid}: {e}")
        return None


def download_recording(url: str, dest_path: str) -> bool:
    try:
        resp = requests.get(url, stream=True, timeout=120)
        resp.raise_for_status()
        with open(dest_path, "wb") as f:
            for chunk in resp.iter_content(chunk_size=8192):
                f.write(chunk)
        return True
    except Exception as e:
        logger.error(f"Ошибка скачивания записи: {e}")
        return False


def _find_record_uuid(call_entry: dict) -> tuple[Optional[str], Optional[str]]:
    for cdr in call_entry.get("cdr", []):
        record_uuid = cdr.get("record_uuid")
        if record_uuid:
            ext_id = str(cdr.get("extension_id", ""))
            if not ext_id:
                ext_name = cdr.get("extension_name", "")
                ext_id = ext_name.split("*")[0] if "*" in ext_name else ""
            return record_uuid, ext_id
    return None, None


def _call_already_imported(db, call_uuid: str) -> bool:
    return db.query(Call).filter(Call.call_identifier == call_uuid).first() is not None


def sync_calls(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    min_duration: Optional[int] = None,
) -> dict:
    from api.routes import analyze_in_background

    if min_duration is None:
        min_duration = TELPHIN_MIN_DURATION
    if end_date is None:
        end_date = datetime.utcnow()
    if start_date is None:
        start_date = end_date - timedelta(days=1)

    db = SessionLocal()
    sync_record = TelphinSync(
        filter_start=start_date,
        filter_end=end_date,
        filter_min_duration=min_duration,
    )
    db.add(sync_record)
    db.commit()
    db.refresh(sync_record)
    sync_id = sync_record.id

    try:
        monitored = db.query(TelphinExtension).filter(TelphinExtension.is_monitored == True).all()
        monitored_ids = set()
        ext_to_manager = {}
        for rec in monitored:
            monitored_ids.add(rec.extension_id)
            if rec.extension_name:
                monitored_ids.add(rec.extension_name)
            name = (rec.manager_name or rec.extension_name or rec.extension_id or "").strip()
            ext_to_manager[rec.extension_id] = name or rec.extension_id
            if rec.extension_name:
                ext_to_manager[rec.extension_name] = name or rec.extension_name
        if not monitored_ids:
            sync_record.status = "completed"
            sync_record.calls_found = 0
            sync_record.calls_imported = 0
            sync_record.calls_skipped = 0
            sync_record.finished_at = datetime.utcnow()
            db.commit()
            logger.info("Telphin sync: нет выбранных операторов, синхронизация пропущена")
            return {"sync_id": sync_id, "status": "completed", "calls_found": 0, "calls_imported": 0, "calls_skipped": 0}

        client_id = get_client_id()
        logger.info(f"Telphin client_id: {client_id}")

        calls = fetch_call_history(client_id, start_date, end_date)
        logger.info(f"Telphin: получено {len(calls)} записей из истории")

        # DEBUG: показываем отслеживаемые добавочные и статистику
        if calls:
            logger.info(f"DEBUG: Отслеживаемые добавочные: {monitored_ids}")
            logger.info(f"DEBUG: Показываем первые 10 звонков из истории:")
            for i, call in enumerate(calls[:10]):
                logger.info(f"  #{i+1}: from={call.get('from_username')}, to={call.get('to_username')}, duration={call.get('duration')}s, result={call.get('result')}")

            # Показываем звонки наших операторов (до фильтрации по длительности)
            our_calls = [
                c for c in calls
                if c.get("from_username") in monitored_ids or c.get("to_username") in monitored_ids
            ]
            logger.info(f"DEBUG: Найдено {len(our_calls)} звонков с отслеживаемых добавочных (без учета длительности/статуса)")
            for i, call in enumerate(our_calls[:5]):
                logger.info(f"  Наш звонок #{i+1}: from={call.get('from_username')}, to={call.get('to_username')}, duration={call.get('duration')}s, result={call.get('result')}")

        filtered = [
            c for c in calls
            if c.get("duration", 0) >= min_duration
            and c.get("result") in ("ANSWER", "bridged")
            and (c.get("from_username") in monitored_ids or c.get("to_username") in monitored_ids)
        ]
        logger.info(f"Telphin: после фильтрации (>{min_duration}с, bridged/ANSWER, операторы): {len(filtered)}")

        # Ограничение на максимальное количество звонков за одну синхронизацию
        MAX_CALLS_PER_SYNC = 20
        if len(filtered) > MAX_CALLS_PER_SYNC:
            logger.warning(f"Найдено {len(filtered)} звонков, но будет импортировано только {MAX_CALLS_PER_SYNC}. Уменьшите диапазон дат для полной синхронизации.")
            filtered = filtered[:MAX_CALLS_PER_SYNC]

        sync_record.calls_found = len(filtered)
        db.commit()

        imported = 0
        skipped = 0
        backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        uploads_dir = os.path.join(backend_dir, "uploads")
        os.makedirs(uploads_dir, exist_ok=True)

        # Сброс флага отмены перед началом
        reset_cancel_flag()

        for entry in filtered:
            # Проверка флага отмены
            if is_sync_cancelled():
                logger.info(f"Синхронизация отменена пользователем. Обработано {imported} из {len(filtered)} звонков")
                sync_record.status = "cancelled"
                sync_record.error_message = "Отменено пользователем"
                sync_record.calls_imported = imported
                sync_record.calls_skipped = skipped
                sync_record.finished_at = datetime.utcnow()
                db.commit()
                return {"sync_id": sync_id, "status": "cancelled", "calls_found": len(filtered), "calls_imported": imported, "calls_skipped": skipped}

            call_uuid = entry.get("call_uuid", "")

            if _call_already_imported(db, call_uuid):
                skipped += 1
                continue

            record_uuid, ext_id = _find_record_uuid(entry)
            if not record_uuid or not ext_id:
                logger.info(f"Нет записи для звонка {call_uuid}, пропускаем")
                skipped += 1
                continue

            rec_url = get_recording_url(ext_id, record_uuid)
            if not rec_url:
                skipped += 1
                continue

            file_path = os.path.join(uploads_dir, f"telphin_{call_uuid}.wav")
            if not download_recording(rec_url, file_path):
                skipped += 1
                continue

            from_user = entry.get("from_username", "")
            to_user = entry.get("to_username", "")
            flow = entry.get("flow", "")
            duration = entry.get("duration", 0)

            init_time = entry.get("init_time_gmt")
            call_date = None
            if init_time:
                try:
                    call_date = datetime.strptime(init_time, "%Y-%m-%dT%H:%M:%S")
                except Exception:
                    try:
                        call_date = datetime.fromisoformat(init_time.replace("Z", "+00:00"))
                    except Exception:
                        pass

            ext_key = from_user if flow == "out" else to_user
            manager_name = ext_to_manager.get(ext_key) or ext_key
            filename = f"telphin_{flow}_{from_user}_to_{to_user}_{call_uuid[:8]}.wav"

            call = Call(
                filename=filename,
                audio_url=file_path,
                manager=manager_name,
                call_date=call_date,
                call_identifier=call_uuid,
                duration=float(duration),
                status="pending",
            )
            db.add(call)
            db.commit()
            db.refresh(call)

            try:
                analyze_in_background(call.id, file_path)
            except Exception as e:
                logger.error(f"Ошибка анализа звонка {call.id}: {e}")

            imported += 1

            # Обновляем прогресс после каждого импортированного звонка
            sync_record.calls_imported = imported
            sync_record.calls_skipped = skipped
            db.commit()

            if TELPHIN_DELAY_BETWEEN_CALLS > 0:
                time.sleep(TELPHIN_DELAY_BETWEEN_CALLS)

        sync_record.status = "completed"
        sync_record.calls_imported = imported
        sync_record.calls_skipped = skipped
        sync_record.finished_at = datetime.utcnow()
        db.commit()

        logger.info(f"Telphin sync завершена: импортировано {imported}, пропущено {skipped}")

        return {
            "sync_id": sync_id,
            "status": "completed",
            "calls_found": len(filtered),
            "calls_imported": imported,
            "calls_skipped": skipped,
        }

    except Exception as e:
        logger.error(f"Ошибка синхронизации Telphin: {e}")
        sync_record.status = "failed"
        sync_record.error_message = str(e)
        sync_record.finished_at = datetime.utcnow()
        db.commit()
        raise
    finally:
        db.close()
