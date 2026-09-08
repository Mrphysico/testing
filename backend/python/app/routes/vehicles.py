from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app.models import Vehicle, EmergencyContact
from app.schemas import VehicleCreate, VehicleOut, VehicleLocationUpdate
from app.auth import require_responder

router = APIRouter(prefix="/vehicles", tags=["vehicles"])

@router.post("", response_model=VehicleOut, status_code=status.HTTP_201_CREATED)
def register_vehicle(vehicle_in: VehicleCreate, db: Session = Depends(get_db), current_user = Depends(require_responder)):
    """
    Onboard a new vehicle with owner details.
    Government authorized only.
    """
    db_vehicle = db.query(Vehicle).filter(Vehicle.plate_number == vehicle_in.plate_number).first()
    if db_vehicle:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Vehicle with this plate number is already registered."
        )
        
    new_vehicle = Vehicle(
        owner_name=vehicle_in.owner_name,
        owner_phone=vehicle_in.owner_phone,
        owner_address=vehicle_in.owner_address,
        type=vehicle_in.type,
        plate_number=vehicle_in.plate_number,
        status=vehicle_in.status,
        latitude=vehicle_in.latitude,
        longitude=vehicle_in.longitude
    )
    
    db.add(new_vehicle)
    db.commit()
    db.refresh(new_vehicle)
    return new_vehicle


@router.get("", response_model=List[VehicleOut])
def get_all_vehicles(db: Session = Depends(get_db), current_user = Depends(require_responder)):
    """
    Fetch all registered vehicles.
    Government authorized only.
    """
    return db.query(Vehicle).all()


@router.get("/live")
def get_live_locations(db: Session = Depends(get_db), current_user = Depends(require_responder)):
    """
    Fetch live locations of all vehicles. Used by operations maps.
    """
    vehicles = db.query(Vehicle).all()
    return [
        {
            "id": v.id,
            "plate_number": v.plate_number,
            "owner_name": v.owner_name,
            "type": v.type,
            "status": v.status,
            "latitude": v.latitude,
            "longitude": v.longitude,
            "last_updated": datetime.utcnow() if hasattr(v, 'updated_at') else None
        }
        for v in vehicles
    ]


@router.patch("/{id}/location", response_model=VehicleOut)
def update_vehicle_location(id: int, update: VehicleLocationUpdate, db: Session = Depends(get_db)):
    """
    Update vehicle location and status.
    No JWT required here to facilitate low-overhead IoT/chip telemetry scripts.
    """
    vehicle = db.query(Vehicle).filter(Vehicle.id == id).first()
    if not vehicle:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vehicle not found."
        )
        
    vehicle.latitude = update.latitude
    vehicle.longitude = update.longitude
    if update.status:
        vehicle.status = update.status
        
    db.commit()
    db.refresh(vehicle)
    return vehicle


@router.get("/{id}")
def get_vehicle_details(id: int, db: Session = Depends(get_db), current_user = Depends(require_responder)):
    """
    Fetch full details of a vehicle and its emergency/home contacts.
    """
    vehicle = db.query(Vehicle).filter(Vehicle.id == id).first()
    if not vehicle:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vehicle not found."
        )
        
    contacts = db.query(EmergencyContact).filter(EmergencyContact.vehicle_id == id).all()
    
    return {
        "id": vehicle.id,
        "owner_name": vehicle.owner_name,
        "owner_phone": vehicle.owner_phone,
        "owner_address": vehicle.owner_address,
        "type": vehicle.type,
        "plate_number": vehicle.plate_number,
        "status": vehicle.status,
        "latitude": vehicle.latitude,
        "longitude": vehicle.longitude,
        "created_at": vehicle.created_at,
        "emergency_contacts": contacts
    }

# Small inline import to fix datetime reference
from datetime import datetime
