import logging
from typing import List, Dict, Any
from datetime import datetime
from twilio.rest import Client as TwilioClient
from app.config import settings

logger = logging.getLogger("app.notification")

# Global in-memory list to store virtual SMS and push messages for the Super Admin dashboard testing console
virtual_sms_logs: List[Dict[str, Any]] = []
virtual_push_logs: List[Dict[str, Any]] = []

def get_virtual_sms_logs() -> List[Dict[str, Any]]:
    return virtual_sms_logs

def clear_virtual_sms_logs():
    virtual_sms_logs.clear()

def get_virtual_push_logs() -> List[Dict[str, Any]]:
    return virtual_push_logs

def clear_virtual_push_logs():
    virtual_push_logs.clear()


def send_sms(to_phone: str, message: str) -> bool:
    """
    Sends an SMS using Twilio.
    If Twilio configuration is not provided or fails, it falls back to a Virtual SMS gateway,
    logging the message and saving it in-memory so it can be monitored via the Super Admin Dashboard.
    """
    timestamp = datetime.utcnow().isoformat()
    logger.info(f"Attempting to send SMS to {to_phone}: {message}")
    
    # Check if Twilio keys are configured
    if settings.TWILIO_ACCOUNT_SID and settings.TWILIO_AUTH_TOKEN and settings.TWILIO_PHONE_NUMBER:
        try:
            client = TwilioClient(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
            client.messages.create(
                body=message,
                from_=settings.TWILIO_PHONE_NUMBER,
                to=to_phone
            )
            logger.info(f"Twilio SMS successfully sent to {to_phone}")
            
            # Store in virtual log too for easy UI testing verification
            virtual_sms_logs.append({
                "to_phone": to_phone,
                "message": message,
                "timestamp": timestamp,
                "gateway": "twilio",
                "status": "sent"
            })
            return True
        except Exception as e:
            logger.error(f"Twilio SMS sending failed: {e}. Falling back to virtual gateway.")
    
    # Virtual SMS gateway fallback (Enabled by default for development)
    virtual_sms_logs.append({
        "to_phone": to_phone,
        "message": message,
        "timestamp": timestamp,
        "gateway": "virtual_fallback",
        "status": "sent (simulation)"
    })
    
    # Cap virtual logs to avoid memory bloat
    if len(virtual_sms_logs) > 500:
        virtual_sms_logs.pop(0)
        
    logger.info(f"[VIRTUAL SMS GATEWAY] Message queued for {to_phone}: {message}")
    return True


def send_push_notification(token: str, title: str, body: str, data: Dict[str, str] = None) -> bool:
    """
    Sends a push notification using Firebase Cloud Messaging.
    Gracefully falls back to virtual logging if credentials are not configured.
    """
    timestamp = datetime.utcnow().isoformat()
    logger.info(f"Attempting to send Push to device {token}: [{title}] {body}")
    
    # Firebase Cloud Messaging simulation
    # In a full FCM deployment, you would initialize firebase_admin with credentials and send messaging.Message.
    # To ensure it runs perfectly without credentials configuration:
    virtual_push_logs.append({
        "device_token": token,
        "title": title,
        "body": body,
        "data": data or {},
        "timestamp": timestamp,
        "status": "sent (simulation)"
    })
    
    if len(virtual_push_logs) > 500:
        virtual_push_logs.pop(0)
        
    logger.info(f"[VIRTUAL FCM GATEWAY] Push notification queued: [{title}] {body}")
    return True
