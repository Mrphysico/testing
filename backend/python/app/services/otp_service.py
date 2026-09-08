import secrets
from datetime import datetime, timedelta
from typing import Tuple
from sqlalchemy.orm import Session
from app.models import OtpVerification


def generate_otp(length: int = 6) -> str:
    """
    Generates a cryptographically secure numeric OTP of the specified length.
    """
    digits = "0123456789"
    return "".join(secrets.choice(digits) for _ in range(length))


def save_otp(
    db: Session,
    email: str,
    phone: str,
    otp_code: str,
    purpose: str = "signup",
    expire_minutes: int = 10
) -> OtpVerification:
    """
    Persists a newly generated OTP into the database with an expiration window.
    Any existing unused OTPs for the same email and purpose are marked expired/superseded.
    """
    normalized_email = email.strip().lower()
    
    # Mark old unverified OTPs as invalidated
    old_otps = db.query(OtpVerification).filter(
        OtpVerification.email == normalized_email,
        OtpVerification.purpose == purpose,
        OtpVerification.is_verified == False
    ).all()
    for item in old_otps:
        item.is_verified = True  # Invalidate previous unused codes
        
    expires_at = datetime.utcnow() + timedelta(minutes=expire_minutes)
    record = OtpVerification(
        email=normalized_email,
        phone=phone.strip(),
        otp_code=otp_code.strip(),
        purpose=purpose,
        is_verified=False,
        expires_at=expires_at,
        created_at=datetime.utcnow()
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def verify_otp(
    db: Session,
    email: str,
    otp_code: str,
    purpose: str = "signup"
) -> Tuple[bool, str]:
    """
    Verifies an incoming OTP code against the latest stored unverified record.
    Returns (is_valid: bool, error_message: str).
    """
    normalized_email = email.strip().lower()
    clean_code = otp_code.strip()

    record = (
        db.query(OtpVerification)
        .filter(
            OtpVerification.email == normalized_email,
            OtpVerification.purpose == purpose,
            OtpVerification.is_verified == False
        )
        .order_by(OtpVerification.created_at.desc())
        .first()
    )

    if not record:
        return False, "No active verification code found for this email. Please request a new OTP."

    if record.expires_at < datetime.utcnow():
        return False, "Verification code has expired. Please request a new OTP."

    if record.otp_code != clean_code:
        return False, "Invalid OTP code. Please check and try again."

    # Mark as verified/consumed
    record.is_verified = True
    db.commit()
    return True, "Verification successful."
