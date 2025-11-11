import google.generativeai as genai
import os
import logging
import time
from dotenv import load_dotenv
from config import GEMINI_API_KEY, GEMINI_TRANSCRIPTION_MODEL

try:
    from google.api_core import exceptions as google_exceptions
except ImportError:
    google_exceptions = None

load_dotenv()

logger = logging.getLogger(__name__)

genai.configure(api_key=GEMINI_API_KEY)

def transcribe_audio(audio_path: str) -> str:
    logger.info(f"Начало транскрипции файла: {audio_path}")
    
    if not os.path.exists(audio_path):
        raise FileNotFoundError(f"Аудио файл не найден: {audio_path}")
    
    try:
        model = genai.GenerativeModel(GEMINI_TRANSCRIPTION_MODEL)
        
        audio_file = genai.upload_file(path=audio_path)
        logger.info(f"Аудио файл загружен в Gemini: {audio_file.uri}")
        
        while audio_file.state.name == "PROCESSING":
            time.sleep(2)
            audio_file = genai.get_file(audio_file.name)
        
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
                user_message = "Модель недоступна на бесплатном тарифе Gemini API. Пожалуйста, используйте другую модель или перейдите на платный тариф."
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
