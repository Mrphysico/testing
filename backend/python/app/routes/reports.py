from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import csv
import io
import logging

from app.database import get_db
from app.models import Accident, Vehicle, Station
from app.auth import require_responder

# ReportLab imports for PDF generation
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

logger = logging.getLogger("app.reports")

router = APIRouter(prefix="/reports", tags=["reports"])

@router.get("/daily")
def get_daily_reports(db: Session = Depends(get_db), current_user = Depends(require_responder)):
    """
    Generate aggregate statistics for the last 24 hours of operations.
    """
    time_limit = datetime.utcnow() - timedelta(days=1)
    accidents = db.query(Accident).filter(Accident.timestamp >= time_limit).all()
    
    # Calculate stats
    total = len(accidents)
    severity_counts = {"low": 0, "medium": 0, "high": 0, "critical": 0}
    type_counts = {"car": 0, "bus": 0, "truck": 0}
    status_counts = {"pending": 0, "dispatched": 0, "resolved": 0}
    
    for a in accidents:
        # Severity
        sev = a.severity.lower()
        if sev in severity_counts:
            severity_counts[sev] += 1
            
        # Vehicle Type
        vehicle = db.query(Vehicle).filter(Vehicle.id == a.vehicle_id).first()
        if vehicle:
            vtype = vehicle.type.lower()
            if vtype in type_counts:
                type_counts[vtype] += 1
                
        # Responder Status (combined)
        if a.police_status == "resolved" and a.hospital_status == "treated":
            status_counts["resolved"] += 1
        elif a.police_status == "dispatched" or a.hospital_status == "dispatched":
            status_counts["dispatched"] += 1
        else:
            status_counts["pending"] += 1
            
    return {
        "total_accidents": total,
        "by_severity": severity_counts,
        "by_vehicle_type": type_counts,
        "by_status": status_counts,
        "timestamp": datetime.utcnow().isoformat()
    }


@router.get("/monthly")
def get_monthly_reports(db: Session = Depends(get_db), current_user = Depends(require_responder)):
    """
    Generate operational analytics for the last 30 days.
    Also breaks down crash records by time of day and regional hotspot stations.
    """
    time_limit = datetime.utcnow() - timedelta(days=30)
    accidents = db.query(Accident).filter(Accident.timestamp >= time_limit).all()
    
    total = len(accidents)
    severity_counts = {"low": 0, "medium": 0, "high": 0, "critical": 0}
    type_counts = {"car": 0, "bus": 0, "truck": 0}
    status_counts = {"pending": 0, "dispatched": 0, "resolved": 0}
    
    # Time of Day slots
    time_slots = {"morning": 0, "afternoon": 0, "evening": 0, "night": 0}
    
    # Regional tracking (by assigned Police Station names)
    regional_counts = {}
    
    for a in accidents:
        # Severity
        sev = a.severity.lower()
        if sev in severity_counts:
            severity_counts[sev] += 1
            
        # Vehicle Type
        vehicle = db.query(Vehicle).filter(Vehicle.id == a.vehicle_id).first()
        if vehicle:
            vtype = vehicle.type.lower()
            if vtype in type_counts:
                type_counts[vtype] += 1
                
        # Status
        if a.police_status == "resolved" and a.hospital_status == "treated":
            status_counts["resolved"] += 1
        elif a.police_status == "dispatched" or a.hospital_status == "dispatched":
            status_counts["dispatched"] += 1
        else:
            status_counts["pending"] += 1
            
        # Time of Day
        hour = a.timestamp.hour
        if 6 <= hour < 12:
            time_slots["morning"] += 1
        elif 12 <= hour < 17:
            time_slots["afternoon"] += 1
        elif 17 <= hour < 21:
            time_slots["evening"] += 1
        else:
            time_slots["night"] += 1
            
        # Region
        if a.assigned_police_id:
            police_station = db.query(Station).filter(Station.id == a.assigned_police_id).first()
            if police_station:
                name = police_station.name
                regional_counts[name] = regional_counts.get(name, 0) + 1
                
    return {
        "total_accidents": total,
        "by_severity": severity_counts,
        "by_vehicle_type": type_counts,
        "by_status": status_counts,
        "by_time_of_day": time_slots,
        "by_region": regional_counts,
        "timestamp": datetime.utcnow().isoformat()
    }


@router.get("/export")
def export_reports(
    db: Session = Depends(get_db), 
    format: str = Query("csv", description="Format: csv or pdf"),
    current_user = Depends(require_responder)
):
    """
    Export all historical accident reports as CSV spreadsheets or beautiful official PDF reports.
    """
    accidents = db.query(Accident).order_by(Accident.timestamp.desc()).all()
    
    if format.lower() == "pdf":
        return generate_pdf_report(accidents, db)
    else:
        return generate_csv_report(accidents, db)


def generate_csv_report(accidents, db: Session):
    """
    Generate CSV file of accidents history on-the-fly.
    """
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Headers
    writer.writerow([
        "Accident ID", "Vehicle Plate", "Vehicle Type", "Owner Name", "Owner Phone", 
        "Latitude", "Longitude", "Location Address", "Severity", 
        "Impact Force (N)", "Speed (km/h)", "Police Status", "Hospital Status", "Timestamp"
    ])
    
    for a in accidents:
        vehicle = db.query(Vehicle).filter(Vehicle.id == a.vehicle_id).first()
        plate = vehicle.plate_number if vehicle else "N/A"
        vtype = vehicle.type.upper() if vehicle else "N/A"
        owner = vehicle.owner_name if vehicle else "N/A"
        phone = vehicle.owner_phone if vehicle else "N/A"
        
        force = a.sensor_data.get("impact_force", "N/A")
        speed = a.sensor_data.get("speed_at_impact", "N/A")
        
        writer.writerow([
            a.id, plate, vtype, owner, phone, 
            a.latitude, a.longitude, a.location_address, a.severity.upper(), 
            force, speed, a.police_status.upper(), a.hospital_status.upper(), 
            a.timestamp.strftime("%Y-%m-%d %H:%M:%S")
        ])
        
    output.seek(0)
    
    response = StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv"
    )
    response.headers["Content-Disposition"] = "attachment; filename=government_accident_report.csv"
    return response


def generate_pdf_report(accidents, db: Session):
    """
    Compiles a comprehensive PDF detailing critical crash telemetry
    using ReportLab flowables.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, 
        pagesize=letter,
        rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=40
    )
    
    styles = getSampleStyleSheet()
    
    # Custom official styles
    title_style = ParagraphStyle(
        'GovTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=20,
        textColor=colors.HexColor('#1E3A8A'),
        alignment=1, # Center
        spaceAfter=15
    )
    
    subtitle_style = ParagraphStyle(
        'GovSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        textColor=colors.HexColor('#4B5563'),
        alignment=1,
        spaceAfter=25
    )
    
    heading_style = ParagraphStyle(
        'GovHeading',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=12,
        textColor=colors.HexColor('#1E3A8A'),
        spaceBefore=15,
        spaceAfter=10
    )
    
    body_style = ParagraphStyle(
        'GovBody',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8,
        textColor=colors.HexColor('#1F2937')
    )
    
    header_cell_style = ParagraphStyle(
        'GovHeaderCell',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8,
        textColor=colors.white
    )

    elements = []
    
    # Header Banner
    elements.append(Paragraph("GOVERNMENT OF INDIA", title_style))
    elements.append(Paragraph("NATIONAL ROAD ACCIDENT ALERT & LOGISTICS SUMMARY REPORT", title_style))
    elements.append(Paragraph(f"Generated on: {datetime.utcnow().strftime('%Y-%m-%d %I:%M %p UTC')} | Confidential - Internal Official Use Only", subtitle_style))
    elements.append(Spacer(1, 10))
    
    # Brief stats summary
    total_count = len(accidents)
    critical_count = sum(1 for a in accidents if a.severity.lower() == "critical")
    resolved_count = sum(1 for a in accidents if a.police_status == "resolved" and a.hospital_status == "treated")
    
    stats_data = [
        ["Total Logged Accidents:", str(total_count), "Resolved Cases:", str(resolved_count)],
        ["Critical Crashes:", str(critical_count), "Active Dispatches:", str(total_count - resolved_count)]
    ]
    
    stats_table = Table(stats_data, colWidths=[130, 100, 130, 100])
    stats_table.setStyle(TableStyle([
        ('FONTNAME', (0,0), (-1,-1), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,-1), 9),
        ('TEXTCOLOR', (0,0), (0,-1), colors.HexColor('#1E3A8A')),
        ('TEXTCOLOR', (2,0), (2,-1), colors.HexColor('#1E3A8A')),
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#F3F4F6')),
        ('GRID', (0,0), (-1,-1), 1, colors.HexColor('#E5E7EB')),
        ('PADDING', (0,0), (-1,-1), 8),
    ]))
    
    elements.append(stats_table)
    elements.append(Spacer(1, 20))
    
    # Incident List Section
    elements.append(Paragraph("HISTORICAL INCIDENT DATABASE LOGS", heading_style))
    
    # Build Table
    table_data = [[
        Paragraph("ID", header_cell_style), 
        Paragraph("Plate #", header_cell_style), 
        Paragraph("Type", header_cell_style), 
        Paragraph("Severity", header_cell_style), 
        Paragraph("Telemetry (Force/Speed)", header_cell_style), 
        Paragraph("Responder Status", header_cell_style), 
        Paragraph("Timestamp", header_cell_style)
    ]]
    
    for idx, a in enumerate(accidents[:40]):  # Limit to first 40 to avoid massive overflow
        vehicle = db.query(Vehicle).filter(Vehicle.id == a.vehicle_id).first()
        plate = vehicle.plate_number if vehicle else "N/A"
        vtype = vehicle.type.upper() if vehicle else "N/A"
        
        force = a.sensor_data.get("impact_force", "N/A")
        speed = a.sensor_data.get("speed_at_impact", "N/A")
        
        status_text = f"Pol: {a.police_status.upper()}\nHosp: {a.hospital_status.upper()}"
        
        # Color coding severity cell background
        sev_upper = a.severity.upper()
        
        table_data.append([
            Paragraph(str(a.id), body_style),
            Paragraph(plate, body_style),
            Paragraph(vtype, body_style),
            Paragraph(sev_upper, body_style),
            Paragraph(f"{force}N / {speed}kmh", body_style),
            Paragraph(status_text, body_style),
            Paragraph(a.timestamp.strftime("%Y-%m-%d %H:%M"), body_style)
        ])
        
    accident_table = Table(table_data, colWidths=[25, 60, 45, 55, 120, 110, 100])
    
    # Table Styling
    t_style = TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1E3A8A')),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('BOTTOMPADDING', (0,0), (-1,0), 6),
        ('TOPPADDING', (0,0), (-1,0), 6),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#D1D5DB')),
        ('PADDING', (0,0), (-1,-1), 4),
    ])
    
    # Alternating row background
    for i in range(1, len(table_data)):
        if i % 2 == 0:
            t_style.add('BACKGROUND', (0,i), (-1,i), colors.HexColor('#F9FAFB'))
            
    accident_table.setStyle(t_style)
    elements.append(accident_table)
    
    # Notice at bottom if truncated
    if len(accidents) > 40:
        elements.append(Spacer(1, 10))
        elements.append(Paragraph(f"* Report truncated. Showing 40 most recent reports out of {len(accidents)} total incidents in database.", subtitle_style))
        
    # Signature Section
    elements.append(Spacer(1, 40))
    sig_data = [
        ["Report Compiled By:", "Authorized Signatory:"],
        ["\n\n___________________________", "\n\n___________________________"],
        ["Government Operations Center System", "Director General - Road Safety Division"]
    ]
    sig_table = Table(sig_data, colWidths=[260, 260])
    sig_table.setStyle(TableStyle([
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,-1), 8),
        ('TEXTCOLOR', (0,0), (-1,-1), colors.HexColor('#374151')),
    ]))
    elements.append(sig_table)
    
    doc.build(elements)
    
    buffer.seek(0)
    response = StreamingResponse(
        buffer,
        media_type="application/pdf"
    )
    response.headers["Content-Disposition"] = "attachment; filename=government_national_accident_report.pdf"
    return response
