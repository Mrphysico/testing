from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
import logging
from pathlib import Path

from app.config import settings
from app.database import engine, Base, SessionLocal
from app.models import Accident, DispatchEvent, User, Vehicle, Station, EmergencyContact
from app.auth import get_password_hash
from app.websocket import manager

# Import routers
from app.routes import auth, vehicles, accidents, emergency_contacts, alerts, stations, reports, operations

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("app.main")


def get_frontend_dir() -> Path:
    # Try finding frontend/javascript first, then fallback to frontend
    cur = Path(__file__).resolve()
    for parent in cur.parents:
        js_cand = parent / "frontend" / "javascript"
        if js_cand.exists() and (js_cand / "index.html").exists():
            return js_cand
        cand = parent / "frontend"
        if cand.exists() and (cand / "index.html").exists():
            return cand
    return cur.parents[2] / "frontend"


FRONTEND_DIR = get_frontend_dir()
logger.info(f"Frontend directory resolved to: {FRONTEND_DIR}")

# Initialize database tables
logger.info("Initializing database tables...")
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Confidential Central Government Ops Dashboard & Smart-Telemetry Platform.",
    version="1.0.0"
)

# Mount static asset folders if they exist
if (FRONTEND_DIR / "css").exists():
    app.mount("/css", StaticFiles(directory=str(FRONTEND_DIR / "css")), name="css")
if (FRONTEND_DIR / "js").exists():
    app.mount("/js", StaticFiles(directory=str(FRONTEND_DIR / "js")), name="js")


# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in settings.CORS_ORIGINS.split(",") if origin.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register REST Routers
app.include_router(auth.router)
app.include_router(vehicles.router)
app.include_router(accidents.router)
app.include_router(emergency_contacts.router)
app.include_router(alerts.router)
app.include_router(stations.router)
app.include_router(reports.router)
app.include_router(operations.router)


@app.websocket("/ws/alerts")
async def websocket_alerts_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for real-time alert broadcasts.
    """
    await manager.connect(websocket)
    try:
        while True:
            # Maintain connection alive, ignore incoming text messages
            data = await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error on connection: {e}")
        manager.disconnect(websocket)


def seed_database():
    """
    Auto-seeds the database with default accounts, stations, vehicles,
    and emergency contacts so the application is instantly functional.
    """
    db = SessionLocal()
    try:
        # 1. Check if seeder already executed
        user_count = db.query(User).count()
        if user_count > 0:
            logger.info("Database already seeded. Skipping seeder.")
            return

        logger.info("Executing automatic database seeder...")

        # 2. Seed Stations (Police & Hospitals)
        logger.info("Seeding emergency response stations...")
        delhi_police = Station(
            name="Delhi Main Police HQ",
            type="police",
            address="Parliament Street, New Delhi, 110001",
            latitude=28.6139,
            longitude=77.2090,
            jurisdiction_area="Delhi NCR",
            phone="011-23319999"
        )
        mumbai_police = Station(
            name="Mumbai Central Police Station",
            type="police",
            address="Dr D N Road, Fort, Mumbai, 400001",
            latitude=18.9750,
            longitude=72.8258,
            jurisdiction_area="Mumbai Ward A",
            phone="022-22620111"
        )
        blr_police = Station(
            name="Bengaluru East Police Division",
            type="police",
            address="Kasturba Road, Bengaluru, 560001",
            latitude=12.9716,
            longitude=77.5946,
            jurisdiction_area="East Bengaluru",
            phone="080-22942222"
        )
        
        aiims_hospital = Station(
            name="AIIMS Trauma Center",
            type="hospital",
            address="Ansari Nagar, Ring Road, New Delhi, 110029",
            latitude=28.5672,
            longitude=77.2100,
            jurisdiction_area="South Delhi",
            phone="011-26588500"
        )
        mumbai_hospital = Station(
            name="KEM General Hospital",
            type="hospital",
            address="Acharya Donde Marg, Parel, Mumbai, 400012",
            latitude=19.0025,
            longitude=72.8420,
            jurisdiction_area="Mumbai Central",
            phone="022-24107000"
        )
        blr_hospital = Station(
            name="St. John's Medical College",
            type="hospital",
            address="Sarjapur Road, John Nagar, Bengaluru, 560034",
            latitude=12.9344,
            longitude=77.6206,
            jurisdiction_area="South East Bengaluru",
            phone="080-22065000"
        )

        existing_station_names = {name for (name,) in db.query(Station.name).all()}
        stations_to_add = [
            station for station in [
                delhi_police,
                mumbai_police,
                blr_police,
                aiims_hospital,
                mumbai_hospital,
                blr_hospital,
            ]
            if station.name not in existing_station_names
        ]
        if stations_to_add:
            db.add_all(stations_to_add)
            db.commit()

        # 3. Seed Government Official Accounts
        logger.info("Seeding default user accounts (admin123, police123, hospital123)...")
        
        super_admin = User(
            name="Chief Officer Administrator",
            email="admin@gov.in",
            password_hash=get_password_hash("admin123"),
            role="superadmin",
            phone="+919999999999"
        )
        
        police_user = User(
            name="Delhi Dispatch Command",
            email="police_delhi@gov.in",
            password_hash=get_password_hash("police123"),
            role="police",
            station_name="Delhi Main Police HQ",
            station_address="Parliament Street, New Delhi, 110001",
            jurisdiction_area="Delhi NCR",
            phone="+919876543210"
        )
        
        hospital_user = User(
            name="AIIMS Trauma Triage",
            email="hospital_delhi@gov.in",
            password_hash=get_password_hash("hospital123"),
            role="hospital",
            station_name="AIIMS Trauma Center",
            station_address="Ansari Nagar, Ring Road, New Delhi, 110029",
            jurisdiction_area="South Delhi",
            phone="+919123456789"
        )

        db.add_all([super_admin, police_user, hospital_user])
        db.commit()

        # 4. Seed Vehicles & Emergency Home Contacts
        logger.info("Seeding registered smart-chip vehicles...")
        
        car_delhi = Vehicle(
            owner_name="Rajesh Kumar",
            owner_phone="+919876543211",
            owner_address="H-15, Rajouri Garden, New Delhi",
            type="car",
            plate_number="DL-1CA-1234",
            status="on_road",
            latitude=28.6448,
            longitude=77.1216
        )
        
        truck_mumbai = Vehicle(
            owner_name="Suresh Patil",
            owner_phone="+919988776655",
            owner_address="Flat 204, Sea Breeze Apts, Bandra, Mumbai",
            type="truck",
            plate_number="MH-01AB-5678",
            status="on_road",
            latitude=19.0596,
            longitude=72.8295
        )
        
        bus_blr = Vehicle(
            owner_name="Ramesh Gowda",
            owner_phone="+919123456780",
            owner_address="No. 42, 10th Main, Jayanagar, Bengaluru",
            type="bus",
            plate_number="KA-03MS-9999",
            status="on_road",
            latitude=12.9307,
            longitude=77.5838
        )

        existing_vehicle_plates = {plate for (plate,) in db.query(Vehicle.plate_number).all()}
        vehicles_to_add = [
            vehicle for vehicle in [car_delhi, truck_mumbai, bus_blr]
            if vehicle.plate_number not in existing_vehicle_plates
        ]
        if vehicles_to_add:
            db.add_all(vehicles_to_add)
            db.commit()

        car_delhi = db.query(Vehicle).filter(Vehicle.plate_number == "DL-1CA-1234").first()
        truck_mumbai = db.query(Vehicle).filter(Vehicle.plate_number == "MH-01AB-5678").first()
        bus_blr = db.query(Vehicle).filter(Vehicle.plate_number == "KA-03MS-9999").first()

        # Seed emergency contacts for these vehicles
        logger.info("Linking home emergency contacts...")
        
        contact_car = EmergencyContact(
            vehicle_id=car_delhi.id,
            name="Priya Kumar (Wife)",
            phone="+919876543212",
            relation="Wife",
            address="H-15, Rajouri Garden, New Delhi"
        )
        
        contact_truck = EmergencyContact(
            vehicle_id=truck_mumbai.id,
            name="Savita Patil (Wife)",
            phone="+919988776654",
            relation="Wife",
            address="Flat 204, Sea Breeze Apts, Bandra, Mumbai"
        )
        
        contact_bus = EmergencyContact(
            vehicle_id=bus_blr.id,
            name="Siddharth Gowda (Son)",
            phone="+919123456781",
            relation="Son",
            address="No. 42, 10th Main, Jayanagar, Bengaluru"
        )

        existing_contact_vehicle_ids = {
            vehicle_id for (vehicle_id,) in db.query(EmergencyContact.vehicle_id).all()
        }
        contacts_to_add = [
            contact for contact in [contact_car, contact_truck, contact_bus]
            if contact.vehicle_id not in existing_contact_vehicle_ids
        ]

        db.add_all(contacts_to_add)
        db.commit()

        logger.info("Automatic database seeding completed successfully!")
    except Exception as e:
        logger.error(f"Error seeding database: {e}")
        db.rollback()
    finally:
        db.close()


@app.on_event("startup")
def startup_event():
    """
    Executes database seeder on application startup.
    """
    seed_database()
    db = SessionLocal()
    try:
        # Clean any orphaned public family access records
        valid_user_ids = {u_id for (u_id,) in db.query(User.id).all()}
        for pfa in db.query(PublicFamilyAccess).all():
            if pfa.user_id not in valid_user_ids:
                db.delete(pfa)
        db.commit()

        # Backfill responder jobs for incidents created before dispatch tracking existed.
        for accident in db.query(Accident).all():
            existing_agencies = {
                agency for (agency,) in db.query(DispatchEvent.agency_type).filter(
                    DispatchEvent.accident_id == accident.id
                ).all()
            }
            if "police" not in existing_agencies:
                police_job_status = "completed" if accident.police_status == "resolved" else "pending"
                db.add(DispatchEvent(accident_id=accident.id, agency_type="police", status=police_job_status))
            if "hospital" not in existing_agencies:
                hospital_job_status = "completed" if accident.hospital_status == "treated" else "pending"
                db.add(DispatchEvent(accident_id=accident.id, agency_type="hospital", status=hospital_job_status))
        db.commit()
    finally:
        db.close()


@app.get("/")
def read_root():
    frontend_file = FRONTEND_DIR / "index.html"
    if frontend_file.exists():
        with frontend_file.open("r", encoding="utf-8") as f:
            return HTMLResponse(
                content=f.read(),
                status_code=200,
                headers={"Cache-Control": "no-store, max-age=0"},
            )
    return {
        "status": "online",
        "system": "National Accident Detection & Alert Infrastructure API Gateway (Dashboard index.html not found)",
        "documentation": "/docs"
    }


@app.get("/favicon.svg", include_in_schema=False)
@app.get("/favicon.ico", include_in_schema=False)
def favicon():
    fav = FRONTEND_DIR / "favicon.svg"
    if not fav.exists() and (FRONTEND_DIR.parent / "favicon.svg").exists():
        fav = FRONTEND_DIR.parent / "favicon.svg"
    if fav.exists():
        return FileResponse(fav, media_type="image/svg+xml")
    return HTMLResponse("", status_code=204)

