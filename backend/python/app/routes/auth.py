from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
import datetime

from app.database import get_db
from app.models import EmergencyContact, PublicFamilyAccess, User, Vehicle
from app.schemas import (
    AdminPasswordReset,
    PasswordChange,
    UserCreate,
    UserLogin,
    UserOut,
    PublicSignup,
    SignupOtpRequest,
    SignupOtpVerify,
    OtpResponse,
    UserUpdate,
    Token,
)
from app.auth import get_password_hash, verify_password, create_access_token, get_current_user, require_superadmin
from app.config import settings
from app.services.email_service import send_otp_email, send_welcome_email
from app.services.otp_service import generate_otp, save_otp, verify_otp
from app.services.notification import send_sms

router = APIRouter(prefix="/auth", tags=["auth"])

VALID_ROLES = {"superadmin", "police", "hospital"}


def normalize_phone(phone: str) -> str:
    return "".join(character for character in phone if character.isdigit())


@router.get("/users", response_model=list[UserOut])
def list_users(db: Session = Depends(get_db), current_user: User = Depends(require_superadmin)):
    """
    List all government official accounts.
    Restricted to Super Admin users.
    """
    return db.query(User).order_by(User.created_at.desc()).all()

@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def register_user(user_in: UserCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """
    Register a new government official account.
    Restricted to Super Admin users.
    """
    # Verify authorization (only superadmin can register new users)
    if current_user.role != "superadmin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only Super Admins can register new accounts."
        )
    if user_in.role not in VALID_ROLES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Role must be one of: superadmin, police, hospital."
        )

    # Check if user already exists
    db_user = db.query(User).filter(User.email == user_in.email).first()
    if db_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered."
        )
    
    # Create the user
    hashed_password = get_password_hash(user_in.password)
    new_user = User(
        name=user_in.name,
        email=user_in.email,
        password_hash=hashed_password,
        role=user_in.role,
        station_name=user_in.station_name,
        station_address=user_in.station_address,
        jurisdiction_area=user_in.jurisdiction_area,
        phone=user_in.phone
    )
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user


@router.patch("/users/{user_id}", response_model=UserOut)
def update_user(
    user_id: int,
    user_in: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_superadmin),
):
    """
    Update a government official account profile.
    Restricted to Super Admin users.
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User account not found.")

    updates = user_in.model_dump(exclude_unset=True)
    if "role" in updates and updates["role"] not in VALID_ROLES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Role must be one of: superadmin, police, hospital."
        )
    if "email" in updates:
        existing = db.query(User).filter(User.email == updates["email"], User.id != user_id).first()
        if existing:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered.")

    for key, value in updates.items():
        setattr(user, key, value)

    db.commit()
    db.refresh(user)
    return user


@router.patch("/users/{user_id}/password")
def reset_user_password(
    user_id: int,
    payload: AdminPasswordReset,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_superadmin),
):
    """
    Reset a government official account password.
    Restricted to Super Admin users.
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User account not found.")
    user.password_hash = get_password_hash(payload.new_password)
    db.commit()
    return {"message": "Password reset successfully."}


@router.delete("/users/{user_id}")
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_superadmin),
):
    """
    Delete a government official account.
    Restricted to Super Admin users.
    """
    if current_user.id == user_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="You cannot delete your own account.")
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User account not found.")
    db.delete(user)
    db.commit()
    return {"message": "User account deleted."}


@router.patch("/change-password")
def change_my_password(
    payload: PasswordChange,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Change the currently logged-in official's password.
    """
    if not verify_password(payload.current_password, current_user.password_hash):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Current password is incorrect.")
    current_user.password_hash = get_password_hash(payload.new_password)
    db.commit()
    return {"message": "Password changed successfully."}


@router.post("/bootstrap-superadmin", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def bootstrap_superadmin(user_in: UserCreate, db: Session = Depends(get_db)):
    """
    Bootstrap endpoint to create the very first Super Admin account
    if no users exist in the database.
    """
    user_count = db.query(User).count()
    if user_count > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="System is already bootstrapped. Please log in as Super Admin."
        )
        
    hashed_password = get_password_hash(user_in.password)
    new_user = User(
        name=user_in.name,
        email=user_in.email,
        password_hash=hashed_password,
        role="superadmin",
        phone=user_in.phone
    )
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user


@router.post("/login", response_model=Token)
def login(credentials: UserLogin, db: Session = Depends(get_db)):
    """
    Official JWT Login for government personnel.
    """
    user = db.query(User).filter(User.email == credentials.email).first()
    if not user or not verify_password(credentials.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Create access token
    access_token_expires = datetime.timedelta(minutes=1440)  # 24 hours
    access_token = create_access_token(
        data={"sub": user.email, "role": user.role}, 
        expires_delta=access_token_expires
    )
    
    return {
        "access_token": access_token, 
        "token_type": "bearer",
        "user": user
    }


@router.post("/send-signup-otp", response_model=OtpResponse)
def send_signup_otp(payload: SignupOtpRequest, db: Session = Depends(get_db)):
    """
    Validates family vehicle and phone match, generates a 6-digit OTP,
    and dispatches it to the user's email and phone.
    """
    normalized_email = payload.email.strip().lower()
    if db.query(User).filter(User.email == normalized_email).first():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered. Please log in.")

    vehicle = db.query(Vehicle).filter(Vehicle.plate_number == payload.plate_number.upper().strip()).first()
    if not vehicle:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No registered vehicle matches plate '{payload.plate_number.upper().strip()}'.",
        )

    requested_phone = normalize_phone(payload.phone)
    contact = next(
        (item for item in db.query(EmergencyContact).filter(EmergencyContact.vehicle_id == vehicle.id).all()
         if normalize_phone(item.phone) == requested_phone),
        None,
    )
    if not contact:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="The provided phone number is not registered as an emergency contact for this vehicle.",
        )

    # Generate OTP code
    otp_code = generate_otp(6)
    save_otp(db, email=normalized_email, phone=payload.phone, otp_code=otp_code, purpose="signup", expire_minutes=10)

    # Send OTP via Email
    send_otp_email(to_email=normalized_email, name=payload.name, otp_code=otp_code)

    # Send OTP via SMS
    send_sms(
        to_phone=payload.phone,
        message=f"Government Emergency Portal: Your verification OTP is {otp_code}. Valid for 10 mins. Dial 112 for emergency."
    )

    dev_otp_val = otp_code if settings.DEV_SHOW_OTP else None
    return {
        "message": f"Verification OTP successfully sent to {normalized_email} and {payload.phone}.",
        "email": normalized_email,
        "phone": payload.phone,
        "dev_otp": dev_otp_val
    }


@router.post("/verify-signup-otp", response_model=Token, status_code=status.HTTP_201_CREATED)
def verify_signup_otp(payload: SignupOtpVerify, db: Session = Depends(get_db)):
    """
    Verifies the 6-digit OTP code, registers the user account, links vehicle access,
    and sends a Signup Successful confirmation email.
    """
    normalized_email = payload.email.strip().lower()
    if db.query(User).filter(User.email == normalized_email).first():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered.")

    vehicle = db.query(Vehicle).filter(Vehicle.plate_number == payload.plate_number.upper().strip()).first()
    if not vehicle:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No registered family vehicle matches that plate number.")

    requested_phone = normalize_phone(payload.phone)
    contact = next(
        (item for item in db.query(EmergencyContact).filter(EmergencyContact.vehicle_id == vehicle.id).all()
         if normalize_phone(item.phone) == requested_phone),
        None,
    )
    if not contact:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Use the phone number registered as this vehicle's emergency family contact.",
        )

    # Verify the OTP code
    is_valid, err_msg = verify_otp(db, email=normalized_email, otp_code=payload.otp_code, purpose="signup")
    if not is_valid:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=err_msg)

    # Create the user
    user = User(
        name=payload.name.strip(),
        email=normalized_email,
        password_hash=get_password_hash(payload.password),
        role="public",
        phone=payload.phone.strip(),
    )
    db.add(user)
    db.flush()

    access = db.query(PublicFamilyAccess).filter(
        PublicFamilyAccess.user_id == user.id,
        PublicFamilyAccess.vehicle_id == vehicle.id
    ).first()
    if access:
        access.contact_name = contact.name
        access.relation = contact.relation
    else:
        db.add(PublicFamilyAccess(
            user_id=user.id,
            vehicle_id=vehicle.id,
            contact_name=contact.name,
            relation=contact.relation,
        ))
    db.commit()
    db.refresh(user)

    # Send Welcome / Signup Successful confirmation email
    send_welcome_email(
        to_email=user.email,
        name=user.name,
        plate_number=vehicle.plate_number,
        contact_name=contact.name,
        relation=contact.relation
    )

    access_token = create_access_token(
        data={"sub": user.email, "role": user.role},
        expires_delta=datetime.timedelta(minutes=1440),
    )
    return {"access_token": access_token, "token_type": "bearer", "user": user}


@router.post("/public-signup", response_model=Token, status_code=status.HTTP_201_CREATED)
def public_signup(payload: PublicSignup, db: Session = Depends(get_db)):
    """Create a public account only when its phone matches a registered family contact."""
    if db.query(User).filter(User.email == payload.email).first():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered.")

    vehicle = db.query(Vehicle).filter(Vehicle.plate_number == payload.plate_number.upper()).first()
    if not vehicle:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No registered family vehicle matches that plate number.")

    requested_phone = normalize_phone(payload.phone)
    contact = next(
        (item for item in db.query(EmergencyContact).filter(EmergencyContact.vehicle_id == vehicle.id).all()
         if normalize_phone(item.phone) == requested_phone),
        None,
    )
    if not contact:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Use the phone number registered as this vehicle's emergency family contact.",
        )

    user = User(
        name=payload.name,
        email=payload.email,
        password_hash=get_password_hash(payload.password),
        role="public",
        phone=payload.phone,
    )
    db.add(user)
    db.flush()

    access = db.query(PublicFamilyAccess).filter(
        PublicFamilyAccess.user_id == user.id,
        PublicFamilyAccess.vehicle_id == vehicle.id
    ).first()
    if access:
        access.contact_name = contact.name
        access.relation = contact.relation
    else:
        db.add(PublicFamilyAccess(
            user_id=user.id,
            vehicle_id=vehicle.id,
            contact_name=contact.name,
            relation=contact.relation,
        ))
    db.commit()
    db.refresh(user)

    # Also send confirmation email for direct public signup
    send_welcome_email(
        to_email=user.email,
        name=user.name,
        plate_number=vehicle.plate_number,
        contact_name=contact.name,
        relation=contact.relation
    )

    access_token = create_access_token(
        data={"sub": user.email, "role": user.role},
        expires_delta=datetime.timedelta(minutes=1440),
    )
    return {"access_token": access_token, "token_type": "bearer", "user": user}


@router.get("/me", response_model=UserOut)
def get_me(current_user: User = Depends(get_current_user)):
    """
    Retrieve logged-in user profile details.
    """
    return current_user
