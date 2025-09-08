import os
import logging
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
import models

# Initialize Slack client
SLACK_BOT_TOKEN = os.environ.get('SLACK_BOT_TOKEN')
SLACK_CHANNEL_ID = os.environ.get('SLACK_CHANNEL_ID')

slack_client = WebClient(token=SLACK_BOT_TOKEN) if SLACK_BOT_TOKEN else None

def send_emergency_to_slack(emergency_report: models.EmergencyReport) -> bool:
    """Send emergency report to Slack channel for team coordination"""
    if not slack_client or not SLACK_CHANNEL_ID:
        return False
    
    try:
        user = models.User.query.get(emergency_report.user_id)
        
        # Create Slack message blocks for rich formatting
        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"🚨 EMERGENCY ALERT - {emergency_report.severity.upper()}"
                }
            },
            {
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": f"*Title:*\n{emergency_report.title}"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Reporter:*\n{user.username if user else 'Unknown'}"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Location:*\n{emergency_report.location or 'Not specified'}"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Time:*\n{emergency_report.created_at.strftime('%Y-%m-%d %H:%M:%S')}"
                    }
                ]
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Description:*\n{emergency_report.description}"
                }
            }
        ]
        
        # Add AI analysis if available
        if emergency_report.ai_analysis:
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*🤖 AI Analysis:*\n```{emergency_report.ai_analysis}```"
                }
            })
        
        # Add action buttons
        blocks.append({
            "type": "actions",
            "elements": [
                {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "🚁 Dispatch Response Team"
                    },
                    "style": "danger",
                    "value": f"dispatch_{emergency_report.id}"
                },
                {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "📞 Contact Reporter"
                    },
                    "value": f"contact_{emergency_report.id}"
                },
                {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "✅ Mark Resolved"
                    },
                    "style": "primary",
                    "value": f"resolve_{emergency_report.id}"
                }
            ]
        })
        
        response = slack_client.chat_postMessage(
            channel=SLACK_CHANNEL_ID,
            text=f"Emergency Alert: {emergency_report.title}",  # Fallback text
            blocks=blocks
        )
        
        logging.info(f"Emergency sent to Slack: {response['ts']}")
        return True
        
    except SlackApiError as e:
        logging.error(f"Slack API error: {e}")
        return False
    except Exception as e:
        logging.error(f"Failed to send to Slack: {e}")
        return False

def send_alert_to_slack(alert: models.Alert) -> bool:
    """Send system alert to Slack channel"""
    if not slack_client or not SLACK_CHANNEL_ID:
        return False
    
    try:
        severity_emoji = {
            'critical': '🔴',
            'high': '🟠',
            'medium': '🟡',
            'low': '🟢'
        }
        
        message = f"""
{severity_emoji.get(alert.severity, '📢')} **SYSTEM ALERT**

**{alert.title}**

Type: {alert.alert_type or 'General'}
Severity: {alert.severity.upper()}
Location: {alert.location or 'Area-wide'}

{alert.description}

Generated: {alert.created_at.strftime('%Y-%m-%d %H:%M:%S')}
        """
        
        response = slack_client.chat_postMessage(
            channel=SLACK_CHANNEL_ID,
            text=message
        )
        
        logging.info(f"Alert sent to Slack: {response['ts']}")
        return True
        
    except Exception as e:
        logging.error(f"Failed to send alert to Slack: {e}")
        return False

def send_daily_summary_to_slack() -> bool:
    """Send daily emergency summary to Slack"""
    if not slack_client or not SLACK_CHANNEL_ID:
        return False
    
    try:
        from datetime import datetime, timedelta
        
        # Get today's statistics
        today = datetime.utcnow().date()
        today_start = datetime.combine(today, datetime.min.time())
        
        total_reports = EmergencyReport.query.filter(
            EmergencyReport.created_at >= today_start
        ).count()
        
        critical_reports = EmergencyReport.query.filter(
            EmergencyReport.created_at >= today_start,
            EmergencyReport.severity == 'critical'
        ).count()
        
        active_alerts = Alert.query.filter_by(active=True).count()
        
        message = f"""
📊 **Daily Emergency Summary** - {today.strftime('%B %d, %Y')}

📋 Total Reports: {total_reports}
🚨 Critical Incidents: {critical_reports}
⚠️ Active Alerts: {active_alerts}

Crisis Navigator is monitoring and coordinating emergency response efforts.
Stay safe! 🛡️
        """
        
        response = slack_client.chat_postMessage(
            channel=SLACK_CHANNEL_ID,
            text=message
        )
        
        logging.info(f"Daily summary sent to Slack: {response['ts']}")
        return True
        
    except Exception as e:
        logging.error(f"Failed to send daily summary to Slack: {e}")
        return False

def get_slack_integration_status() -> dict:
    """Check Slack integration status"""
    if not slack_client or not SLACK_CHANNEL_ID:
        return {
            'enabled': False,
            'status': 'Not configured',
            'error': 'Missing Slack credentials'
        }
    
    try:
        # Test the connection
        response = slack_client.auth_test()
        
        return {
            'enabled': True,
            'status': 'Connected',
            'team': response.get('team', 'Unknown'),
            'user': response.get('user', 'Unknown'),
            'channel': SLACK_CHANNEL_ID
        }
        
    except Exception as e:
        return {
            'enabled': False,
            'status': 'Connection failed',
            'error': str(e)
        }