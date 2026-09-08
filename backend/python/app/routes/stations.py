from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
import math

from app.database import get_db
from app.models import Station
from app.schemas import StationCreate, StationOut
from app.auth import require_responder

router = APIRouter(prefix="/stations", tags=["stations"])

def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate the great-circle distance between two points on the Earth 
    surface in kilometers using the Haversine formula.
    """
    # Convert latitude and longitude to radians
    d_lat = math.radians(lat2 - lat1)
    d_lon = math.radians(lon2 - lon1)
    
    a = (math.sin(d_lat / 2) ** 2 + 
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * 
         math.sin(d_lon / 2) ** 2)
    
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    earth_radius_km = 6371.0
    return earth_radius_km * c


@router.post("", response_model=StationOut, status_code=status.HTTP_201_CREATED)
def create_station(station_in: StationCreate, db: Session = Depends(get_db), current_user = Depends(require_responder)):
    """
    Register a new Police Station or Hospital.
    Government authorized only.
    """
    new_station = Station(
        name=station_in.name,
        type=station_in.type,
        address=station_in.address,
        latitude=station_in.latitude,
        longitude=station_in.longitude,
        jurisdiction_area=station_in.jurisdiction_area,
        phone=station_in.phone
    )
    db.add(new_station)
    db.commit()
    db.refresh(new_station)
    return new_station


@router.get("", response_model=List[StationOut])
def get_all_stations(db: Session = Depends(get_db), current_user = Depends(require_responder)):
    """
    Get all registered stations.
    """
    return db.query(Station).all()


@router.get("/nearest")
def get_nearest_stations(latitude: float, longitude: float, db: Session = Depends(get_db)):
    """
    Get the nearest police station and hospital for given coordinates.
    Used during telemetry trigger to auto-route alerts.
    """
    stations = db.query(Station).all()
    if not stations:
        return {"police": None, "hospital": None}
        
    nearest_police = None
    nearest_hospital = None
    min_police_dist = float('inf')
    min_hospital_dist = float('inf')
    
    for s in stations:
        dist = haversine_distance(latitude, longitude, s.latitude, s.longitude)
        if s.type == "police":
            if dist < min_police_dist:
                min_police_dist = dist
                nearest_police = {
                    "station": s,
                    "distance_km": round(dist, 2)
                }
        elif s.type == "hospital":
            if dist < min_hospital_dist:
                min_hospital_dist = dist
                nearest_hospital = {
                    "station": s,
                    "distance_km": round(dist, 2)
                }
                
    return {
        "police": nearest_police,
        "hospital": nearest_hospital
    }
