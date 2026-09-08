import requests
import random
import time
import sys

API_URL = "http://127.0.0.1:8000"
DEFAULT_ADMIN_EMAIL = "admin@gov.in"
DEFAULT_ADMIN_PASSWORD = "admin123"

def get_auth_headers():
    """
    Logs in with the seeded admin account and returns an Authorization header.
    The backend seeds this account automatically on first startup.
    """
    try:
        login_res = requests.post(f"{API_URL}/auth/login", json={
            "email": DEFAULT_ADMIN_EMAIL,
            "password": DEFAULT_ADMIN_PASSWORD
        }, timeout=3.0)
        if login_res.status_code == 200:
            token = login_res.json()["access_token"]
            return {"Authorization": f"Bearer {token}"}
        print(f"[-] Admin login failed with code {login_res.status_code}: {login_res.text}")
    except Exception as e:
        print(f"[-] Could not authenticate with API server: {e}")
    return None

def get_registered_vehicles():
    """
    Fetch all active vehicles from the FastAPI database.
    """
    headers = get_auth_headers()
    if not headers:
        return []

    try:
        res = requests.get(f"{API_URL}/vehicles/live", headers=headers, timeout=3.0)
        if res.status_code == 200:
            return res.json()
        print(f"[-] Vehicle lookup failed with code {res.status_code}: {res.text}")
    except Exception as e:
        print(f"[-] Could not connect to API server: {e}")
    return []

def register_mock_vehicle():
    """
    Bootstraps a simulated vehicle if none are registered.
    """
    # Create random plate number
    plate = f"DL-3CA-{random.randint(1000, 9999)}"
    payload = {
        "owner_name": "Simulated Driver",
        "owner_phone": "+919999988888",
        "owner_address": "Simulator Lane, New Delhi, India",
        "type": random.choice(["car", "bus", "truck"]),
        "plate_number": plate,
        "status": "on_road",
        "latitude": 28.6139,
        "longitude": 77.2090
    }
    
    try:
        headers = get_auth_headers()
        if not headers:
            return []

        res = requests.post(f"{API_URL}/vehicles", json=payload, headers=headers, timeout=3.0)
        if res.status_code == 201:
            v = res.json()
            print(f"[+] Successfully registered mock vehicle: {v['plate_number']} (ID: {v['id']})")
            return [v]
        print(f"[-] Mock vehicle registration failed with code {res.status_code}: {res.text}")
    except Exception as e:
        print(f"[-] Failed to register default simulated vehicle: {e}")
    return []

def trigger_accident(vehicle_id):
    """
    Generates random Indian coordinates and smart-chip crash telemetry,
    then triggers the API endpoint.
    """
    # India GPS limits: Latitude: 8.0 to 37.0, Longitude: 68.0 to 97.0
    lat = round(random.uniform(8.0, 37.0), 6)
    lon = round(random.uniform(68.0, 97.0), 6)
    
    # Coordinates overrides to Delhi NCR or Mumbai to ensure they land near our seeded stations occasionally!
    if random.choice([True, False]):
        # Delhi region
        lat = round(random.uniform(28.40, 28.75), 6)
        lon = round(random.uniform(77.00, 77.30), 6)
    
    severity = random.choice(["low", "medium", "high", "critical"])
    
    sensor_data = {
        "impact_force": round(random.uniform(50.0, 500.0), 2),
        "gyroscope_x": round(random.uniform(-180.0, 180.0), 2),
        "gyroscope_y": round(random.uniform(-180.0, 180.0), 2),
        "speed_at_impact": round(random.uniform(40.0, 180.0), 2)
    }
    
    payload = {
        "vehicle_id": vehicle_id,
        "latitude": lat,
        "longitude": lon,
        "severity": severity,
        "sensor_data": sensor_data
    }
    
    print(f"\n[!] Simulating smart-chip collision trigger...")
    print(f"    - Vehicle ID: {vehicle_id}")
    print(f"    - GPS Coordinates: {lat}, {lon}")
    print(f"    - Severity: {severity.upper()}")
    print(f"    - Telemetry speed: {sensor_data['speed_at_impact']} km/h | force: {sensor_data['impact_force']} N")
    
    try:
        url = f"{API_URL}/accidents/trigger"
        res = requests.post(url, json=payload, timeout=5.0)
        if res.status_code == 201:
            data = res.json()
            print(f"[+] Accident logged. ID: {data['id']}")
            print(f"[+] Resolved Address: {data['location_address']}")
            print(f"[+] Assigned Police Station ID: {data['assigned_police_id']}")
            print(f"[+] Assigned Hospital ID: {data['assigned_hospital_id']}")
            return True
        else:
            print(f"[-] Trigger failed with code {res.status_code}: {res.text}")
    except Exception as e:
        print(f"[-] Connection failed during trigger dispatch: {e}")
    return False

if __name__ == "__main__":
    print("=" * 60)
    print("      GOVERNMENT SMART-CHIP TELEMETRY ACCIDENT SIMULATOR      ")
    print("=" * 60)
    
    vehicles = get_registered_vehicles()
    if not vehicles:
        print("[-] No registered vehicles found in the database. Bootstrapping dynamic vehicle...")
        vehicles = register_mock_vehicle()
        
    if not vehicles:
        print("[-] Error: Unable to query or register a vehicle. Is the FastAPI server running?")
        sys.exit(1)
        
    # Check flags
    loop_mode = True
    if len(sys.argv) > 1 and sys.argv[1] == "--single":
        loop_mode = False
        
    if not loop_mode:
        vehicle = random.choice(vehicles)
        trigger_accident(vehicle["id"])
    else:
        print("[+] Starting automatic simulation. Triggering random crash telemetry every 30 seconds...")
        print("[+] Press Ctrl+C to terminate.")
        try:
            while True:
                # Reload vehicles list to reflect newly registered ones
                current_vehicles = get_registered_vehicles() or vehicles
                vehicle = random.choice(current_vehicles)
                trigger_accident(vehicle["id"])
                print("[~] Waiting 30 seconds for next cycle...")
                time.sleep(30)
        except KeyboardInterrupt:
            print("\n[-] Simulator terminated.")
