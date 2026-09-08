# Government Accident Detection & Alert System

Central Emergency Operations Portal and Smart Telemetry Platform organized with dedicated language directories, secure OTP signup verification, and automated confirmation emails.

---

## 📁 Clean Directory Architecture

The repository is organized by language and responsibility:

| Folder | Tech / Language | What it contains |
| --- | --- | --- |
| **`frontend/javascript/`** | **HTML / CSS / JavaScript (React)** | Modular web dashboard: <br>&bull; `index.html`: Clean HTML skeleton<br>&bull; `css/style.css`: Extracted animations & leaflet styles<br>&bull; `js/app.js`: React UI with 2-step OTP registration & incident maps |
| **`backend/python/`** | **Python (FastAPI & SQLAlchemy)** | API Server, OTP Verification & Notification Services:<br>&bull; `app/routes/`: Authentication, Vehicles, Accidents, Reports<br>&bull; `app/services/`: SMTP email, OTP generation, Twilio SMS<br>&bull; `run.py`: Server launcher<br>&bull; `requirements.txt`: Python package dependencies<br>&bull; `simulator/`: Telemetry hardware test simulator |
| **`mobile/`** | **React Native (Expo)** | Mobile responder application for emergency personnel |

---

## 🚀 How to Run the Project

### 1. Start Backend & Web Dashboard

Run these commands from the project root:

```powershell
# Install dependencies
python -m pip install -r backend/python/requirements.txt

# Start the server (either command works)
python backend/python/run.py
# or
python backend/run.py
```

Open **<http://127.0.0.1:8000>** in your browser.
API documentation is available at **<http://127.0.0.1:8000/docs>**.

---

## 🔐 New Feature: Two-Step OTP Verification for Signup

Public family accounts can register to monitor their family vehicle's accident status:

1. Click the **Sign Up (OTP)** tab on the website.
2. Enter your **Name**, **Email Address**, **Password**, **Registered Phone**, and **Vehicle Plate**.
3. Click **Send Verification OTP**:
   - The system checks if your phone number matches the vehicle's registered emergency contact.
   - A secure 6-digit one-time password (OTP) is sent to your **Email** and **Phone**.
4. Enter the **6-digit OTP code** and click **Verify & Complete Signup**.
5. Once verified:
   - Your family account is created.
   - You are automatically signed into the Family Status Portal.
   - An **Official Welcome Confirmation Email** is dispatched to your registered email address.

### 🧪 Ready-to-use Demo Vehicle for Testing Signup:

- **Vehicle Plate Number**: `DL-1CA-1234`
- **Registered Emergency Phone**: `+919876543212`
- **Name**: Any name (e.g. `Priya Kumar`)
- **Email**: Your email address
- **Password**: Any password with at least 6 characters (e.g. `family123`)

*(Note: In development mode, the test OTP is also displayed in the server terminal and as a convenient hint banner on screen for instant testing).*

---

## 📧 How to Setup Real Email (Gmail / SMTP)

By default, when SMTP is not configured, the system uses **Virtual Email Logging** (it prints the complete email in the server terminal so nothing breaks).

To send **REAL emails** to Gmail, Outlook, or Yahoo inboxes:

1. Open `backend/python/.env` (or create it from `backend/python/.env.example`).
2. Add your SMTP credentials:

```ini
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your_email@gmail.com
SMTP_PASSWORD=your_16_character_app_password
SMTP_FROM_EMAIL=your_email@gmail.com
SMTP_FROM_NAME=Government Emergency Portal
SMTP_TLS=True
```

> **How to get a Gmail App Password:**
> 1. Go to your **Google Account** &rarr; **Security**.
> 2. Enable **2-Step Verification**.
> 3. Search for **App passwords** &rarr; Create one named "Emergency Portal".
> 4. Copy the 16-character code into `SMTP_PASSWORD` above.

---

## 🛡️ Default Staff Demo Accounts

For police dispatchers, hospitals, and central administrators:

| Role | Email / Login ID | Password | Access Level |
| --- | --- | --- | --- |
| **Super Admin** | `admin@gov.in` | `admin123` | Full dashboard, admin panel, virtual SMS logs, fleet management |
| **Police HQ** | `police_delhi@gov.in` | `police123` | Police response dispatching, station oversight |
| **Hospital Trauma** | `hospital_delhi@gov.in` | `hospital123` | Medical triage, patient treatment status |

---

## 📡 Accident Simulator (Optional)

In a separate terminal, trigger simulated crash telemetry:

```powershell
python backend/python/simulator/simulator.py --single
```
