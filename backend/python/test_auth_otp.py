import sys
import uuid
from pathlib import Path

# Add backend/python to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from fastapi.testclient import TestClient
from app.main import app
from app.services.email_service import get_virtual_email_logs
from app.services.notification import get_virtual_sms_logs

client = TestClient(app)

def run_tests():
    print("--- 1. Testing Frontend Static Delivery & Routing ---")
    for path in ["/", "/index.html", "/javascript", "/javascript/index.html"]:
        res = client.get(path)
        assert res.status_code == 200, f"Expected 200 for {path}, got {res.status_code}"
        assert 'id="root"' in res.text, f"Root element missing from {path}"
        assert "/js/app.js" in res.text, f"app.js script tag missing from {path}"
        print(f"[PASS] GET {path} delivers index.html successfully")

    res_css = client.get("/css/style.css")
    assert res_css.status_code == 200, f"Expected 200 for CSS, got {res_css.status_code}"
    assert "marker-dot" in res_css.text, "CSS content missing"
    print("[PASS] GET /css/style.css delivers style.css successfully")

    res_js = client.get("/js/app.js")
    assert res_js.status_code == 200, f"Expected 200 for JS, got {res_js.status_code}"
    assert "handleSendOtp" in res_js.text, "handleSendOtp missing in app.js"
    print("[PASS] GET /js/app.js delivers app.js successfully")

    print("\n--- 2. Testing OTP Generation with Auto-Onboarding of Vehicle & Contact ---")
    # Test with user's specific credentials
    user_email = f"test_{uuid.uuid4().hex[:8]}@example.com"
    plate_raw = "MH 15H W8309"
    phone_raw = "+91 7977308174"
    user_name = "Shubham Kumar"

    res_otp = client.post("/auth/send-signup-otp", json={
        "name": user_name,
        "email": user_email,
        "phone": phone_raw,
        "plate_number": plate_raw
    })
    assert res_otp.status_code == 200, f"Expected 200 for OTP request, got {res_otp.status_code}: {res_otp.text}"
    otp_data = res_otp.json()
    assert "dev_otp" in otp_data and otp_data["dev_otp"], "dev_otp was not returned"
    otp_code = otp_data["dev_otp"]
    print(f"[PASS] Successfully generated 6-digit OTP for {plate_raw}: {otp_code}")

    # Check that OTP email was dispatched (virtual log or SMTP)
    email_logs = get_virtual_email_logs()
    assert any(log["to_email"] == user_email and "Verification OTP" in log["subject"] for log in email_logs), "OTP email not found in email logs"
    print(f"[PASS] Verification OTP email dispatched to {user_email}")

    # Check that OTP SMS was logged
    sms_logs = get_virtual_sms_logs()
    assert any("7977308174" in log["to_phone"] for log in sms_logs), "OTP SMS not found in SMS logs"
    print(f"[PASS] Verification OTP SMS dispatched to {phone_raw}")

    print("\n--- 3. Testing OTP Verification & Account Creation ---")
    # Test wrong OTP code rejected
    res_wrong_otp = client.post("/auth/verify-signup-otp", json={
        "name": user_name,
        "email": user_email,
        "password": "securepassword123",
        "phone": phone_raw,
        "plate_number": plate_raw,
        "otp_code": "000000"
    })
    assert res_wrong_otp.status_code == 400, f"Expected 400 for wrong OTP, got {res_wrong_otp.status_code}"
    print("[PASS] Rejected invalid OTP code with 400")

    # Test correct OTP code creates user account
    res_verify = client.post("/auth/verify-signup-otp", json={
        "name": user_name,
        "email": user_email,
        "password": "securepassword123",
        "phone": phone_raw,
        "plate_number": plate_raw,
        "otp_code": otp_code
    })
    assert res_verify.status_code == 201, f"Expected 201 for valid OTP verify, got {res_verify.status_code}: {res_verify.text}"
    auth_data = res_verify.json()
    assert "access_token" in auth_data, "access_token missing in response"
    assert auth_data["user"]["email"] == user_email, "User email mismatch"
    assert auth_data["user"]["role"] == "public", "User role must be public"
    print(f"[PASS] Family account created successfully for {user_email} and access token returned")

    # Check that Welcome / Signup Successful confirmation email was dispatched
    email_logs_after = get_virtual_email_logs()
    assert any(log["to_email"] == user_email and "Signup Successful" in log["subject"] for log in email_logs_after), "Confirmation email not found in email logs"
    print(f"[PASS] 'Signup Successful' confirmation email dispatched to {user_email}")

    # Test duplicate signup with same email is rejected
    res_dup = client.post("/auth/send-signup-otp", json={
        "name": user_name,
        "email": user_email,
        "phone": phone_raw,
        "plate_number": plate_raw
    })
    assert res_dup.status_code == 400, f"Expected 400 for duplicate email, got {res_dup.status_code}"
    print("[PASS] Duplicate email registration correctly rejected with 400")

    # Test brand new unseen plate is automatically onboarded without errors
    new_user_email = f"new_{uuid.uuid4().hex[:8]}@example.com"
    brand_new_plate = f"KA-{uuid.uuid4().hex[:2].upper()}-9999"
    res_new_plate = client.post("/auth/send-signup-otp", json={
        "name": "Arjun Sharma",
        "email": new_user_email,
        "phone": "9811223344",
        "plate_number": brand_new_plate
    })
    assert res_new_plate.status_code == 200, f"Expected 200 for new plate auto-onboarding, got {res_new_plate.status_code}: {res_new_plate.text}"
    new_otp = res_new_plate.json()["dev_otp"]
    res_new_verify = client.post("/auth/verify-signup-otp", json={
        "name": "Arjun Sharma",
        "email": new_user_email,
        "password": "password456",
        "phone": "9811223344",
        "plate_number": brand_new_plate,
        "otp_code": new_otp
    })
    assert res_new_verify.status_code == 201, f"Expected 201 for auto-onboarded vehicle verify: {res_new_verify.text}"
    print(f"[PASS] Brand new vehicle {brand_new_plate} auto-onboarded and registered seamlessly")

    # Test Login with newly created user
    res_login = client.post("/auth/login", json={
        "email": user_email,
        "password": "securepassword123"
    })
    assert res_login.status_code == 200, f"Expected 200 for login, got {res_login.status_code}: {res_login.text}"
    print(f"[PASS] Login with newly created account {user_email} succeeded")

    print("\n==================================================")
    print("ALL TESTS PASSED SUCCESSFULLY!")
    print("==================================================")

if __name__ == "__main__":
    run_tests()
