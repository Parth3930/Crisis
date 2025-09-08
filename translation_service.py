import os
import json
import logging
from google import genai
from google.genai import types
from pydantic import BaseModel

# Initialize Gemini client for translation (fallback key if not provided)
client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY", "disabled-key"))

class TranslationResponse(BaseModel):
    translated_text: str
    detected_language: str
    confidence: float

SUPPORTED_LANGUAGES = {
    'en': 'English',
    'es': 'Spanish', 
    'fr': 'French',
    'de': 'German',
    'it': 'Italian',
    'pt': 'Portuguese',
    'ru': 'Russian',
    'ja': 'Japanese',
    'ko': 'Korean',
    'zh': 'Chinese',
    'ar': 'Arabic',
    'hi': 'Hindi',
    'ur': 'Urdu',
    'bn': 'Bengali'
}

def translate_emergency_text(text: str, target_language: str = 'en') -> TranslationResponse:
    """Translate emergency text to target language using Gemini AI"""
    try:
        system_prompt = f"""
You are a professional emergency services translator. Translate the following emergency report text to {SUPPORTED_LANGUAGES.get(target_language, target_language)}.

Requirements:
- Maintain the urgency and critical nature of the message
- Preserve all important details (locations, numbers, names)
- Use appropriate emergency terminology
- Detect the original language
- Provide confidence score (0.0 to 1.0)

Respond with JSON in the specified format.
        """

        response = client.models.generate_content(
            model="gemini-2.5-pro",
            contents=[
                types.Content(role="user", parts=[types.Part(text=f"Translate this emergency text: {text}")])
            ],
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                response_mime_type="application/json",
                response_schema=TranslationResponse,
            ),
        )

        raw_json = response.text
        if raw_json:
            data = json.loads(raw_json)
            return TranslationResponse(**data)
        else:
            raise ValueError("Empty response from translation model")

    except Exception as e:
        logging.error(f"Translation failed: {e}")
        # Return fallback response
        return TranslationResponse(
            translated_text=text,
            detected_language="unknown",
            confidence=0.0
        )

def get_multilingual_emergency_message(report_title: str, report_description: str) -> dict:
    """Generate emergency message in multiple languages"""
    base_text = f"EMERGENCY: {report_title}. Details: {report_description}"
    
    translations = {}
    priority_languages = ['es', 'fr', 'zh', 'ar', 'hi']  # High-impact international languages
    
    for lang_code in priority_languages:
        try:
            translation = translate_emergency_text(base_text, lang_code)
            translations[lang_code] = {
                'language': SUPPORTED_LANGUAGES[lang_code],
                'text': translation.translated_text,
                'confidence': translation.confidence
            }
        except Exception as e:
            logging.error(f"Failed to translate to {lang_code}: {e}")
            
    return translations

def detect_and_translate_user_input(text: str) -> dict:
    """Detect language and translate user input to English for processing"""
    try:
        # First detect language and translate to English
        english_translation = translate_emergency_text(text, 'en')
        
        return {
            'original_text': text,
            'english_text': english_translation.translated_text,
            'detected_language': english_translation.detected_language,
            'confidence': english_translation.confidence
        }
        
    except Exception as e:
        logging.error(f"Language detection failed: {e}")
        return {
            'original_text': text,
            'english_text': text,
            'detected_language': 'en',
            'confidence': 1.0
        }