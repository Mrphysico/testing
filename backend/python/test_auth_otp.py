import sys
from pathlib import Path

# Add backend/python to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from fastapi.testclient import TestClient
from app.main import app
from app.services.email_service import get_virtual_email_logs
from app.services.notification import get_virtual_sms_logs

client = TestClient(app)

def run_tests():
    print("--- 1. Testing Frontend Static Delivery ---")
    res = client.get("/")
    assert res.status_code == 200, f"Expected 200, got {res.status_code}"
    assert 'id="root"' in res.text, "Root element missing from HTML"
    assert "/js/app.js" in res.text, "app.js script tag missing"
    print("[PASS] Root GET / delivers frontend/javascript/index.html")

    res_css = client.get("/css/style.css")
    assert res_css.status_code == 200, f"Expected 200 for CSS, got {res_css.status_code}"
    assert "marker-dot" in res_css.text, "CSS content missing"
    print("[PASS] GET /css/style.css delivers style.css successfully")

    res_js = client.get("/js/app.js")
    assert res_js.status_code == 200, f"Expected 200 for JS, got {res_js.status_code}"
    assert "handleSendOtp" in res_js.text, "handleSendOtp missing in app.js"
    print("[PASS] GET /js/app.js delivers app.js successfully")

    print("\n--- 2. Testing OTP Generation & Validation ---")
    # Test invalid plate
    res_bad_plate = client.post("/auth/send-signup-otp", json={
        "name": "Priya Kumar",
        "email": "priya.test@example.com",
        "phone": "+919876543212",
        "plate_number": "INVALID-PLATE-99"
    })
    assert res_bad_plate.status_code == 404, f"Expected 404 for invalid plate, got {res_bad_plate.status_code}"
    print("[PASS] Rejected invalid vehicle plate number with 404")

    # Test mismatched emergency contact phone
    res_bad_phone = client.post("/auth/send-signup-otp", json={
        "name": "Priya Kumar",
        "email": "priya.test@example.com",
        "phone": "+910000000000",
        "plate_number": "DL-1CA-1234"
    })
    assert res_bad_phone.status_code == 403, f"Expected 403 for wrong contact, got {res_bad_phone.status_code}"
    print("[PASS] Rejected mismatched emergency phone with 403")

    # Test valid OTP request
    res_otp = client.post("/auth/send-signup-otp", json={
        "name": "Priya Kumar",
        "email": "priya.test@example.com",
        "phone": "+919876543212",
        "plate_number": "DL-1CA-1234"
    })
    assert res_otp.status_code == 200, f"Expected 200 for OTP request, got {res_otp.status_code}: {res_otp.text}"
    otp_data = res_otp.json()
    assert "dev_otp" in otp_data and otp_data["dev_otp"], "dev_otp was not returned"
    otp_code = otp_data["dev_otp"]
    print(f"[PASS] Generated 6-digit OTP successfully: {otp_code}")

    # Check that OTP email was dispatched (virtual log or SMTP)
    email_logs = get_virtual_email_logs()
    assert any(log["to_email"] == "priya.test@example.com" and "Verification OTP" in log["subject"] for log in email_logs), "OTP email not found in email logs"
    print("[PASS] Verification OTP email dispatched to priya.test@example.com")

    # Check that OTP SMS was logged
    sms_logs = get_virtual_sms_logs()
    assert any(log["to_phone"] == "+919876543212" for log in sms_logs), "OTP SMS not found in SMS logs"
    print("[PASS] Verification OTP SMS dispatched to +919876543212")

    print("\n--- 3. Testing OTP Verification & Account Creation ---")
    # Test wrong OTP code
    res_wrong_otp = client.post("/auth/verify-signup-otp", json={
        "name": "Priya Kumar",
        "email": "priya.test@example.com",
        "password": "securepassword123",
        "phone": "+919876543212",
        "plate_number": "DL-1CA-1234",
        "otp_code": "000000"
    })
    assert res_wrong_otp.status_code == 400, f"Expected 400 for wrong OTP, got {res_wrong_otp.status_code}"
    print("[PASS] Rejected invalid OTP code with 400")

    # Test correct OTP code
    res_verify = client.post("/auth/verify-signup-otp", json={
        "name": "Priya Kumar",
        "email": "priya.test@example.com",
        "password": "securepassword123",
        "phone": "+919876543212",
        "plate_number": "DL-1CA-1234",
        "otp_code": otp_code
    })
    assert res_verify.status_code == 201, f"Expected 201 for valid OTP verify, got {res_verify.status_code}: {res_verify.text}"
    auth_data = res_verify.json()
    assert "access_token" in auth_data, "access_token missing in response"
    assert auth_data["user"]["email"] == "priya.test@example.com", "User email mismatch"
    assert auth_data["user"]["role"] == "public", "User role must be public"
    print("[PASS] Family account created successfully and access token returned")

    # Check that Welcome / Signup Successful confirmation email was sent
    email_logs_after = get_virtual_email_logs()
    assert any(log["to_email"] == "priya.test@example.com" and "Signup Successful" in log["subject"] for log in email_logs_after), "Confirmation email not found in email logs"
    print("[PASS] 'Signup Successful' confirmation email dispatched to priya.test@example.com")

    # Test duplicate signup rejected
    res_dup = client.post("/auth/send-signup-otp", json={
        "name": "Priya Kumar",
        "email": "priya.test@example.com",
        "phone": "+919876543212",
        "plate_number": "DL-1CA-1234"
    })
    assert res_dup.status_code == 400, f"Expected 400 for duplicate email, got {res_dup.status_code}"
    print("[PASS] Duplicate email registration rejected with 400")

    print("\n==================================================")
    print("ALL TESTS PASSED SUCCESSFULLY!")
    print("==================================================")

if __name__ == "__main__":
    run_tests()
