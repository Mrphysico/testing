import datetime
from typing import Optional

from app.database import Base, SessionLocal, engine
from app.models import Accident, Alert, EmergencyContact, Station, Vehicle
from app.routes.stations import haversine_distance


Base.metadata.create_all(bind=engine)


INDIA_STATIONS = [
    ("Delhi Police Control Room", "police", "Police Headquarters, Jai Singh Road, New Delhi", 28.6271, 77.2090, "Delhi NCR", "112"),
    ("AIIMS Trauma Centre Delhi", "hospital", "Ansari Nagar, New Delhi", 28.5672, 77.2100, "Delhi NCR", "011-26588500"),
    ("Mumbai Police Commissioner Office", "police", "Crawford Market, Mumbai", 18.9470, 72.8338, "Mumbai", "112"),
    ("KEM Hospital Mumbai", "hospital", "Acharya Donde Marg, Parel, Mumbai", 19.0025, 72.8420, "Mumbai", "022-24107000"),
    ("Bengaluru City Police Control", "police", "Infantry Road, Bengaluru", 12.9816, 77.5956, "Bengaluru", "112"),
    ("Victoria Hospital Bengaluru", "hospital", "Fort Road, Bengaluru", 12.9635, 77.5732, "Bengaluru", "080-26701150"),
    ("Chennai Police Control Room", "police", "EVK Sampath Road, Chennai", 13.0827, 80.2707, "Chennai", "112"),
    ("Rajiv Gandhi Government General Hospital Chennai", "hospital", "Park Town, Chennai", 13.0829, 80.2760, "Chennai", "044-25305000"),
    ("Kolkata Police Headquarters Lalbazar", "police", "Lalbazar Street, Kolkata", 22.5726, 88.3639, "Kolkata", "112"),
    ("SSKM Hospital Kolkata", "hospital", "AJC Bose Road, Kolkata", 22.5390, 88.3427, "Kolkata", "033-22041100"),
    ("Hyderabad Police Commissionerate", "police", "Basheerbagh, Hyderabad", 17.3850, 78.4867, "Hyderabad", "112"),
    ("Osmania General Hospital Hyderabad", "hospital", "Afzal Gunj, Hyderabad", 17.3713, 78.4744, "Hyderabad", "040-24600146"),
    ("Ahmedabad Police Commissioner Office", "police", "Shahibaug, Ahmedabad", 23.0225, 72.5714, "Ahmedabad", "112"),
    ("Civil Hospital Ahmedabad", "hospital", "Asarwa, Ahmedabad", 23.0523, 72.6031, "Ahmedabad", "079-22683721"),
    ("Jaipur Police Control Room", "police", "MI Road, Jaipur", 26.9124, 75.7873, "Jaipur", "112"),
    ("SMS Hospital Jaipur", "hospital", "JLN Marg, Jaipur", 26.9025, 75.8186, "Jaipur", "0141-2518222"),
    ("Lucknow Police Commissionerate", "police", "Hazratganj, Lucknow", 26.8467, 80.9462, "Lucknow", "112"),
    ("King George Medical University Lucknow", "hospital", "Chowk, Lucknow", 26.8683, 80.9160, "Lucknow", "0522-2257540"),
    ("Patna Police Control Room", "police", "Gandhi Maidan, Patna", 25.5941, 85.1376, "Patna", "112"),
    ("AIIMS Patna", "hospital", "Phulwari Sharif, Patna", 25.5629, 85.0429, "Patna", "0612-2451070"),
    ("Bhopal Police Control Room", "police", "Jahangirabad, Bhopal", 23.2599, 77.4126, "Bhopal", "112"),
    ("AIIMS Bhopal", "hospital", "Saket Nagar, Bhopal", 23.2068, 77.4597, "Bhopal", "0755-2672334"),
    ("Raipur Police Control Room", "police", "Civil Lines, Raipur", 21.2514, 81.6296, "Raipur", "112"),
    ("AIIMS Raipur", "hospital", "Tatibandh, Raipur", 21.2588, 81.5797, "Raipur", "0771-2573777"),
    ("Ranchi Police Control Room", "police", "Kutchery Road, Ranchi", 23.3441, 85.3096, "Ranchi", "112"),
    ("RIMS Ranchi", "hospital", "Bariatu, Ranchi", 23.3903, 85.3482, "Ranchi", "0651-2541533"),
    ("Bhubaneswar Police Commissionerate", "police", "Vani Vihar, Bhubaneswar", 20.2961, 85.8245, "Bhubaneswar", "112"),
    ("AIIMS Bhubaneswar", "hospital", "Sijua, Bhubaneswar", 20.2310, 85.7750, "Bhubaneswar", "0674-2476789"),
    ("Guwahati Police Commissionerate", "police", "Pan Bazaar, Guwahati", 26.1445, 91.7362, "Guwahati", "112"),
    ("Gauhati Medical College Hospital", "hospital", "Bhangagarh, Guwahati", 26.1570, 91.7720, "Guwahati", "0361-2529457"),
    ("Shillong Police Control Room", "police", "Police Bazaar, Shillong", 25.5788, 91.8933, "Shillong", "112"),
    ("NEIGRIHMS Shillong", "hospital", "Mawdiangdiang, Shillong", 25.6067, 91.9407, "Shillong", "0364-2538013"),
    ("Agartala Police Control Room", "police", "West Tripura, Agartala", 23.8315, 91.2868, "Agartala", "112"),
    ("GBP Hospital Agartala", "hospital", "Kunjaban, Agartala", 23.8467, 91.2840, "Agartala", "0381-2325901"),
    ("Aizawl Police Control Room", "police", "Zarkawt, Aizawl", 23.7271, 92.7176, "Aizawl", "112"),
    ("Civil Hospital Aizawl", "hospital", "Dawrpui, Aizawl", 23.7307, 92.7173, "Aizawl", "0389-2322318"),
    ("Imphal Police Control Room", "police", "Kangla, Imphal", 24.8170, 93.9368, "Imphal", "112"),
    ("RIMS Imphal", "hospital", "Lamphelpat, Imphal", 24.8185, 93.9229, "Imphal", "0385-2414629"),
    ("Kohima Police Control Room", "police", "Kohima, Nagaland", 25.6751, 94.1086, "Kohima", "112"),
    ("Naga Hospital Authority Kohima", "hospital", "Kohima, Nagaland", 25.6688, 94.1090, "Kohima", "0370-2242916"),
    ("Itanagar Police Control Room", "police", "Itanagar, Arunachal Pradesh", 27.0844, 93.6053, "Itanagar", "112"),
    ("TRIHMS Itanagar", "hospital", "Naharlagun, Itanagar", 27.1030, 93.6950, "Itanagar", "0360-2350404"),
    ("Gangtok Police Control Room", "police", "Gangtok, Sikkim", 27.3389, 88.6065, "Gangtok", "112"),
    ("STNM Hospital Gangtok", "hospital", "Sochakgang, Gangtok", 27.3320, 88.6130, "Gangtok", "03592-202944"),
    ("Thiruvananthapuram Police Control Room", "police", "PMG Junction, Thiruvananthapuram", 8.5241, 76.9366, "Thiruvananthapuram", "112"),
    ("Government Medical College Thiruvananthapuram", "hospital", "Ulloor, Thiruvananthapuram", 8.5234, 76.9286, "Thiruvananthapuram", "0471-2528300"),
    ("Panaji Police Control Room", "police", "Panaji, Goa", 15.4909, 73.8278, "Goa", "112"),
    ("Goa Medical College Bambolim", "hospital", "Bambolim, Goa", 15.4630, 73.8580, "Goa", "0832-2458727"),
    ("Chandigarh Police Control Room", "police", "Sector 9, Chandigarh", 30.7333, 76.7794, "Chandigarh", "112"),
    ("PGIMER Chandigarh", "hospital", "Sector 12, Chandigarh", 30.7640, 76.7754, "Chandigarh", "0172-2756565"),
    ("Srinagar Police Control Room", "police", "Lal Chowk, Srinagar", 34.0837, 74.7973, "Srinagar", "112"),
    ("SMHS Hospital Srinagar", "hospital", "Karan Nagar, Srinagar", 34.0780, 74.8010, "Srinagar", "0194-2504801"),
    ("Leh Police Control Room", "police", "Leh, Ladakh", 34.1526, 77.5771, "Leh", "112"),
    ("SNM Hospital Leh", "hospital", "Leh, Ladakh", 34.1642, 77.5848, "Leh", "01982-252014"),
    ("Port Blair Police Control Room", "police", "Aberdeen Bazaar, Port Blair", 11.6234, 92.7265, "Port Blair", "112"),
    ("GB Pant Hospital Port Blair", "hospital", "Atlanta Point, Port Blair", 11.6683, 92.7350, "Port Blair", "03192-230628"),
    ("Puducherry Police Control Room", "police", "White Town, Puducherry", 11.9416, 79.8083, "Puducherry", "112"),
    ("JIPMER Puducherry", "hospital", "Dhanvantari Nagar, Puducherry", 11.9548, 79.7996, "Puducherry", "0413-2296000"),
]


RECENT_INDIA_ACCIDENTS = [
    ("DL-REAL-2401", "car", "NH-48 near Gurugram, Haryana", 28.4595, 77.0266, "critical", 440, 118),
    ("MH-REAL-2402", "truck", "Mumbai-Pune Expressway near Lonavala, Maharashtra", 18.7546, 73.4062, "high", 390, 96),
    ("KA-REAL-2403", "bus", "Outer Ring Road near Marathahalli, Bengaluru", 12.9569, 77.7011, "medium", 210, 62),
    ("TN-REAL-2404", "car", "GST Road near Tambaram, Chennai", 12.9249, 80.1000, "high", 330, 88),
    ("WB-REAL-2405", "truck", "NH-16 near Kolaghat, West Bengal", 22.4300, 87.8730, "critical", 465, 121),
    ("TS-REAL-2406", "car", "ORR near Gachibowli, Hyderabad", 17.4401, 78.3489, "medium", 190, 74),
    ("GJ-REAL-2407", "truck", "SG Highway near Ahmedabad, Gujarat", 23.0730, 72.5150, "high", 370, 101),
    ("RJ-REAL-2408", "bus", "Jaipur-Ajmer Highway near Kishangarh, Rajasthan", 26.5900, 74.8720, "critical", 480, 109),
    ("UP-REAL-2409", "car", "Agra-Lucknow Expressway near Kannauj, Uttar Pradesh", 27.0550, 79.9180, "high", 350, 105),
    ("BR-REAL-2410", "truck", "NH-31 near Patna bypass, Bihar", 25.6070, 85.2230, "medium", 230, 68),
    ("MP-REAL-2411", "bus", "Bhopal-Indore Highway near Sehore, Madhya Pradesh", 23.2000, 77.0850, "high", 360, 93),
    ("CG-REAL-2412", "car", "Raipur-Bhilai Road near Kumhari, Chhattisgarh", 21.2660, 81.5190, "medium", 205, 70),
    ("JH-REAL-2413", "truck", "Ranchi-Jamshedpur Highway near Bundu, Jharkhand", 23.1800, 85.5900, "high", 410, 89),
    ("OD-REAL-2414", "car", "NH-16 near Cuttack, Odisha", 20.4625, 85.8828, "medium", 220, 77),
    ("AS-REAL-2415", "bus", "NH-27 near Guwahati, Assam", 26.1450, 91.7200, "critical", 455, 111),
    ("KL-REAL-2416", "car", "NH-66 near Kollam, Kerala", 8.8932, 76.6141, "high", 320, 84),
    ("GA-REAL-2417", "truck", "NH-66 near Panaji, Goa", 15.4989, 73.8278, "medium", 245, 72),
    ("CH-REAL-2418", "car", "Madhya Marg, Chandigarh", 30.7510, 76.7860, "low", 95, 42),
    ("JK-REAL-2419", "bus", "Srinagar-Jammu Highway near Banihal, Jammu and Kashmir", 33.4360, 75.1960, "critical", 490, 102),
    ("PY-REAL-2420", "car", "East Coast Road near Puducherry", 11.9139, 79.8145, "medium", 185, 66),
]


def nearest_station(db, lat: float, lon: float, station_type: str) -> Optional[Station]:
    stations = db.query(Station).filter(Station.type == station_type).all()
    if not stations:
        return None
    return min(stations, key=lambda station: haversine_distance(lat, lon, station.latitude, station.longitude))


def seed_stations(db) -> int:
    added = 0
    for name, station_type, address, lat, lon, area, phone in INDIA_STATIONS:
        exists = db.query(Station).filter(Station.name == name).first()
        if exists:
            continue
        db.add(Station(
            name=name,
            type=station_type,
            address=address,
            latitude=lat,
            longitude=lon,
            jurisdiction_area=area,
            phone=phone,
        ))
        added += 1
    db.commit()
    return added


def seed_recent_accidents(db) -> int:
    added = 0
    base_time = datetime.datetime.utcnow()
    for index, (plate, vehicle_type, address, lat, lon, severity, impact, speed) in enumerate(RECENT_INDIA_ACCIDENTS, start=1):
        vehicle = db.query(Vehicle).filter(Vehicle.plate_number == plate).first()
        if not vehicle:
            vehicle = Vehicle(
                owner_name=f"Protected Owner {index:02d}",
                owner_phone="+910000000000",
                owner_address="Personal details hidden for privacy. Government records only.",
                type=vehicle_type,
                plate_number=plate,
                status="accident",
                latitude=lat,
                longitude=lon,
            )
            db.add(vehicle)
            db.commit()
            db.refresh(vehicle)

            db.add(EmergencyContact(
                vehicle_id=vehicle.id,
                name=f"Registered Home Contact {index:02d}",
                phone="+910000000000",
                relation="Home Contact",
                address="Protected contact address",
            ))
            db.commit()

        existing = db.query(Accident).filter(
            Accident.vehicle_id == vehicle.id,
            Accident.location_address == address,
        ).first()
        if existing:
            continue

        police = nearest_station(db, lat, lon, "police")
        hospital = nearest_station(db, lat, lon, "hospital")
        vehicle.status = "accident"
        vehicle.latitude = lat
        vehicle.longitude = lon

        accident = Accident(
            vehicle_id=vehicle.id,
            latitude=lat,
            longitude=lon,
            location_address=address,
            severity=severity,
            sensor_data={
                "impact_force": impact,
                "gyroscope_x": round(-80 + index * 6.1, 2),
                "gyroscope_y": round(65 - index * 4.3, 2),
                "speed_at_impact": speed,
                "source": "India-wide public-style demo data",
            },
            police_status="pending" if severity in {"critical", "high"} else "dispatched",
            hospital_status="pending" if severity == "critical" else "dispatched",
            assigned_police_id=police.id if police else None,
            assigned_hospital_id=hospital.id if hospital else None,
            timestamp=base_time - datetime.timedelta(hours=index),
        )
        db.add(accident)
        db.commit()
        db.refresh(accident)

        recipients = [("Registered Home Contact", "+910000000000")]
        if police:
            recipients.append((police.name, police.phone))
        if hospital:
            recipients.append((hospital.name, hospital.phone))

        for recipient_name, recipient_phone in recipients:
            db.add(Alert(
                accident_id=accident.id,
                recipient_name=recipient_name,
                recipient_phone=recipient_phone,
                type="sms",
                message_text=(
                    f"ALERT: Vehicle {plate} reported a {severity.upper()} accident at "
                    f"{address}. Emergency services have been notified. Helpline: 112"
                ),
                status="sent",
            ))
        db.commit()
        added += 1
    return added


def main():
    db = SessionLocal()
    try:
        stations_added = seed_stations(db)
        accidents_added = seed_recent_accidents(db)
        print(f"India-wide stations/hospitals added: {stations_added}")
        print(f"Recent accident records added: {accidents_added}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
