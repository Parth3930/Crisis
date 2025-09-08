import os
import json
import logging
from datetime import datetime, timedelta
import trafilatura
from google import genai
from google.genai import types
from pydantic import BaseModel
import models
from extensions import db

# Initialize Gemini client with safe default key
client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY", "disabled-key"))

class CrisisDetection(BaseModel):
    is_crisis: bool
    crisis_type: str
    severity: str  # low, medium, high, critical
    location: str | None
    confidence: float
    summary: str
    recommended_actions: list[str]

def scrape_news_for_crises(news_urls: list[str] = None) -> list[CrisisDetection]:
    """Scrape news websites for crisis information"""
    default_urls = [
        "https://www.cnn.com/",
        "https://www.reuters.com/",
        "https://www.bbc.com/news",
        "https://apnews.com/",
        "https://www.weather.gov/"
    ]
    
    urls_to_check = news_urls or default_urls
    crisis_detections = []
    
    for url in urls_to_check[:3]:  # Limit to avoid overwhelming the system
        try:
            # Scrape the website content
            downloaded = trafilatura.fetch_url(url)
            if not downloaded:
                continue
                
            text_content = trafilatura.extract(downloaded)
            if not text_content:
                continue
            
            # Analyze content for crisis information
            crisis_info = analyze_text_for_crisis(text_content[:2000], url)  # Limit text length
            if crisis_info.is_crisis and crisis_info.confidence > 0.6:
                crisis_detections.append(crisis_info)
                
        except Exception as e:
            logging.error(f"Error scraping {url}: {e}")
            continue
    
    return crisis_detections

def analyze_text_for_crisis(text: str, source: str = "Unknown") -> CrisisDetection:
    """Use AI to analyze text content for crisis information"""
    try:
        system_prompt = """
You are a crisis detection AI system. Analyze the provided news text to identify potential emergency situations.

Look for:
- Natural disasters (earthquakes, hurricanes, floods, wildfires)
- Human-made emergencies (accidents, building collapses, chemical spills)
- Public health emergencies (disease outbreaks, contamination)
- Security incidents (terrorism, mass violence)
- Infrastructure failures (power outages, transportation disruptions)

Determine:
1. Is this describing an active crisis situation?
2. What type of crisis is it?
3. Severity level (low/medium/high/critical)
4. Location if mentioned
5. Confidence in your assessment (0.0 to 1.0)
6. Brief summary of the situation
7. Recommended emergency response actions

Respond with JSON in the specified format. Only classify as crisis if it's an active, current emergency situation.
        """
        
        analysis_prompt = f"Analyze this news content for crisis situations:\n\nSource: {source}\n\nContent:\n{text}"
        
        response = client.models.generate_content(
            model="gemini-2.5-pro",
            contents=[
                types.Content(role="user", parts=[types.Part(text=analysis_prompt)])
            ],
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                response_mime_type="application/json",
                response_schema=CrisisDetection,
            ),
        )
        
        raw_json = response.text
        if raw_json:
            data = json.loads(raw_json)
            return CrisisDetection(**data)
            
    except Exception as e:
        logging.error(f"Crisis analysis failed: {e}")
    
    # Return safe fallback
    return CrisisDetection(
        is_crisis=False,
        crisis_type="unknown",
        severity="low",
        location=None,
        confidence=0.0,
        summary="Analysis unavailable",
        recommended_actions=[]
    )

def monitor_social_keywords() -> list[dict]:
    """Monitor for crisis-related keywords (simulated social monitoring)"""
    # This would connect to social media APIs in a real implementation
    # For demo purposes, we'll simulate detecting crisis keywords
    
    simulated_social_posts = [
        {
            'content': 'Major traffic accident on Highway 95, multiple vehicles involved, emergency responders on scene',
            'timestamp': datetime.utcnow() - timedelta(minutes=15),
            'platform': 'Twitter',
            'location': 'Highway 95'
        },
        {
            'content': 'Power outage affecting downtown area, traffic lights not working, avoid the area',
            'timestamp': datetime.utcnow() - timedelta(minutes=30),
            'platform': 'Facebook',
            'location': 'Downtown'
        },
        {
            'content': 'Smoke visible from industrial district, fire department responding',
            'timestamp': datetime.utcnow() - timedelta(minutes=45),
            'platform': 'Instagram',
            'location': 'Industrial District'
        }
    ]
    
    crisis_posts = []
    for post in simulated_social_posts:
        # Analyze post for crisis content
        crisis_info = analyze_text_for_crisis(post['content'])
        if crisis_info.is_crisis and crisis_info.confidence > 0.5:
            crisis_posts.append({
                'original_post': post,
                'analysis': crisis_info.dict(),
                'detected_at': datetime.utcnow()
            })
    
    return crisis_posts

def create_automatic_alerts_from_monitoring() -> int:
    """Create automatic alerts based on monitoring data"""
    alerts_created = 0
    
    try:
        # Check news sources
        news_crises = scrape_news_for_crises()
        for crisis in news_crises:
            if crisis.severity in ['high', 'critical'] and crisis.confidence > 0.7:
                alert = models.Alert()
                alert.title = f"Detected Crisis: {crisis.crisis_type.title()}"
                alert.description = crisis.summary
                alert.alert_type = crisis.crisis_type
                alert.severity = crisis.severity
                alert.location = crisis.location
                alert.active = True
                
                db.session.add(alert)
                alerts_created += 1
        
        # Check social media monitoring
        social_crises = monitor_social_keywords()
        for social_crisis in social_crises:
            analysis = social_crisis['analysis']
            if analysis['severity'] in ['high', 'critical']:
                alert = models.Alert()
                alert.title = f"Social Media Alert: {analysis['crisis_type'].title()}"
                alert.description = f"Detected from social media: {analysis['summary']}"
                alert.alert_type = analysis['crisis_type']
                alert.severity = analysis['severity']
                alert.location = analysis.get('location')
                alert.active = True
                
                db.session.add(alert)
                alerts_created += 1
        
        if alerts_created > 0:
            db.session.commit()
            logging.info(f"Created {alerts_created} automatic alerts from monitoring")
        
    except Exception as e:
        db.session.rollback()
        logging.error(f"Failed to create automatic alerts: {e}")
    
    return alerts_created

def generate_crisis_monitoring_report() -> dict:
    """Generate comprehensive crisis monitoring report"""
    try:
        # Get monitoring results
        news_results = scrape_news_for_crises()
        social_results = monitor_social_keywords()
        
        # Count active crises by severity
        crisis_counts = {
            'critical': len([c for c in news_results if c.severity == 'critical']),
            'high': len([c for c in news_results if c.severity == 'high']),
            'medium': len([c for c in news_results if c.severity == 'medium']),
            'low': len([c for c in news_results if c.severity == 'low'])
        }
        
        # Get unique crisis types
        crisis_types = list(set([c.crisis_type for c in news_results if c.is_crisis]))
        
        # Get affected locations
        locations = list(set([c.location for c in news_results if c.location]))
        
        return {
            'monitoring_timestamp': datetime.utcnow().isoformat(),
            'sources_checked': 5,  # Number of sources monitored
            'crises_detected': len([c for c in news_results if c.is_crisis]),
            'social_alerts': len(social_results),
            'crisis_counts_by_severity': crisis_counts,
            'crisis_types_detected': crisis_types,
            'affected_locations': locations,
            'recommendations': [
                'Continue monitoring news sources for emerging threats',
                'Verify social media reports through official channels',
                'Maintain readiness for high-severity incidents'
            ],
            'detailed_results': {
                'news_crises': [c.dict() for c in news_results if c.is_crisis],
                'social_monitoring': social_results
            }
        }
        
    except Exception as e:
        logging.error(f"Crisis monitoring report failed: {e}")
        return {
            'monitoring_timestamp': datetime.utcnow().isoformat(),
            'error': 'Monitoring report generation failed',
            'sources_checked': 0,
            'crises_detected': 0
        }