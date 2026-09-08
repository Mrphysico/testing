from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
import datetime
import requests
import asyncio
import logging

from app.database import get_db
from app.models import Accident, Vehicle, EmergencyContact, PublicFamilyAccess, Station, Alert, DispatchEvent
from app.schemas import AccidentTrigger, AccidentOut, AccidentPoliceStatusUpdate, AccidentHospitalStatusUpdate, FamilyAccidentOut
from app.auth import get_current_user, require_responder
from app.websocket import manager
from app.services.notification import send_sms, send_push_notification
from app.routes.stations import haversine_distance

logger = logging.getLogger("app.accidents")

router = APIRouter(prefix="/accidents", tags=["accidents"])


def get_response_policy(severity: str) -> dict:
    """
    Decide whether an incident needs confirmation calls or immediate dispatch.
    Low damage is verified by calls first. High and critical crashes dispatch at once.
    """
    severity = severity.lower()
    if severity == "low":
        return {
            "police_status": "call_confirmation",
            "hospital_status": "call_confirmation",
            "action": "confirmation_call",
            "family_text": "minor damage has been detected. Police and hospital teams will confirm through calls before dispatch.",
            "responder_text": "Low damage detected. Call the vehicle owner/home contact and confirm whether field help is required.",
            "push_title": "Verification Call Required",
            "push_body": "Low severity accident signal received. Confirm by phone before dispatch.",
        }
    if severity == "medium":
        return {
            "police_status": "call_confirmation",
            "hospital_status": "call_confirmation",
            "action": "confirmation_call_priority",
            "family_text": "moderate damage has been detected. Emergency teams are confirming by phone and preparing response.",
            "responder_text": "Medium severity accident signal received. Call to confirm condition and prepare dispatch if needed.",
            "push_title": "Priority Verification Required",
            "push_body": "Medium severity accident signal received. Confirm quickly and prepare response.",
        }
    return {
        "police_status": "dispatched",
        "hospital_status": "dispatched",
        "action": "immediate_dispatch",
        "family_text": "heavy damage has been detected due to a road accident. Police and ambulance help have been dispatched immediately.",
        "responder_text": "Immediate dispatch required. Send police unit and ambulance to the accident location now.",
        "push_title": "Immediate Help Dispatched",
        "push_body": "Critical/high severity crash detected. Police and ambulance dispatch required immediately.",
    }


def reverse_geocode(lat: float, lon: float) -> str:
    """
    Resolves GPS coordinates to a human-readable street address.
    Utilizes OpenStreetMap Nominatim with a high-fidelity offline Indian road locator fallback.
    """
    try:
        url = f"https://nominatim.openstreetmap.org/reverse?format=json&lat={lat}&lon={lon}&zoom=15"
        # Nominatim requires a user agent
        headers = {"User-Agent": "GovernmentAccidentAlertSystem/2.0 (contact: admin@gov.in)"}
        response = requests.get(url, headers=headers, timeout=2.5)
        if response.status_code == 200:
            data = response.json()
            address = data.get("display_name")
            if address:
                return address
    except Exception as e:
        logger.warning(f"Reverse geocode lookup failed: {e}. Utilizing offline fallback.")

    # High-quality offline Indian road location mapping fallback
    major_regions = [
        ("Mumbai-Pune Expressway, Maharashtra", 18.78, 73.34),
        ("Yamuna Expressway, Greater Noida, UP", 28.40, 77.53),
        ("Outer Ring Road, Bengaluru, Karnataka", 12.92, 77.68),
        ("NH-48, Sector 15, Gurugram, Haryana", 28.45, 77.02),
        ("Mount Road, Teynampet, Chennai, TN", 13.04, 80.24),
        ("Eastern Express Highway, Mumbai, MH", 19.11, 72.91),
        ("Ring Road near Dhaula Kuan, New Delhi", 28.59, 77.16),
        ("Gachibowli Flyover, Hyderabad, Telangana", 17.44, 78.34),
        ("Howrah Bridge Approach, Kolkata, WB", 22.58, 88.34)
    ]
    
    # Locate closest coordinate seed
    closest_region = "National Highway 44"
    min_dist = float('inf')
    for region, r_lat, r_lon in major_regions:
        dist = (lat - r_lat)**2 + (lon - r_lon)**2
        if dist < min_dist:
            min_dist = dist
            closest_region = region
            
    return f"{closest_region}, India (GPS Coordinates: {lat:.5f}, {longitude:.5f})" if 'longitude' in globals() else f"{closest_region}, India (GPS Coordinates: {lat:.5f}, {lon:.5f})"


@router.post("/trigger", response_model=AccidentOut, status_code=status.HTTP_201_CREATED)
def trigger_accident(payload: AccidentTrigger, db: Session = Depends(get_db)):
    """
    Simulate a vehicle smart chip triggering an accident.
    Saves the accident, updates vehicle location & status, auto-assigns nearest
    police/hospital stations, broadcasts over WebSockets, and dispatches SMS alerts.
    """
    # 1. Verify and update vehicle status
    vehicle = db.query(Vehicle).filter(Vehicle.id == payload.vehicle_id).first()
    if not vehicle:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Vehicle with ID {payload.vehicle_id} is not registered in the system."
        )
    
    vehicle.status = "accident"
    vehicle.latitude = payload.latitude
    vehicle.longitude = payload.longitude
    
    # 2. Get readable location address
    address = reverse_geocode(payload.latitude, payload.longitude)
    
    # 3. Find closest police and hospital units
    stations = db.query(Station).all()
    assigned_police_id = None
    assigned_hospital_id = None
    nearest_police = None
    nearest_hospital = None
    min_police_dist = float('inf')
    min_hospital_dist = float('inf')
    
    for s in stations:
        dist = haversine_distance(payload.latitude, payload.longitude, s.latitude, s.longitude)
        if s.type == "police":
            if dist < min_police_dist:
                min_police_dist = dist
                assigned_police_id = s.id
                nearest_police = s
        elif s.type == "hospital":
            if dist < min_hospital_dist:
                min_hospital_dist = dist
                assigned_hospital_id = s.id
                nearest_hospital = s

    # 4. Save Accident Report
    response_policy = get_response_policy(payload.severity)
    sensor_payload = payload.sensor_data.model_dump()
    sensor_payload["response_policy"] = response_policy["action"]

    new_accident = Accident(
        vehicle_id=payload.vehicle_id,
        latitude=payload.latitude,
        longitude=payload.longitude,
        location_address=address,
        severity=payload.severity,
        sensor_data=sensor_payload,
        police_status=response_policy["police_status"],
        hospital_status=response_policy["hospital_status"],
        assigned_police_id=assigned_police_id,
        assigned_hospital_id=assigned_hospital_id,
        timestamp=datetime.datetime.utcnow()
    )
    db.add(new_accident)
    db.commit()
    db.refresh(new_accident)

    # Create trackable responder jobs for acknowledgement, ETA, and escalation.
    db.add_all([
        DispatchEvent(accident_id=new_accident.id, agency_type="police", status="pending"),
        DispatchEvent(accident_id=new_accident.id, agency_type="hospital", status="pending"),
    ])
    db.commit()
    
    # Load associated vehicle details for relationship lookups in API responses
    new_accident.vehicle = vehicle
    new_accident.assigned_police = nearest_police
    new_accident.assigned_hospital = nearest_hospital
    
    # 5. Broadcast WebSocket alert to all logged-in operations dashboard clients
    event_payload = {
        "event": "new_accident",
        "data": {
            "id": new_accident.id,
            "vehicle_id": vehicle.id,
            "plate_number": vehicle.plate_number,
            "vehicle_type": vehicle.type,
            "owner_name": vehicle.owner_name,
            "owner_phone": vehicle.owner_phone,
            "latitude": new_accident.latitude,
            "longitude": new_accident.longitude,
            "location_address": new_accident.location_address,
            "severity": new_accident.severity,
            "sensor_data": new_accident.sensor_data,
            "timestamp": new_accident.timestamp.isoformat(),
            "police_status": new_accident.police_status,
            "hospital_status": new_accident.hospital_status,
            "assigned_police": {
                "id": nearest_police.id,
                "name": nearest_police.name,
                "phone": nearest_police.phone,
                "address": nearest_police.address
            } if nearest_police else None,
            "assigned_hospital": {
                "id": nearest_hospital.id,
                "name": nearest_hospital.name,
                "phone": nearest_hospital.phone,
                "address": nearest_hospital.address
            } if nearest_hospital else None,
        }
    }
    
    # Broadcast async to websockets
    asyncio.run(manager.broadcast(event_payload))
    
    # 6. Fetch emergency/home contacts for the vehicle and send Twilio SMS
    contacts = db.query(EmergencyContact).filter(EmergencyContact.vehicle_id == vehicle.id).all()
    timestamp_str = new_accident.timestamp.strftime("%d/%m/%Y at %I:%M %p")
    
    # Family/Home Alert SMS
    family_message = (
        f"ALERT: Your vehicle {vehicle.plate_number} has reported an accident signal at "
        f"{new_accident.location_address} on {timestamp_str}. "
        f"Severity: {new_accident.severity.upper()}.\n"
        f"{response_policy['family_text']}\n"
        f"Please contact emergency services immediately. Helpline: 112"
    )
    for c in contacts:
        send_sms(c.phone, family_message)
        # Log Alert to alerts table
        db_alert = Alert(
            accident_id=new_accident.id,
            recipient_name=c.name,
            recipient_phone=c.phone,
            type="sms",
            message_text=family_message,
            status="sent"
        )
        db.add(db_alert)
        
    # Police Station SMS or verification call record
    if nearest_police:
        police_message = (
            f"{response_policy['responder_text']} Location: {new_accident.location_address} "
            f"({new_accident.latitude:.4f}, {new_accident.longitude:.4f}). "
            f"Vehicle: {vehicle.plate_number} ({vehicle.type.upper()}), Severity: {new_accident.severity.upper()}. "
            f"Telemetry: Speed {payload.sensor_data.speed_at_impact} km/h, Force {payload.sensor_data.impact_force} N."
        )
        alert_type = "call" if response_policy["action"].startswith("confirmation_call") else "sms"
        if alert_type == "sms":
            send_sms(nearest_police.phone, police_message)
        db.add(Alert(
            accident_id=new_accident.id,
            recipient_name=nearest_police.name,
            recipient_phone=nearest_police.phone,
            type=alert_type,
            message_text=police_message,
            status="sent"
        ))
        
    # Hospital SMS or verification call record
    if nearest_hospital:
        hospital_message = (
            f"{response_policy['responder_text']} Medical desk: verify victim condition. "
            f"Location: {new_accident.location_address} ({new_accident.latitude:.4f}, {new_accident.longitude:.4f}). "
            f"Vehicle: {vehicle.plate_number}, Severity: {new_accident.severity.upper()}. "
            f"Telemetry: Speed {payload.sensor_data.speed_at_impact} km/h, Force {payload.sensor_data.impact_force} N."
        )
        alert_type = "call" if response_policy["action"].startswith("confirmation_call") else "sms"
        if alert_type == "sms":
            send_sms(nearest_hospital.phone, hospital_message)
        db.add(Alert(
            accident_id=new_accident.id,
            recipient_name=nearest_hospital.name,
            recipient_phone=nearest_hospital.phone,
            type=alert_type,
            message_text=hospital_message,
            status="sent"
        ))
        
    # 7. Push Notifications simulation to field officers
    officer_push_token = "simulation_field_token_device"
    push_title = f"{response_policy['push_title']} - {new_accident.severity.upper()}"
    push_body = f"{response_policy['push_body']} Vehicle {vehicle.plate_number} at {new_accident.location_address}."
    send_push_notification(officer_push_token, push_title, push_body, {"accident_id": str(new_accident.id)})
    
    db.add(Alert(
        accident_id=new_accident.id,
        recipient_name="Field Officers (Push)",
        recipient_phone="N/A",
        type="push",
        message_text=f"Title: {push_title} | Body: {push_body}",
        status="sent"
    ))

    db.commit()
    return new_accident


@router.get("", response_model=List[AccidentOut])
def get_all_accidents(
    db: Session = Depends(get_db), 
    severity: Optional[str] = None, 
    status: Optional[str] = None, 
    current_user = Depends(get_current_user)
):
    """
    Get all accidents. Supports filtering by severity level and responder status.
    Government authorized only.
    """
    if current_user.role == "public":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Use the family status endpoint for public accounts.")

    query = db.query(Accident)
    
    # Filter by user role jurisdiction
    if current_user.role == "police" and current_user.station_name:
        # Filter accidents assigned to this police station
        station = db.query(Station).filter(Station.name == current_user.station_name).first()
        if station:
            query = query.filter(Accident.assigned_police_id == station.id)
            
    elif current_user.role == "hospital" and current_user.station_name:
        # Filter accidents assigned to this hospital
        station = db.query(Station).filter(Station.name == current_user.station_name).first()
        if station:
            query = query.filter(Accident.assigned_hospital_id == station.id)
            
    if severity:
        query = query.filter(Accident.severity == severity)
        
    if status:
        # Map generic status filter
        if status == "pending":
            query = query.filter((Accident.police_status == "pending") | (Accident.hospital_status == "pending"))
        elif status == "dispatched":
            query = query.filter((Accident.police_status == "dispatched") | (Accident.hospital_status == "dispatched"))
        elif status == "resolved":
            query = query.filter(Accident.police_status == "resolved", Accident.hospital_status == "treated")

    return query.order_by(Accident.timestamp.desc()).all()


@router.get("/family", response_model=List[FamilyAccidentOut])
def get_family_accidents(db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    """Return only incidents for vehicles linked to the signed-in family contact."""
    if current_user.role != "public":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="This endpoint is for public family accounts.")

    return [
        FamilyAccidentOut(
            id=accident.id,
            vehicle_plate=vehicle.plate_number,
            location_address=accident.location_address,
            latitude=accident.latitude,
            longitude=accident.longitude,
            severity=accident.severity,
            police_status=accident.police_status,
            hospital_status=accident.hospital_status,
            timestamp=accident.timestamp,
        )
        for accident, vehicle in (
            db.query(Accident, Vehicle)
            .join(PublicFamilyAccess, PublicFamilyAccess.vehicle_id == Accident.vehicle_id)
            .join(Vehicle, Vehicle.id == Accident.vehicle_id)
            .filter(PublicFamilyAccess.user_id == current_user.id)
            .order_by(Accident.timestamp.desc())
            .all()
        )
    ]


@router.get("/{id}", response_model=AccidentOut)
def get_accident_by_id(id: int, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    """
    Retrieve full details of a specific accident report.
    """
    accident = db.query(Accident).filter(Accident.id == id).first()
    if not accident:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Accident report not found."
        )
    if current_user.role == "public":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Use the family status endpoint for public accounts.")
    return accident


@router.patch("/{id}/police-status", response_model=AccidentOut)
def update_police_status(
    id: int, 
    update: AccidentPoliceStatusUpdate, 
    db: Session = Depends(get_db), 
    current_user = Depends(require_responder)
):
    """
    Updates the police response dispatch status.
    If the status is marked as 'resolved' and hospital is 'treated', the vehicle status is set back to 'on_road'.
    """
    accident = db.query(Accident).filter(Accident.id == id).first()
    if not accident:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Accident report not found."
        )
        
    accident.police_status = update.police_status
    if update.police_status == "resolved":
        dispatch = db.query(DispatchEvent).filter(
            DispatchEvent.accident_id == id,
            DispatchEvent.agency_type == "police"
        ).first()
        if dispatch:
            dispatch.status = "completed"
    if update.assigned_police_id:
        accident.assigned_police_id = update.assigned_police_id
        
    # Check if accident is fully cleared by both responders
    if accident.police_status == "resolved" and accident.hospital_status == "treated":
        vehicle = db.query(Vehicle).filter(Vehicle.id == accident.vehicle_id).first()
        if vehicle:
            vehicle.status = "on_road"
            
    db.commit()
    db.refresh(accident)
    
    # Broadcast status change via WebSocket
    event_payload = {
        "event": "status_update",
        "data": {
            "id": accident.id,
            "police_status": accident.police_status,
            "hospital_status": accident.hospital_status,
            "vehicle_status": "on_road" if (accident.police_status == "resolved" and accident.hospital_status == "treated") else "accident"
        }
    }
    asyncio.run(manager.broadcast(event_payload))
    
    return accident


@router.patch("/{id}/hospital-status", response_model=AccidentOut)
def update_hospital_status(
    id: int, 
    update: AccidentHospitalStatusUpdate, 
    db: Session = Depends(get_db), 
    current_user = Depends(require_responder)
):
    """
    Updates the medical/hospital response status.
    If status is marked as 'treated' and police is 'resolved', the vehicle status is set back to 'on_road'.
    """
    accident = db.query(Accident).filter(Accident.id == id).first()
    if not accident:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Accident report not found."
        )
        
    accident.hospital_status = update.hospital_status
    if update.hospital_status == "treated":
        dispatch = db.query(DispatchEvent).filter(
            DispatchEvent.accident_id == id,
            DispatchEvent.agency_type == "hospital"
        ).first()
        if dispatch:
            dispatch.status = "completed"
    if update.assigned_hospital_id:
        accident.assigned_hospital_id = update.assigned_hospital_id
        
    # Check if accident is fully cleared by both responders
    if accident.police_status == "resolved" and accident.hospital_status == "treated":
        vehicle = db.query(Vehicle).filter(Vehicle.id == accident.vehicle_id).first()
        if vehicle:
            vehicle.status = "on_road"
            
    db.commit()
    db.refresh(accident)
    
    # Broadcast status change via WebSocket
    event_payload = {
        "event": "status_update",
        "data": {
            "id": accident.id,
            "police_status": accident.police_status,
            "hospital_status": accident.hospital_status,
            "vehicle_status": "on_road" if (accident.police_status == "resolved" and accident.hospital_status == "treated") else "accident"
        }
    }
    asyncio.run(manager.broadcast(event_payload))
    
    return accident
