import os
import json
import logging
from google import genai
from google.genai import types
from pydantic import BaseModel

# Initialize Gemini client with safe default to avoid crashing when env vars are missing
client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY", "disabled-key"))

class EmergencyAnalysis(BaseModel):
    severity: str  # low, medium, high, critical
    category: str  # fire, flood, medical, accident, weather, etc.
    urgency: str   # immediate, urgent, moderate, low
    confidence: float
    recommendations: list[str]
    estimated_response_time: str

def analyze_emergency_report(description: str, location: str | None = None) -> EmergencyAnalysis:
    """
    Analyze an emergency report using Gemini AI to determine severity, category, and recommendations.
    """
    try:
        system_prompt = (
            "You are an expert emergency response analyst. "
            "Analyze the emergency report and provide structured information to help coordinate response efforts. "
            "Consider the description and location to determine:\n"
            "1. Severity level (low, medium, high, critical)\n"
            "2. Emergency category (fire, flood, medical, accident, weather, security, other)\n"
            "3. Urgency level (immediate, urgent, moderate, low)\n"
            "4. Confidence score (0.0 to 1.0)\n"
            "5. Specific recommendations for response teams\n"
            "6. Estimated response time needed\n\n"
            "Respond with JSON in the specified format."
        )

        content = f"Emergency Description: {description}"
        if location:
            content += f"\nLocation: {location}"

        response = client.models.generate_content(
            model="gemini-2.5-pro",
            contents=[
                types.Content(role="user", parts=[types.Part(text=content)])
            ],
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                response_mime_type="application/json",
                response_schema=EmergencyAnalysis,
            ),
        )

        raw_json = response.text
        logging.info(f"Gemini Analysis Response: {raw_json}")

        if raw_json:
            data = json.loads(raw_json)
            return EmergencyAnalysis(**data)
        else:
            raise ValueError("Empty response from Gemini model")

    except Exception as e:
        logging.error(f"Failed to analyze emergency report: {e}")
        # Return default analysis in case of failure
        return EmergencyAnalysis(
            severity="medium",
            category="other",
            urgency="moderate",
            confidence=0.0,
            recommendations=["Please contact emergency services immediately", "Provide more details if possible"],
            estimated_response_time="15-30 minutes"
        )

def analyze_emergency_image(image_path: str, description: str | None = None) -> str:
    """
    Analyze an emergency-related image using Gemini AI.
    """
    try:
        with open(image_path, "rb") as f:
            image_bytes = f.read()
            
            prompt = "Analyze this emergency-related image and describe what you see. "
            prompt += "Focus on identifying potential hazards, damage, injuries, or emergency situations. "
            prompt += "Provide specific details that would be useful for emergency responders."
            
            if description:
                prompt += f"\n\nContext provided: {description}"

            response = client.models.generate_content(
                model="gemini-2.5-pro",
                contents=[
                    types.Part.from_bytes(
                        data=image_bytes,
                        mime_type="image/jpeg",
                    ),
                    prompt,
                ],
            )

        return response.text if response.text else "Unable to analyze image"

    except Exception as e:
        logging.error(f"Failed to analyze emergency image: {e}")
        return "Image analysis failed. Please contact emergency services directly."

def generate_emergency_summary(reports: list) -> str:
    """
    Generate a summary of multiple emergency reports for dashboard display.
    """
    try:
        if not reports:
            return "No recent emergency reports."

        reports_text = "\n".join([
            f"Report {i+1}: {report.title} - {report.description[:100]}..." 
            for i, report in enumerate(reports[:5])
        ])

        prompt = (
            "Generate a brief summary of the current emergency situation based on these reports. "
            "Highlight the most critical issues and provide an overall assessment:\n\n"
            f"{reports_text}"
        )

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt
        )

        return response.text or "Unable to generate summary"

    except Exception as e:
        logging.error(f"Failed to generate emergency summary: {e}")
        return "Summary generation failed."
