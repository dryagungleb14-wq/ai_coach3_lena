import google.generativeai as genai
import json
import os
import logging
import time
import re

from utils.checklist import get_checklist_prompt
from config import GEMINI_API_KEY, GEMINI_EVALUATION_MODEL

try:
    from google.api_core import exceptions as google_exceptions
except ImportError:
    google_exceptions = None

genai.configure(api_key=GEMINI_API_KEY)

logger = logging.getLogger(__name__)

def normalize_scores(scores_data: dict) -> dict:
    valid_scores = {0, 0.5, 1}
    
    for key, value in scores_data.items():
        if isinstance(value, dict):
            if "score" in value:
                score = value["score"]
                if score == "N/A" or score == "n/a" or score is None:
                    value["score"] = "N/A"
                elif isinstance(score, (int, float)):
                    if score not in valid_scores:
                        closest = min(valid_scores, key=lambda x: abs(x - score))
                        logger.warning(f"Нормализация балла {key}: {score} -> {closest}")
                        value["score"] = closest
    
    return scores_data

def extract_special_circumstances(scores_data: dict) -> dict:
    special = scores_data.get("special_circumstances")
    if not isinstance(special, dict):
        return {}
    result = {
        "client_refused_questions": bool(special.get("client_refused_questions")),
        "no_trainer": bool(special.get("no_trainer")),
        "no_trainer_time": bool(special.get("no_trainer_time")),
        "trainer_search": bool(special.get("trainer_search")),
        "parent_child_discussion": bool(special.get("parent_child_discussion")),
        "conversation_interrupted": bool(special.get("conversation_interrupted")),
        "technical_issues": bool(special.get("technical_issues")),
        "client_reaction": bool(special.get("client_reaction")),
        "no_lesson_scheduled": bool(special.get("no_lesson_scheduled")),
    }
    summary = special.get("summary")
    if isinstance(summary, str) and summary.strip():
        result["summary"] = summary.strip()
    return result

def _evaluate_transcription_once(transcription: str) -> dict:
    if not transcription or len(transcription.strip()) == 0:
        raise ValueError("Транскрипция пустая. Невозможно провести оценку.")
    
    prompt = get_checklist_prompt()
    full_prompt = f"{prompt}\n\nРасшифровка звонка:\n\n{transcription}\n\nОцени звонок по чек-листу и верни JSON."
    
    special_circumstances = {}
    try:
        model = genai.GenerativeModel(GEMINI_EVALUATION_MODEL)
        response = model.generate_content(
            full_prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=0,
                top_p=1.0,
                top_k=1,
                max_output_tokens=8192,
                response_mime_type="application/json"
            )
        )
        
        if not response:
            raise Exception("Gemini API вернул пустой ответ при оценке")
        
        if not hasattr(response, 'text') or response.text is None:
            raise Exception("Gemini API не вернул текст оценки")
        
        response_text = response.text.strip()
        logger.info(f"Ответ модели получен, длина {len(response_text)} символов")
        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0].strip()
        elif "```" in response_text:
            response_text = response_text.split("```")[1].split("```")[0].strip()
        
        try:
            scores_data = json.loads(response_text)
        except json.JSONDecodeError as e:
            logger.error(f"Ошибка парсинга JSON оценки: {e}. Длина ответа: {len(response_text)}")
            raise Exception("Не удалось распарсить JSON ответ от модели оценки")
        
        if not scores_data or not isinstance(scores_data, dict) or len(scores_data) == 0:
            raise Exception("Модель вернула пустой словарь оценок")
        
        scores_data = normalize_scores(scores_data)
        special_circumstances = extract_special_circumstances(scores_data)
        
        logger.info(f"Итоговые баллы: {json.dumps({k: v.get('score', 'N/A') for k, v in scores_data.items()}, ensure_ascii=False)}")
        
    except Exception as e:
        error_msg = str(e)
        is_resource_exhausted = False
        
        if google_exceptions and isinstance(e, google_exceptions.ResourceExhausted):
            is_resource_exhausted = True
        elif "ResourceExhausted" in str(type(e)) or "429" in error_msg or "quota" in error_msg.lower():
            is_resource_exhausted = True
        
        if is_resource_exhausted:
            if "limit: 0" in error_msg or "free_tier" in error_msg.lower():
                user_message = f"Модель {GEMINI_EVALUATION_MODEL} недоступна на бесплатном тарифе Gemini API. Пожалуйста, используйте другую модель (например, gemini-1.5-flash) или перейдите на платный тариф."
            elif "quota" in error_msg.lower() or "limit" in error_msg.lower():
                user_message = f"Превышена квота Gemini API. {error_msg}"
            else:
                user_message = f"Ошибка квоты Gemini API: {error_msg}"
            logger.error(f"Ошибка при выполнении оценки через Gemini (429): {e}")
            import traceback
            logger.error(traceback.format_exc())
            raise Exception(user_message) from e
        
        logger.error(f"Ошибка при оценке: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise
    
    all_keys = ["1", "2", "3.1", "3.2", "3.3", "4.1", "4.2", "4.3", "4.4", "5", "6", "7.1", "7.2"]
    total_score = 0.0
    max_possible_score = 0.0
    
    for key in all_keys:
        score_data = scores_data.get(key, {})
        score = score_data.get("score", "N/A")
        
        if score == "N/A" or score == "n/a" or score is None:
            continue
        
        if isinstance(score, (int, float)):
            total_score += score
            max_possible_score += 1.0
    
    if max_possible_score == 0:
        score_percent = 0.0
    else:
        score_percent = (total_score / max_possible_score) * 100.0
    
    comments = {}
    for key, value in scores_data.items():
        if isinstance(value, dict) and "comment" in value:
            comments[key] = value["comment"]
    
    result = {
        "scores": scores_data,
        "итоговая_оценка": total_score,
        "max_score": max_possible_score,
        "score_percent": score_percent,
        "нарушения": False,
        "комментарии": json.dumps(comments, ensure_ascii=False),
        "special_circumstances": special_circumstances
    }
    
    logger.info(f"Итоговая оценка: {total_score} из {max_possible_score} возможных ({score_percent:.1f}%)")
    
    return result

def _extract_retry_after(error_msg: str) -> float:
    retry_match = re.search(r"retry in ([\d.]+)s", error_msg, re.IGNORECASE)
    if retry_match:
        return float(retry_match.group(1))
    return None

def evaluate_transcription(transcription: str, max_retries: int = 5) -> dict:
    last_exception = None
    
    for attempt in range(1, max_retries + 1):
        try:
            logger.info(f"Попытка оценки {attempt}/{max_retries}")
            return _evaluate_transcription_once(transcription)
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
                logger.warning(f"Ошибка оценки (попытка {attempt}/{max_retries}): {e}. Повтор через {wait_time} сек...")
                time.sleep(wait_time)
            else:
                logger.error(f"Все попытки оценки исчерпаны после {max_retries} попыток")
    
    raise Exception(f"Не удалось выполнить оценку после {max_retries} попыток: {str(last_exception)}") from last_exception

