import google.generativeai as genai
import os
import logging
import time
import re
from dotenv import load_dotenv
from config import GEMINI_API_KEY, GEMINI_TRANSCRIPTION_MODEL

try:
    from google.api_core import exceptions as google_exceptions
except ImportError:
    google_exceptions = None

load_dotenv()

logger = logging.getLogger(__name__)

genai.configure(api_key=GEMINI_API_KEY)

def _transcribe_audio_once(audio_path: str) -> str:
    logger.info(f"Начало транскрипции файла: {audio_path}")
    
    if not os.path.exists(audio_path):
        raise FileNotFoundError(f"Аудио файл не найден: {audio_path}")
    
    try:
        model = genai.GenerativeModel(GEMINI_TRANSCRIPTION_MODEL)
        
        audio_file = genai.upload_file(path=audio_path)
        logger.info(f"Аудио файл загружен в Gemini: {audio_file.uri}")
        
        max_wait_time = 300
        wait_interval = 2
        elapsed_time = 0
        max_checks = max_wait_time // wait_interval
        
        check_count = 0
        while audio_file.state.name == "PROCESSING":
            if check_count >= max_checks:
                raise Exception(f"Таймаут ожидания обработки файла в Gemini (превышено {max_wait_time} секунд)")
            time.sleep(wait_interval)
            elapsed_time += wait_interval
            check_count += 1
            audio_file = genai.get_file(audio_file.name)
            if check_count % 10 == 0:
                logger.info(f"Ожидание обработки файла в Gemini: {elapsed_time}/{max_wait_time} секунд")
        
        if audio_file.state.name == "FAILED":
            raise Exception(f"Ошибка загрузки файла в Gemini: {audio_file.state}")
        
        logger.info("Отправка запроса на транскрипцию в Gemini API...")
        
        prompt = "Транскрибируй этот аудио файл на русском языке. Верни только текст без дополнительных комментариев."
        
        response = model.generate_content(
            [prompt, audio_file],
            generation_config=genai.types.GenerationConfig(
                temperature=0,
                response_mime_type="text/plain"
            )
        )
        
        if not response:
            raise Exception("Gemini API вернул пустой ответ")
        
        if not hasattr(response, 'text') or response.text is None:
            raise Exception("Gemini API не вернул текст транскрипции")
        
        transcription = response.text.strip()
        
        if not transcription or len(transcription) == 0:
            raise Exception("Транскрипция пустая. Возможно, аудио файл не содержит речи или произошла ошибка при обработке.")
        
        try:
            genai.delete_file(audio_file.name)
        except Exception as e:
            logger.warning(f"Не удалось удалить временный файл из Gemini: {e}")
        
        logger.info(f"Транскрипция завершена успешно, длина текста: {len(transcription)} символов")
        
        return transcription
        
    except Exception as e:
        error_msg = str(e)
        is_resource_exhausted = False
        
        if google_exceptions and isinstance(e, google_exceptions.ResourceExhausted):
            is_resource_exhausted = True
        elif "ResourceExhausted" in str(type(e)) or "429" in error_msg or "quota" in error_msg.lower():
            is_resource_exhausted = True
        
        if is_resource_exhausted:
            if "limit: 0" in error_msg or "free_tier" in error_msg.lower():
                user_message = f"Модель {GEMINI_TRANSCRIPTION_MODEL} недоступна на бесплатном тарифе Gemini API. Пожалуйста, используйте другую модель (например, gemini-1.5-flash) или перейдите на платный тариф."
            elif "quota" in error_msg.lower() or "limit" in error_msg.lower():
                user_message = f"Превышена квота Gemini API. {error_msg}"
            else:
                user_message = f"Ошибка квоты Gemini API: {error_msg}"
            logger.error(f"Ошибка при выполнении транскрипции через Gemini (429): {e}")
            import traceback
            logger.error(traceback.format_exc())
            raise Exception(user_message) from e
        
        logger.error(f"Ошибка при выполнении транскрипции через Gemini: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise

def _extract_retry_after(error_msg: str) -> float:
    retry_match = re.search(r"retry in ([\d.]+)s", error_msg, re.IGNORECASE)
    if retry_match:
        return float(retry_match.group(1))
    return None

def transcribe_audio(audio_path: str, max_retries: int = 5) -> str:
    last_exception = None
    
    for attempt in range(1, max_retries + 1):
        try:
            logger.info(f"Попытка транскрипции {attempt}/{max_retries} для файла {audio_path}")
            return _transcribe_audio_once(audio_path)
        except Exception as e:
            last_exception = e
            error_msg = str(e)
            
            is_quota_error = False
            if google_exceptions and isinstance(e, google_exceptions.ResourceExhausted):
                is_quota_error = True
            elif "ResourceExhausted" in str(type(e)) or "429" in error_msg or "quota" in error_msg.lower():
                is_quota_error = True
            
            if is_quota_error:
                if "limit: 0" in error_msg or "free_tier" in error_msg.lower():
                    logger.error(f"Модель недоступна на free tier, повторная попытка не поможет: {e}")
                    raise
                
                retry_after = _extract_retry_after(error_msg)
                if retry_after and attempt < max_retries:
                    wait_time = retry_after + 1
                    logger.warning(f"Ошибка квоты API (попытка {attempt}/{max_retries}): {e}. Повтор через {wait_time:.1f} сек...")
                    time.sleep(wait_time)
                    continue
                else:
                    logger.error(f"Ошибка квоты API, повторная попытка не поможет: {e}")
                    raise
            
            if attempt < max_retries:
                wait_time = 2 ** attempt
                logger.warning(f"Ошибка транскрипции (попытка {attempt}/{max_retries}): {e}. Повтор через {wait_time} сек...")
                time.sleep(wait_time)
            else:
                logger.error(f"Все попытки транскрипции исчерпаны после {max_retries} попыток")
    
    raise Exception(f"Не удалось выполнить транскрипцию после {max_retries} попыток: {str(last_exception)}") from last_exception
