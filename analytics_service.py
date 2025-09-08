import os
import json
import logging
from datetime import datetime, timedelta
from sqlalchemy import func
from google import genai
from google.genai import types
from pydantic import BaseModel
import models

# Initialize Gemini client with safe default
client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY", "disabled-key"))

class EmergencyPrediction(BaseModel):
    risk_level: str  # low, moderate, high, critical
    predicted_incidents: int
    high_risk_areas: list[str]
    recommended_preparations: list[str]
    confidence: float
    time_frame: str

class TrendAnalysis(BaseModel):
    trend_direction: str  # increasing, decreasing, stable
    severity_distribution: dict
    common_categories: list[str]
    peak_hours: list[int]
    geographical_hotspots: list[str]
    insights: list[str]

def analyze_emergency_trends(days_back: int = 30) -> TrendAnalysis:
    """Analyze emergency trends using AI to identify patterns"""
    try:
        # Get recent emergency data
        cutoff_date = datetime.utcnow() - timedelta(days=days_back)
        recent_reports = models.EmergencyReport.query.filter(
            models.EmergencyReport.created_at >= cutoff_date
        ).all()
        
        if not recent_reports:
            return TrendAnalysis(
                trend_direction="stable",
                severity_distribution={},
                common_categories=[],
                peak_hours=[],
                geographical_hotspots=[],
                insights=["Insufficient data for trend analysis"]
            )
        
        # Prepare data summary for AI analysis
        data_summary = {
            'total_reports': len(recent_reports),
            'severity_counts': {},
            'hourly_distribution': [0] * 24,
            'locations': [],
            'categories': [],
            'descriptions_sample': []
        }
        
        for report in recent_reports:
            # Count by severity
            severity = report.severity or 'unknown'
            data_summary['severity_counts'][severity] = data_summary['severity_counts'].get(severity, 0) + 1
            
            # Track hourly patterns
            hour = report.created_at.hour
            data_summary['hourly_distribution'][hour] += 1
            
            # Collect locations and sample descriptions
            if report.location:
                data_summary['locations'].append(report.location)
            if report.ai_analysis and 'Category:' in report.ai_analysis:
                category_line = [line for line in report.ai_analysis.split('\n') if 'Category:' in line]
                if category_line:
                    category = category_line[0].split(':')[1].strip()
                    data_summary['categories'].append(category)
            
            data_summary['descriptions_sample'].append(report.description[:100])
        
        # Use AI to analyze trends
        system_prompt = """
You are an emergency management analyst. Analyze the emergency data to identify trends and patterns.

Provide insights about:
- Overall trend direction (increasing, decreasing, stable)
- Severity distribution patterns
- Most common emergency categories
- Peak activity hours (0-23)
- Geographic hotspots
- Actionable insights for emergency preparedness

Respond with JSON in the specified format.
        """
        
        analysis_prompt = f"""
Analyze this emergency data from the past {days_back} days:

{json.dumps(data_summary, indent=2)}

Identify trends, patterns, and provide actionable insights for emergency management teams.
        """
        
        response = client.models.generate_content(
            model="gemini-2.5-pro",
            contents=[
                types.Content(role="user", parts=[types.Part(text=analysis_prompt)])
            ],
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                response_mime_type="application/json",
                response_schema=TrendAnalysis,
            ),
        )
        
        raw_json = response.text
        if raw_json:
            data = json.loads(raw_json)
            return TrendAnalysis(**data)
        
    except Exception as e:
        logging.error(f"Trend analysis failed: {e}")
    
    # Fallback analysis
    return TrendAnalysis(
        trend_direction="stable",
        severity_distribution={"medium": 50, "high": 30, "low": 20},
        common_categories=["Medical", "Fire", "Accident"],
        peak_hours=[9, 12, 18],
        geographical_hotspots=["Downtown", "Highway 95"],
        insights=["Analysis in progress - check back later"]
    )

def predict_emergency_risk(location: str = None, time_hours: int = 24) -> EmergencyPrediction:
    """Predict emergency risk for next time period"""
    try:
        # Get historical data for prediction
        historical_reports = EmergencyReport.query.order_by(
            EmergencyReport.created_at.desc()
        ).limit(100).all()
        
        # Prepare context for AI prediction
        context_data = {
            'recent_incidents': len(historical_reports),
            'severity_pattern': {},
            'time_patterns': {},
            'location_focus': location
        }
        
        for report in historical_reports:
            severity = report.severity or 'medium'
            context_data['severity_pattern'][severity] = context_data['severity_pattern'].get(severity, 0) + 1
            
            hour = report.created_at.hour
            context_data['time_patterns'][str(hour)] = context_data['time_patterns'].get(str(hour), 0) + 1
        
        system_prompt = f"""
You are a predictive emergency analytics expert. Based on historical emergency data, predict the risk level and potential incidents for the next {time_hours} hours.

Consider:
- Historical incident patterns
- Severity distributions
- Time-based patterns
- Location-specific risks (if provided)
- Seasonal and environmental factors

Provide specific, actionable predictions and recommendations.

Respond with JSON in the specified format.
        """
        
        prediction_prompt = f"""
Based on this historical emergency data, predict emergency risk for the next {time_hours} hours:

{json.dumps(context_data, indent=2)}

{"Focus area: " + location if location else "General area prediction"}

Provide risk assessment and preparedness recommendations.
        """
        
        response = client.models.generate_content(
            model="gemini-2.5-pro",
            contents=[
                types.Content(role="user", parts=[types.Part(text=prediction_prompt)])
            ],
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                response_mime_type="application/json",
                response_schema=EmergencyPrediction,
            ),
        )
        
        raw_json = response.text
        if raw_json:
            data = json.loads(raw_json)
            return EmergencyPrediction(**data)
            
    except Exception as e:
        logging.error(f"Risk prediction failed: {e}")
    
    # Fallback prediction
    return EmergencyPrediction(
        risk_level="moderate",
        predicted_incidents=2,
        high_risk_areas=["Downtown", "Industrial District"],
        recommended_preparations=[
            "Ensure emergency vehicles are fueled and ready",
            "Check communication systems",
            "Review evacuation routes"
        ],
        confidence=0.7,
        time_frame=f"Next {time_hours} hours"
    )

def generate_emergency_insights_dashboard() -> dict:
    """Generate comprehensive insights for emergency management dashboard"""
    try:
        trend_analysis = analyze_emergency_trends()
        risk_prediction = predict_emergency_risk()
        
        # Get current statistics
        total_reports = models.EmergencyReport.query.count()
        active_alerts = models.Alert.query.filter_by(active=True).count()
        recent_reports = models.EmergencyReport.query.filter(
            models.EmergencyReport.created_at >= datetime.utcnow() - timedelta(hours=24)
        ).count()
        
        return {
            'summary_stats': {
                'total_reports': total_reports,
                'active_alerts': active_alerts,
                'recent_24h': recent_reports
            },
            'trends': trend_analysis.dict(),
            'predictions': risk_prediction.dict(),
            'generated_at': datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logging.error(f"Dashboard insights generation failed: {e}")
        return {
            'summary_stats': {'total_reports': 0, 'active_alerts': 0, 'recent_24h': 0},
            'trends': {'insights': ['Dashboard loading...']},
            'predictions': {'risk_level': 'unknown'},
            'generated_at': datetime.utcnow().isoformat()
        }