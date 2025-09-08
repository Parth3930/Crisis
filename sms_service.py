import os
import logging
from twilio.rest import Client
import models

# Initialize Twilio client
TWILIO_ACCOUNT_SID = os.environ.get("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.environ.get("TWILIO_AUTH_TOKEN") 
TWILIO_PHONE_NUMBER = os.environ.get("TWILIO_PHONE_NUMBER")

client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN) if TWILIO_ACCOUNT_SID else None

def send_emergency_sms(phone_number: str, emergency_report: models.EmergencyReport) -> bool:
    """Send SMS alert for emergency report"""
    if not client or not phone_number:
        return False
    
    try:
        severity_emoji = {
            'critical': '🚨',
            'high': '⚠️',
            'medium': '📢',
            'low': '📍'
        }
        
        message_body = f"""
{severity_emoji.get(emergency_report.severity, '📢')} EMERGENCY ALERT
{emergency_report.severity.upper()} PRIORITY

Title: {emergency_report.title}
Location: {emergency_report.location or 'Location unknown'}
Time: {emergency_report.created_at.strftime('%m/%d/%Y %I:%M %p')}

Description: {emergency_report.description[:100]}{'...' if len(emergency_report.description) > 100 else ''}

Crisis Navigator - Immediate response required
        """.strip()
        
        message = client.messages.create(
            body=message_body,
            from_=TWILIO_PHONE_NUMBER,
            to=phone_number
        )
        
        logging.info(f"SMS sent successfully: {message.sid}")
        return True
        
    except Exception as e:
        logging.error(f"Failed to send SMS: {e}")
        return False

def send_bulk_emergency_alerts(emergency_report: models.EmergencyReport, radius_km: float = 10) -> int:
    """Send SMS alerts to all users within radius of emergency"""
    if not client:
        return 0
    
    sent_count = 0
    try:
        # Get users with phone numbers (in real app, would calculate distance)
        users_to_notify = models.User.query.filter(models.User.phone.isnot(None)).limit(50).all()
        
        for user in users_to_notify:
            if send_emergency_sms(user.phone, emergency_report):
                sent_count += 1
                
        logging.info(f"Sent {sent_count} emergency SMS alerts")
        return sent_count
        
    except Exception as e:
        logging.error(f"Failed to send bulk SMS alerts: {e}")
        return sent_count

def send_status_update_sms(phone_number: str, report_id: int, new_status: str) -> bool:
    """Send SMS when emergency status is updated"""
    if not client or not phone_number:
        return False
    
    try:
        status_messages = {
            'in_progress': '🚁 Emergency responders have been dispatched to your location',
            'resolved': '✅ Emergency situation has been resolved. Stay safe!'
        }
        
        message_body = f"""
Crisis Navigator Update

Emergency Report #{report_id}
Status: {new_status.upper().replace('_', ' ')}

{status_messages.get(new_status, f'Status updated to: {new_status}')}

Thank you for using Crisis Navigator
        """.strip()
        
        message = client.messages.create(
            body=message_body,
            from_=TWILIO_PHONE_NUMBER,
            to=phone_number
        )
        
        logging.info(f"Status update SMS sent: {message.sid}")
        return True
        
    except Exception as e:
        logging.error(f"Failed to send status SMS: {e}")
        return False