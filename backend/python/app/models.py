from sqlalchemy import Boolean, Column, Integer, String, Float, DateTime, ForeignKey, JSON, UniqueConstraint
from sqlalchemy.orm import relationship
import datetime

from app.database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    role = Column(String, nullable=False)  # 'superadmin', 'police', 'hospital', 'public'
    station_name = Column(String, nullable=True)
    station_address = Column(String, nullable=True)
    jurisdiction_area = Column(String, nullable=True)
    phone = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


class Vehicle(Base):
    __tablename__ = "vehicles"

    id = Column(Integer, primary_key=True, index=True)
    owner_name = Column(String, nullable=False)
    owner_phone = Column(String, nullable=False)
    owner_address = Column(String, nullable=False)
    type = Column(String, nullable=False)  # 'car', 'bus', 'truck'
    plate_number = Column(String, unique=True, index=True, nullable=False)
    status = Column(String, default="on_road")  # 'on_road', 'accident', 'parked'
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    # Relationships
    emergency_contacts = relationship("EmergencyContact", back_populates="vehicle", cascade="all, delete-orphan")
    accidents = relationship("Accident", back_populates="vehicle")


class EmergencyContact(Base):
    __tablename__ = "emergency_contacts"

    id = Column(Integer, primary_key=True, index=True)
    vehicle_id = Column(Integer, ForeignKey("vehicles.id", ondelete="CASCADE"), nullable=False)
    name = Column(String, nullable=False)
    phone = Column(String, nullable=False)
    relation = Column(String, nullable=False)
    address = Column(String, nullable=False)

    # Relationships
    vehicle = relationship("Vehicle", back_populates="emergency_contacts")


class PublicFamilyAccess(Base):
    __tablename__ = "public_family_access"
    __table_args__ = (UniqueConstraint("user_id", "vehicle_id", name="uq_public_family_access"),)

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    vehicle_id = Column(Integer, ForeignKey("vehicles.id", ondelete="CASCADE"), nullable=False)
    contact_name = Column(String, nullable=False)
    relation = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


class Accident(Base):
    __tablename__ = "accidents"

    id = Column(Integer, primary_key=True, index=True)
    vehicle_id = Column(Integer, ForeignKey("vehicles.id"), nullable=False)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    location_address = Column(String, nullable=False)
    severity = Column(String, nullable=False)  # 'low', 'medium', 'high', 'critical'
    sensor_data = Column(JSON, nullable=False)  # {impact_force, gyroscope_x, gyroscope_y, speed_at_impact}
    police_status = Column(String, default="pending")  # 'pending', 'dispatched', 'resolved'
    hospital_status = Column(String, default="pending")  # 'pending', 'dispatched', 'treated'
    assigned_police_id = Column(Integer, ForeignKey("stations.id"), nullable=True)
    assigned_hospital_id = Column(Integer, ForeignKey("stations.id"), nullable=True)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)

    # Relationships
    vehicle = relationship("Vehicle", back_populates="accidents")
    assigned_police = relationship("Station", foreign_keys=[assigned_police_id])
    assigned_hospital = relationship("Station", foreign_keys=[assigned_hospital_id])
    alerts = relationship("Alert", back_populates="accident", cascade="all, delete-orphan")


class Alert(Base):
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, index=True)
    accident_id = Column(Integer, ForeignKey("accidents.id", ondelete="CASCADE"), nullable=False)
    recipient_name = Column(String, nullable=False)
    recipient_phone = Column(String, nullable=False)
    type = Column(String, nullable=False)  # 'sms', 'call', 'push'
    message_text = Column(String, nullable=False)
    status = Column(String, default="sent")  # 'sent', 'failed'
    sent_at = Column(DateTime, default=datetime.datetime.utcnow)

    # Relationships
    accident = relationship("Accident", back_populates="alerts")


class Station(Base):
    __tablename__ = "stations"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    type = Column(String, nullable=False)  # 'police', 'hospital'
    address = Column(String, nullable=False)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    jurisdiction_area = Column(String, nullable=True)
    phone = Column(String, nullable=False)


class VehicleDevice(Base):
    __tablename__ = "vehicle_devices"

    id = Column(Integer, primary_key=True, index=True)
    vehicle_id = Column(Integer, ForeignKey("vehicles.id", ondelete="CASCADE"), unique=True, nullable=False)
    device_uid = Column(String, unique=True, index=True, nullable=False)
    api_key_hash = Column(String, nullable=False)
    firmware_version = Column(String, default="1.0.0")
    status = Column(String, default="offline")
    battery_level = Column(Float, default=100.0)
    network_signal = Column(Float, default=0.0)
    last_seen = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


class EmergencyProfile(Base):
    __tablename__ = "emergency_profiles"

    id = Column(Integer, primary_key=True, index=True)
    vehicle_id = Column(Integer, ForeignKey("vehicles.id", ondelete="CASCADE"), unique=True, nullable=False)
    blood_group = Column(String, nullable=True)
    allergies = Column(String, nullable=True)
    medical_conditions = Column(String, nullable=True)
    emergency_notes = Column(String, nullable=True)
    consent_given = Column(Boolean, default=False, nullable=False)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)


class DispatchEvent(Base):
    __tablename__ = "dispatch_events"

    id = Column(Integer, primary_key=True, index=True)
    accident_id = Column(Integer, ForeignKey("accidents.id", ondelete="CASCADE"), nullable=False)
    agency_type = Column(String, nullable=False)
    status = Column(String, default="pending")
    assigned_unit = Column(String, nullable=True)
    acknowledged_by = Column(String, nullable=True)
    acknowledged_at = Column(DateTime, nullable=True)
    eta_minutes = Column(Integer, nullable=True)
    escalation_level = Column(Integer, default=0)
    last_attempt_at = Column(DateTime, default=datetime.datetime.utcnow)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    actor_email = Column(String, nullable=False)
    action = Column(String, nullable=False)
    entity_type = Column(String, nullable=False)
    entity_id = Column(String, nullable=True)
    details = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


class OtpVerification(Base):
    __tablename__ = "otp_verifications"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, index=True, nullable=False)
    phone = Column(String, index=True, nullable=False)
    otp_code = Column(String, nullable=False)
    purpose = Column(String, default="signup", nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

