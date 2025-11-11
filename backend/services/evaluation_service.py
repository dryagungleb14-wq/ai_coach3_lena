import google.generativeai as genai
import json
import os
import logging

from utils.checklist import get_checklist_prompt
from config import GEMINI_API_KEY, GEMINI_EVALUATION_MODEL

genai.configure(api_key=GEMINI_API_KEY)

logger = logging.getLogger(__name__)

def normalize_scores(scores_data: dict) -> dict:
    valid_scores = {0, 5, 10}
    
    for key, value in scores_data.items():
        if isinstance(value, dict):
            if "score" in value:
                score = value["score"]
                if isinstance(score, (int, float)):
                    if score not in valid_scores:
                        closest = min(valid_scores, key=lambda x: abs(x - score))
                        logger.warning(f"Нормализация балла {key}: {score} -> {closest}")
                        value["score"] = closest
            elif "violation" in value and key == "9":
                continue
    
    return scores_data

def evaluate_transcription(transcription: str) -> dict:
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
        
        logger.info(f"Итоговые баллы: {json.dumps({k: v.get('score', v.get('violation', 'N/A')) for k, v in scores_data.items()}, ensure_ascii=False)}")
        
    except Exception as e:
        logger.error(f"Ошибка при оценке: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise
    
    violations = scores_data.get("9", {}).get("violation", False)
    
    total_score = 0
    if not violations:
        for key in ["1.1", "1.2", "2.1", "2.2", "3.1", "3.2", "4.1", "4.2", "5.1", "5.2", "6", "7", "8"]:
            score = scores_data.get(key, {}).get("score", 0)
            total_score += score
    else:
        total_score = 0
    
    comments = {}
    for key, value in scores_data.items():
        if isinstance(value, dict) and "comment" in value:
            comments[key] = value["comment"]
    
    result = {
        "scores": scores_data,
        "итоговая_оценка": total_score,
        "нарушения": violations,
        "комментарии": json.dumps(comments, ensure_ascii=False)
    }
    
    logger.info(f"Итоговая оценка: {total_score}")
    
    return result

