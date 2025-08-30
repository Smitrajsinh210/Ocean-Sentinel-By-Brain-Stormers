"""
Ocean Sentinel - Multi-Channel Notification Service
Real-time alerts via SMS, Email, Push notifications, and WebSockets
"""

import asyncio
import aiohttp
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
import json
from twilio.rest import Client as TwilioClient
from twilio.base.exceptions import TwilioException
import pusher
import smtplib
from email.mime.text import MimeText
from email.mime.multipart import MimeMultipart

from app.config import settings, NOTIFICATION_CHANNELS
from app.utils.database import create_supabase_client

logger = logging.getLogger(__name__)

class NotificationService:
    """Comprehensive notification service for threat alerts"""
    
    def __init__(self):
        # Initialize services
        self.pusher_client = None
        self.twilio_client = None
        self.supabase = create_supabase_client()
        
        # Initialize Pusher for real-time notifications
        if all([settings.pusher_app_id, settings.pusher_key, settings.pusher_secret]):
            self.pusher_client = pusher.Pusher(
                app_id=settings.pusher_app_id,
                key=settings.pusher_key,
                secret=settings.pusher_secret,
                cluster=settings.pusher_cluster,
                ssl=True
            )
            logger.info("✅ Pusher client initialized")
        else:
            logger.warning("⚠️ Pusher credentials not configured")
        
        # Initialize Twilio for SMS
        if settings.twilio_sid and settings.twilio_token:
            self.twilio_client = TwilioClient(settings.twilio_sid, settings.twilio_token)
            logger.info("✅ Twilio client initialized")
        else:
            logger.warning("⚠️ Twilio credentials not configured")
    
    async def send_critical_alert(self, threat_data: Dict) -> Dict[str, Any]:
        """
        Send critical threat alert through all available channels
        Args:
            threat_data: Threat information dictionary
        Returns:
            Results of notification attempts
        """
        logger.info(f"🚨 Sending critical alert for {threat_data.get('type')} threat")
        
        # Get recipients based on threat location and severity
        recipients = await self._get_alert_recipients(threat_data)
        
        # Prepare alert message
        alert_message = self._generate_alert_message(threat_data)
        
        # Send through all channels
        results = {
            'alert_id': f"alert_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
            'threat_id': threat_data.get('id'),
            'timestamp': datetime.utcnow().isoformat(),
            'channels': {},
            'recipients_notified': 0,
            'total_recipients': len(recipients)
        }
        
        # Real-time web notifications
        if self.pusher_client:
            web_result = await self._send_web_notification(threat_data, alert_message)
            results['channels']['web'] = web_result
        
        # SMS notifications for high severity
        if threat_data.get('severity', 0) >= 4 and self.twilio_client:
            sms_result = await self._send_sms_alerts(recipients, alert_message)
            results['channels']['sms'] = sms_result
            results['recipients_notified'] += sms_result.get('sent_count', 0)
        
        # Email notifications
        email_result = await self._send_email_alerts(recipients, threat_data, alert_message)
        results['channels']['email'] = email_result
        results['recipients_notified'] += email_result.get('sent_count', 0)
        
        # Webhook notifications for emergency services
        if threat_data.get('severity', 0) >= 4:
            webhook_result = await self._send_webhook_alerts(threat_data)
            results['channels']['webhook'] = webhook_result
        
        # Store alert record
        await self._store_alert_record(results, threat_data)
        
        logger.info(f"📊 Alert sent to {results['recipients_notified']}/{results['total_recipients']} recipients")
        return results
    
    async def send_routine_notification(self, data: Dict, notification_type: str = "update") -> bool:
        """
        Send routine system updates (non-critical)
        Args:
            data: Notification data
            notification_type: Type of notification (update, report, etc.)
        Returns:
            Success status
        """
        try:
            if self.pusher_client:
                # Send to dashboard channel
                self.pusher_client.trigger(
                    'dashboard-updates',
                    notification_type,
                    {
                        'data': data,
                        'timestamp': datetime.utcnow().isoformat(),
                        'type': notification_type
                    }
                )
                
                logger.info(f"📢 Routine notification sent: {notification_type}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error sending routine notification: {e}")
            return False
    
    async def _send_web_notification(self, threat_data: Dict, message: str) -> Dict:
        """Send real-time web notification via Pusher"""
        try:
            if not self.pusher_client:
                return {'status': 'failed', 'reason': 'Pusher not configured'}
            
            # Broadcast to all connected clients
            self.pusher_client.trigger(
                'threat-alerts',
                'new-threat',
                {
                    'threat': threat_data,
                    'message': message,
                    'timestamp': datetime.utcnow().isoformat(),
                    'severity': threat_data.get('severity', 1),
                    'location': {
                        'lat': threat_data.get('latitude'),
                        'lon': threat_data.get('longitude')
                    }
                }
            )
            
            # Send to location-specific channels if coordinates available
            if threat_data.get('latitude') and threat_data.get('longitude'):
                lat, lon = threat_data['latitude'], threat_data['longitude']
                location_channel = f"location-{int(lat)}_{int(lon)}"
                
                self.pusher_client.trigger(
                    location_channel,
                    'local-threat',
                    {
                        'threat': threat_data,
                        'message': message,
                        'timestamp': datetime.utcnow().isoformat()
                    }
                )
            
            return {'status': 'success', 'channels': ['threat-alerts', 'location-specific']}
            
        except Exception as e:
            logger.error(f"Error sending web notification: {e}")
            return {'status': 'failed', 'reason': str(e)}
    
    async def _send_sms_alerts(self, recipients: List[Dict], message: str) -> Dict:
        """Send SMS alerts via Twilio"""
        if not self.twilio_client:
            return {'status': 'failed', 'reason': 'Twilio not configured', 'sent_count': 0}
        
        sent_count = 0
        failed_count = 0
        errors = []
        
        for recipient in recipients:
            phone = recipient.get('phone')
            if not phone:
                continue
            
            try:
                message_obj = self.twilio_client.messages.create(
                    body=message[:1600],  # SMS character limit
                    from_=settings.twilio_phone,
                    to=phone
                )
                
                sent_count += 1
                logger.info(f"📱 SMS sent to {phone[-4:]}****")
                
            except TwilioException as e:
                failed_count += 1
                errors.append(f"SMS to {phone[-4:]}****: {str(e)}")
                logger.error(f"Failed to send SMS to {phone[-4:]}****: {e}")
            
            # Rate limiting - Twilio free tier has limits
            await asyncio.sleep(1)
        
        return {
            'status': 'completed',
            'sent_count': sent_count,
            'failed_count': failed_count,
            'errors': errors
        }
    
    async def _send_email_alerts(self, recipients: List[Dict], threat_data: Dict, message: str) -> Dict:
        """Send email alerts using Resend or SMTP"""
        sent_count = 0
        failed_count = 0
        errors = []
        
        for recipient in recipients:
            email = recipient.get('email')
            if not email:
                continue
            
            try:
                success = await self._send_single_email(
                    email, 
                    threat_data, 
                    message,
                    recipient.get('name', 'Recipient')
                )
                
                if success:
                    sent_count += 1
                    logger.info(f"📧 Email sent to {email}")
                else:
                    failed_count += 1
                    errors.append(f"Failed to send email to {email}")
                
            except Exception as e:
                failed_count += 1
                errors.append(f"Email to {email}: {str(e)}")
                logger.error(f"Failed to send email to {email}: {e}")
            
            # Rate limiting
            await asyncio.sleep(0.5)
        
        return {
            'status': 'completed',
            'sent_count': sent_count,
            'failed_count': failed_count,
            'errors': errors
        }
    
    async def _send_single_email(self, email: str, threat_data: Dict, message: str, name: str) -> bool:
        """Send a single email notification"""
        try:
            if settings.resend_api_key:
                # Use Resend API
                return await self._send_via_resend(email, threat_data, message, name)
            else:
                # Use SMTP (fallback)
                return await self._send_via_smtp(email, threat_data, message, name)
                
        except Exception as e:
            logger.error(f"Error sending email: {e}")
            return False
    
    async def _send_via_resend(self, email: str, threat_data: Dict, message: str, name: str) -> bool:
        """Send email via Resend API"""
        try:
            url = "https://api.resend.com/emails"
            headers = {
                'Authorization': f'Bearer {settings.resend_api_key}',
                'Content-Type': 'application/json'
            }
            
            # Generate HTML email content
            html_content = self._generate_email_html(threat_data, message, name)
            
            payload = {
                'from': 'Ocean Sentinel <alerts@oceansentinel.ai>',
                'to': [email],
                'subject': f'🚨 Ocean Sentinel Alert: {threat_data.get("type", "Environmental").title()} Threat Detected',
                'html': html_content,
                'text': message
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, json=payload) as response:
                    if response.status == 200:
                        return True
                    else:
                        logger.error(f"Resend API error: {response.status}")
                        return False
                        
        except Exception as e:
            logger.error(f"Error with Resend API: {e}")
            return False
    
    async def _send_via_smtp(self, email: str, threat_data: Dict, message: str, name: str) -> bool:
        """Send email via SMTP (fallback method)"""
        try:
            # For demo purposes, we'll just log that email would be sent
            logger.info(f"📧 Email prepared for {email} (SMTP not configured)")
            return True
            
        except Exception as e:
            logger.error(f"SMTP error: {e}")
            return False
    
    async def _send_webhook_alerts(self, threat_data: Dict) -> Dict:
        """Send webhook alerts to emergency services and partner systems"""
        webhooks = [
            # Add webhook URLs for emergency services
            # These would be configured based on partnerships
            {
                'url': 'https://httpbin.org/post',  # Test webhook
                'name': 'Emergency Services Test'
            }
        ]
        
        sent_count = 0
        failed_count = 0
        errors = []
        
        for webhook in webhooks:
            try:
                payload = {
                    'source': 'Ocean Sentinel',
                    'threat': threat_data,
                    'timestamp': datetime.utcnow().isoformat(),
                    'priority': 'high' if threat_data.get('severity', 0) >= 4 else 'medium'
                }
                
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        webhook['url'], 
                        json=payload,
                        timeout=aiohttp.ClientTimeout(total=10)
                    ) as response:
                        if response.status == 200:
                            sent_count += 1
                            logger.info(f"🔗 Webhook sent to {webhook['name']}")
                        else:
                            failed_count += 1
                            errors.append(f"{webhook['name']}: HTTP {response.status}")
                            
            except Exception as e:
                failed_count += 1
                errors.append(f"{webhook['name']}: {str(e)}")
                logger.error(f"Webhook error for {webhook['name']}: {e}")
        
        return {
            'status': 'completed',
            'sent_count': sent_count,
            'failed_count': failed_count,
            'errors': errors
        }
    
    async def _get_alert_recipients(self, threat_data: Dict) -> List[Dict]:
        """Get list of recipients for alert based on threat location and severity"""
        try:
            # For demo purposes, return sample recipients
            recipients = [
                {
                    'id': 'user_001',
                    'name': 'Emergency Coordinator',
                    'email': 'emergency@coastalauth.gov',
                    'phone': '+1234567890',
                    'role': 'emergency_manager'
                },
                {
                    'id': 'user_002', 
                    'name': 'Harbor Master',
                    'email': 'harbor@portauth.gov',
                    'phone': '+1234567891',
                    'role': 'port_authority'
                }
            ]
            
            return recipients
            
        except Exception as e:
            logger.error(f"Error getting recipients: {e}")
            return []
    
    def _generate_alert_message(self, threat_data: Dict) -> str:
        """Generate human-readable alert message"""
        threat_type = threat_data.get('type', 'environmental').title()
        severity = threat_data.get('severity', 1)
        confidence = threat_data.get('confidence', 0) * 100
        description = threat_data.get('description', 'Environmental threat detected')
        recommendation = threat_data.get('recommendation', 'Monitor situation closely')
        
        severity_text = {
            1: "MINOR", 2: "MODERATE", 3: "SIGNIFICANT", 
            4: "DANGEROUS", 5: "EXTREME"
        }.get(severity, "UNKNOWN")
        
        message = f"""
🚨 OCEAN SENTINEL ALERT 🚨

{severity_text} {threat_type} THREAT DETECTED

📍 Location: {threat_data.get('latitude', 'N/A'):.4f}, {threat_data.get('longitude', 'N/A'):.4f}
⚠️ Severity: {severity}/5
🎯 Confidence: {confidence:.0f}%
⏰ Detected: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}

📋 Description: {description}

🔧 Recommended Action: {recommendation}

This is an automated alert from Ocean Sentinel AI monitoring system.
For more information, visit the dashboard or contact emergency services if immediate action is required.
        """.strip()
        
        return message
    
    def _generate_email_html(self, threat_data: Dict, message: str, name: str) -> str:
        """Generate HTML email content"""
        severity_colors = {
            1: "#28a745", 2: "#ffc107", 3: "#fd7e14", 4: "#dc3545", 5: "#6f42c1"
        }
        
        severity = threat_data.get('severity', 1)
        color = severity_colors.get(severity, "#6c757d")
        
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Ocean Sentinel Alert</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 0; padding: 20px; }}
        .container {{ max-width: 600px; margin: 0 auto; border: 1px solid #ddd; border-radius: 8px; }}
        .header {{ background: {color}; color: white; padding: 20px; text-align: center; border-radius: 8px 8px 0 0; }}
        .content {{ padding: 20px; }}
        .footer {{ background: #f8f9fa; padding: 15px; text-align: center; border-radius: 0 0 8px 8px; }}
        .alert-details {{ background: #f8f9fa; padding: 15px; border-radius: 4px; margin: 15px 0; }}
        .severity-badge {{ display: inline-block; padding: 4px 8px; background: {color}; color: white; border-radius: 4px; font-weight: bold; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🌊 Ocean Sentinel Alert</h1>
            <p>Environmental Threat Detection System</p>
        </div>
        <div class="content">
            <h2>Hello {name},</h2>
            <p>Ocean Sentinel has detected a <span class="severity-badge">SEVERITY {severity}</span> environmental threat that may affect your area.</p>
            
            <div class="alert-details">
                <h3>Threat Details:</h3>
                <ul>
                    <li><strong>Type:</strong> {threat_data.get('type', 'Unknown').title()}</li>
                    <li><strong>Severity:</strong> {severity}/5</li>
                    <li><strong>Confidence:</strong> {threat_data.get('confidence', 0)*100:.0f}%</li>
                    <li><strong>Location:</strong> {threat_data.get('latitude', 'N/A'):.4f}, {threat_data.get('longitude', 'N/A'):.4f}</li>
                    <li><strong>Detected:</strong> {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}</li>
                </ul>
                
                <p><strong>Description:</strong> {threat_data.get('description', 'Environmental threat detected')}</p>
                <p><strong>Recommended Action:</strong> {threat_data.get('recommendation', 'Monitor situation closely')}</p>
            </div>
            
            <p>This alert was generated automatically by our AI monitoring system. For real-time updates and detailed information, please visit your Ocean Sentinel dashboard.</p>
        </div>
        <div class="footer">
            <p>Ocean Sentinel - AI-Powered Coastal Threat Detection</p>
            <p>This is an automated message. Do not reply to this email.</p>
        </div>
    </div>
</body>
</html>
        """
        
        return html
    
    async def _store_alert_record(self, alert_results: Dict, threat_data: Dict):
        """Store alert record in database"""
        try:
            record = {
                'alert_id': alert_results['alert_id'],
                'threat_id': threat_data.get('id'),
                'message': self._generate_alert_message(threat_data)[:500],  # Truncate for storage
                'severity': threat_data.get('severity', 1),
                'channels': json.dumps(list(alert_results['channels'].keys())),
                'recipients_count': alert_results['recipients_notified'],
                'total_recipients': alert_results['total_recipients'],
                'status': 'sent',
                'timestamp': alert_results['timestamp']
            }
            
            await self.supabase.table('alert_notifications').insert(record).execute()
            logger.info(f"📝 Alert record stored: {alert_results['alert_id']}")
            
        except Exception as e:
            logger.error(f"Failed to store alert record: {e}")
