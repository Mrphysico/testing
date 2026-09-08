from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app.models import EmergencyContact, Vehicle
from app.schemas import EmergencyContactCreate, EmergencyContactOut
from app.auth import require_responder

router = APIRouter(prefix="/emergency-contacts", tags=["emergency-contacts"])

@router.post("", response_model=EmergencyContactOut, status_code=status.HTTP_201_CREATED)
def create_emergency_contact(contact_in: EmergencyContactCreate, db: Session = Depends(get_db), current_user = Depends(require_responder)):
    """
    Link a new home/emergency contact to a vehicle.
    """
    vehicle = db.query(Vehicle).filter(Vehicle.id == contact_in.vehicle_id).first()
    if not vehicle:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Vehicle with ID {contact_in.vehicle_id} does not exist."
        )
        
    new_contact = EmergencyContact(
        vehicle_id=contact_in.vehicle_id,
        name=contact_in.name,
        phone=contact_in.phone,
        relation=contact_in.relation,
        address=contact_in.address
    )
    
    db.add(new_contact)
    db.commit()
    db.refresh(new_contact)
    return new_contact


@router.get("/{vehicle_id}", response_model=List[EmergencyContactOut])
def get_contacts_for_vehicle(vehicle_id: int, db: Session = Depends(get_db), current_user = Depends(require_responder)):
    """
    Get all home emergency contacts linked to a specific vehicle.
    """
    contacts = db.query(EmergencyContact).filter(EmergencyContact.vehicle_id == vehicle_id).all()
    return contacts


@router.delete("/{id}", status_code=status.HTTP_200_OK)
def remove_emergency_contact(id: int, db: Session = Depends(get_db), current_user = Depends(require_responder)):
    """
    Delete/unlink an emergency contact.
    """
    contact = db.query(EmergencyContact).filter(EmergencyContact.id == id).first()
    if not contact:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Contact not found."
        )
        
    db.delete(contact)
    db.commit()
    return {"message": "Emergency contact successfully unlinked."}
