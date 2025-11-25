import google.generativeai as genai
import json
import os
import logging
import time

from utils.checklist import get_checklist_prompt
from config import GEMINI_API_KEY, GEMINI_EVALUATION_MODEL

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

def _evaluate_transcription_once(transcription: str) -> dict:
    if not transcription or len(transcription.strip()) == 0:
        raise ValueError("Транскрипция пустая. Невозможно провести оценку.")
    
    prompt = get_checklist_prompt()
    full_prompt = f"{prompt}\n\nРасшифровка звонка:\n\n{transcription}\n\nОцени звонок по чек-листу и верни JSON."
    
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
        
        logger.info(f"Ответ модели (первые 300 символов): {response_text[:300]}")
        
        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0].strip()
        elif "```" in response_text:
            response_text = response_text.split("```")[1].split("```")[0].strip()
        
        try:
            scores_data = json.loads(response_text)
        except json.JSONDecodeError as e:
            logger.error(f"Ошибка парсинга JSON: {e}")
            logger.error(f"Полный ответ модели: {response_text}")
            raise Exception(f"Не удалось распарсить JSON ответ от модели. Ответ: {response_text[:500]}")
        
        if not scores_data or not isinstance(scores_data, dict) or len(scores_data) == 0:
            raise Exception("Модель вернула пустой словарь оценок")
        
        scores_data = normalize_scores(scores_data)
        
        logger.info(f"Итоговые баллы: {json.dumps({k: v.get('score', 'N/A') for k, v in scores_data.items()}, ensure_ascii=False)}")
        
    except Exception as e:
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
        "комментарии": json.dumps(comments, ensure_ascii=False)
    }
    
    logger.info(f"Итоговая оценка: {total_score} из {max_possible_score} возможных ({score_percent:.1f}%)")
    
    return result

def evaluate_transcription(transcription: str, max_retries: int = 3) -> dict:
    last_exception = None
    
    for attempt in range(1, max_retries + 1):
        try:
            logger.info(f"Попытка оценки {attempt}/{max_retries}")
            return _evaluate_transcription_once(transcription)
        except Exception as e:
            last_exception = e
            error_msg = str(e)
            
            if "quota" in error_msg.lower() or "429" in error_msg or "ResourceExhausted" in str(type(e)):
                logger.error(f"Ошибка квоты API, повторная попытка не поможет: {e}")
                raise
            
            if attempt < max_retries:
                wait_time = 2 ** attempt
                logger.warning(f"Ошибка оценки (попытка {attempt}/{max_retries}): {e}. Повтор через {wait_time} сек...")
                time.sleep(wait_time)
            else:
                logger.error(f"Все попытки оценки исчерпаны после {max_retries} попыток")
    
    raise Exception(f"Не удалось выполнить оценку после {max_retries} попыток: {str(last_exception)}") from last_exception

