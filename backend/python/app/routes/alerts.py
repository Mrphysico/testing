from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app.models import Alert, Accident
from app.schemas import AlertOut, ManualAlertSend
from app.auth import require_responder
from app.services.notification import send_sms, get_virtual_sms_logs, clear_virtual_sms_logs, get_virtual_push_logs, clear_virtual_push_logs

router = APIRouter(prefix="/alerts", tags=["alerts"])

@router.post("/send", response_model=AlertOut, status_code=status.HTTP_201_CREATED)
def send_manual_alert(payload: ManualAlertSend, db: Session = Depends(get_db), current_user = Depends(require_responder)):
    """
    Manually dispatch an emergency SMS broadcast related to a specific accident.
    """
    accident = db.query(Accident).filter(Accident.id == payload.accident_id).first()
    if not accident:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Linked accident report not found."
        )
        
    # Send SMS via gateway
    success = send_sms(payload.recipient_phone, payload.message_text)
    
    db_alert = Alert(
        accident_id=payload.accident_id,
        recipient_name="Manual Recipient",
        recipient_phone=payload.recipient_phone,
        type="sms",
        message_text=payload.message_text,
        status="sent" if success else "failed"
    )
    
    db.add(db_alert)
    db.commit()
    db.refresh(db_alert)
    return db_alert


@router.get("/virtual-gateway/sms-logs")
def get_virtual_sms_gateway_logs(current_user = Depends(require_responder)):
    """
    Retreive all SMS transmissions captured by the virtual simulator.
    Used for live verification on the Super Admin control panel.
    """
    return get_virtual_sms_logs()


@router.delete("/virtual-gateway/sms-logs")
def clear_virtual_sms_gateway_logs(current_user = Depends(require_responder)):
    """
    Wipes the virtual SMS cache.
    """
    clear_virtual_sms_logs()
    return {"message": "Virtual SMS logs cleared."}


@router.get("/virtual-gateway/push-logs")
def get_virtual_push_gateway_logs(current_user = Depends(require_responder)):
    """
    Retrieve all simulated Push messages captured by the virtual gateway.
    """
    return get_virtual_push_logs()


@router.delete("/virtual-gateway/push-logs")
def clear_virtual_push_gateway_logs(current_user = Depends(require_responder)):
    """
    Wipes the virtual push notification logs.
    """
    clear_virtual_push_logs()
    return {"message": "Virtual push logs cleared."}


@router.get("/{accident_id}", response_model=List[AlertOut])
def get_alerts_for_accident(accident_id: int, db: Session = Depends(get_db), current_user = Depends(require_responder)):
    """
    Fetch all alerts generated (SMS, Push, Call) for a specific accident.
    """
    alerts = db.query(Alert).filter(Alert.accident_id == accident_id).order_by(Alert.sent_at.desc()).all()
    return alerts
