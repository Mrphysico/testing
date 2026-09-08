from pydantic import BaseModel, EmailStr, Field, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime

# ==========================================
# AUTHENTICATION & USERS
# ==========================================
class UserBase(BaseModel):
    name: str
    email: EmailStr
    role: str = Field(..., description="superadmin, police, or hospital")
    phone: str
    station_name: Optional[str] = None
    station_address: Optional[str] = None
    jurisdiction_area: Optional[str] = None

class UserCreate(UserBase):
    password: str

class UserUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    role: Optional[str] = None
    phone: Optional[str] = None
    station_name: Optional[str] = None
    station_address: Optional[str] = None
    jurisdiction_area: Optional[str] = None

class PasswordChange(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=6)

class AdminPasswordReset(BaseModel):
    new_password: str = Field(..., min_length=6)

class UserOut(UserBase):
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class UserLogin(BaseModel):
    email: EmailStr
    password: str


class PublicSignup(BaseModel):
    name: str = Field(..., min_length=2)
    email: EmailStr
    password: str = Field(..., min_length=6)
    phone: str = Field(..., min_length=6)
    plate_number: str = Field(..., min_length=3)

class SignupOtpRequest(BaseModel):
    name: str = Field(..., min_length=2)
    email: EmailStr
    phone: str = Field(..., min_length=6)
    plate_number: str = Field(..., min_length=3)

class SignupOtpVerify(BaseModel):
    name: str = Field(..., min_length=2)
    email: EmailStr
    password: str = Field(..., min_length=6)
    phone: str = Field(..., min_length=6)
    plate_number: str = Field(..., min_length=3)
    otp_code: str = Field(..., min_length=4, max_length=10)

class OtpResponse(BaseModel):
    message: str
    email: str
    phone: str
    dev_otp: Optional[str] = None

class Token(BaseModel):
    access_token: str
    token_type: str
    user: UserOut

class TokenData(BaseModel):
    email: Optional[str] = None
    role: Optional[str] = None


# ==========================================
# VEHICLES
# ==========================================
class VehicleBase(BaseModel):
    owner_name: str
    owner_phone: str
    owner_address: str
    type: str = Field(..., description="car, bus, or truck")
    plate_number: str
    status: str = "on_road"  # 'on_road', 'accident', 'parked'
    latitude: float
    longitude: float

class VehicleCreate(VehicleBase):
    pass

class VehicleOut(VehicleBase):
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class VehicleLocationUpdate(BaseModel):
    latitude: float
    longitude: float
    status: Optional[str] = None

# ==========================================
# EMERGENCY CONTACTS
# ==========================================
class EmergencyContactBase(BaseModel):
    name: str
    phone: str
    relation: str
    address: str

class EmergencyContactCreate(EmergencyContactBase):
    vehicle_id: int

class EmergencyContactOut(EmergencyContactBase):
    id: int
    vehicle_id: int

    model_config = ConfigDict(from_attributes=True)

# ==========================================
# STATIONS
# ==========================================
class StationBase(BaseModel):
    name: str
    type: str = Field(..., description="police or hospital")
    address: str
    latitude: float
    longitude: float
    jurisdiction_area: Optional[str] = None
    phone: str

class StationCreate(StationBase):
    pass

class StationOut(StationBase):
    id: int

    model_config = ConfigDict(from_attributes=True)

# ==========================================
# ACCIDENTS
# ==========================================
class SensorDataSchema(BaseModel):
    impact_force: float = Field(..., description="Force in Newtons")
    gyroscope_x: float
    gyroscope_y: float
    speed_at_impact: float = Field(..., description="Speed in km/h")

class AccidentTrigger(BaseModel):
    vehicle_id: int
    latitude: float
    longitude: float
    sensor_data: SensorDataSchema
    severity: str = Field(..., description="low, medium, high, critical")

class AccidentOut(BaseModel):
    id: int
    vehicle_id: int
    latitude: float
    longitude: float
    location_address: str
    severity: str
    sensor_data: Dict[str, Any]
    police_status: str
    hospital_status: str
    assigned_police_id: Optional[int] = None
    assigned_hospital_id: Optional[int] = None
    timestamp: datetime
    
    # Detailed vehicle and station outputs in standard API responses
    vehicle: Optional[VehicleOut] = None
    assigned_police: Optional[StationOut] = None
    assigned_hospital: Optional[StationOut] = None

    model_config = ConfigDict(from_attributes=True)


class FamilyAccidentOut(BaseModel):
    id: int
    vehicle_plate: str
    location_address: str
    latitude: float
    longitude: float
    severity: str
    police_status: str
    hospital_status: str
    timestamp: datetime

class AccidentPoliceStatusUpdate(BaseModel):
    police_status: str = Field(..., description="pending, dispatched, resolved")
    assigned_police_id: Optional[int] = None

class AccidentHospitalStatusUpdate(BaseModel):
    hospital_status: str = Field(..., description="pending, dispatched, treated")
    assigned_hospital_id: Optional[int] = None

# ==========================================
# ALERTS
# ==========================================
class AlertBase(BaseModel):
    recipient_name: str
    recipient_phone: str
    type: str = Field(..., description="sms, call, or push")
    message_text: str
    status: str = "sent"

class AlertCreate(BaseModel):
    accident_id: int
    recipient_name: str
    recipient_phone: str
    type: str
    message_text: str

class AlertOut(AlertBase):
    id: int
    accident_id: int
    sent_at: datetime

    model_config = ConfigDict(from_attributes=True)

class ManualAlertSend(BaseModel):
    accident_id: int
    recipient_phone: str
    message_text: str
