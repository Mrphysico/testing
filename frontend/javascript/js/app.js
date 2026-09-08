const { useEffect, useMemo, useRef, useState } = React;
const API = window.location.origin;

// Default entity templates
const emptyStation = { name: "", type: "police", address: "", latitude: 28.6139, longitude: 77.2090, jurisdiction_area: "", phone: "" };
const emptyVehicle = { owner_name: "", owner_phone: "", owner_address: "", type: "car", plate_number: "", status: "on_road", latitude: 28.6139, longitude: 77.2090 };
const emptyContact = { vehicle_id: "", name: "", phone: "", relation: "", address: "" };
const emptyAccount = { name: "", email: "", password: "", role: "police", phone: "", station_name: "", station_address: "", jurisdiction_area: "" };

function cls(...parts) { return parts.filter(Boolean).join(" "); }
function formatDate(value) { return value ? new Date(value).toLocaleString() : "N/A"; }
function roleLabel(role) { return ({ superadmin: "Super Admin", police: "Police Station", hospital: "Hospital", public: "Family Account" })[role] || role; }
function vehicleIcon(type) { return type === "bus" ? "B" : type === "truck" ? "T" : "C"; }
function severityClass(sev) {
  return {
    low: "bg-yellow-100 text-yellow-800 border-yellow-300",
    medium: "bg-orange-100 text-orange-800 border-orange-300",
    high: "bg-red-100 text-danger border-red-300",
    critical: "bg-danger text-white border-danger"
  }[(sev || "").toLowerCase()] || "bg-slate-100 text-slate-700 border-slate-300";
}

function Icon({ name, className = "w-4 h-4" }) {
  return <i data-lucide={name} className={className}></i>;
}

function App() {
  const [token, setToken] = useState(localStorage.getItem("token") || "");
  const [user, setUser] = useState(() => JSON.parse(localStorage.getItem("user") || "null"));
  const [login, setLogin] = useState({ email: "admin@gov.in", password: "admin123" });
  const [publicSignup, setPublicSignup] = useState({ name: "", email: "", password: "", phone: "", plate_number: "" });
  const [page, setPage] = useState("dashboard");
  const [loading, setLoading] = useState(false);
  const [toast, setToast] = useState("");
  const [vehicles, setVehicles] = useState([]);
  const [accidents, setAccidents] = useState([]);
  const [stations, setStations] = useState([]);
  const [users, setUsers] = useState([]);
  const [smsLogs, setSmsLogs] = useState([]);
  const [pushLogs, setPushLogs] = useState([]);
  const [operations, setOperations] = useState(null);
  const [devices, setDevices] = useState([]);
  const [profiles, setProfiles] = useState([]);
  const [dispatches, setDispatches] = useState([]);
  const [auditLogs, setAuditLogs] = useState([]);
  const [newDevice, setNewDevice] = useState({ vehicle_id: "", device_uid: "", firmware_version: "1.0.0" });
  const [deviceKey, setDeviceKey] = useState("");
  const [profileForm, setProfileForm] = useState({ vehicle_id: "", blood_group: "", allergies: "", medical_conditions: "", emergency_notes: "", consent_given: false });
  const [daily, setDaily] = useState(null);
  const [monthly, setMonthly] = useState(null);
  const [filters, setFilters] = useState({ q: "", severity: "", status: "" });
  const [newStation, setNewStation] = useState(emptyStation);
  const [newVehicle, setNewVehicle] = useState(emptyVehicle);
  const [newContact, setNewContact] = useState(emptyContact);
  const [newAccount, setNewAccount] = useState(emptyAccount);
  const [passwordForm, setPasswordForm] = useState({ current_password: "", new_password: "" });
  const [resetPassword, setResetPassword] = useState({});
  const [selectedAccident, setSelectedAccident] = useState(null);

  useEffect(() => { lucide.createIcons(); });

  useEffect(() => {
    if (!token) return;

    if (user?.role === "public") {
      fetchAll();
      return;
    }

    fetchAll();
    let socket;
    let reconnectTimer;
    let stopped = false;

    const connect = () => {
      if (stopped) return;
      socket = new WebSocket(`${location.protocol === "https:" ? "wss" : "ws"}://${location.host}/ws/alerts`);
      socket.onmessage = (event) => {
        const payload = JSON.parse(event.data);
        if (payload.event === "new_accident") {
          setAccidents(prev => [payload.data, ...prev.filter(a => a.id !== payload.data.id)]);
          setSelectedAccident(payload.data);
          notify(`New ${payload.data.severity.toUpperCase()} accident: ${payload.data.plate_number}`);
          fetchAll();
        }
        if (payload.event === "status_update") {
          setAccidents(prev => prev.map(a => a.id === payload.data.id ? { ...a, ...payload.data } : a));
          notify(`Incident #${payload.data.id} status updated`);
        }
      };
      socket.onclose = () => {
        if (!stopped) reconnectTimer = setTimeout(connect, 3000);
      };
      socket.onerror = () => socket.close();
    };

    connect();
    return () => {
      stopped = true;
      clearTimeout(reconnectTimer);
      if (socket) {
        socket.onclose = null;
        socket.close();
      }
    };
  }, [token]);

  const authHeaders = () => ({ "Authorization": `Bearer ${token}` });
  const jsonHeaders = () => ({ ...authHeaders(), "Content-Type": "application/json" });
  const notify = (message) => { setToast(message); setTimeout(() => setToast(""), 5500); };

  async function api(path, options = {}) {
    const res = await fetch(`${API}${path}`, options);
    const data = res.headers.get("content-type")?.includes("application/json") ? await res.json() : await res.text();
    if (!res.ok) throw new Error(data.detail || data.message || "Request failed");
    return data;
  }

  async function fetchAll() {
    setLoading(true);
    try {
      if (user?.role === "public") {
        const familyAccidents = await api("/accidents/family", { headers: authHeaders() });
        setAccidents(familyAccidents);
        setSelectedAccident(familyAccidents[0] || null);
        return;
      }
      const [vehicleData, stationData, accidentData, dailyData, monthlyData] = await Promise.all([
        api("/vehicles", { headers: authHeaders() }),
        api("/stations", { headers: authHeaders() }),
        api("/accidents", { headers: authHeaders() }),
        api("/reports/daily", { headers: authHeaders() }),
        api("/reports/monthly", { headers: authHeaders() })
      ]);
      setVehicles(vehicleData);
      setStations(stationData);
      setAccidents(accidentData);
      setDaily(dailyData);
      setMonthly(monthlyData);
      const [operationsData, deviceData, profileData, dispatchData] = await Promise.all([
        api("/operations/overview", { headers: authHeaders() }),
        api("/operations/devices", { headers: authHeaders() }),
        api("/operations/profiles", { headers: authHeaders() }),
        api("/operations/dispatches", { headers: authHeaders() })
      ]);
      setOperations(operationsData);
      setDevices(deviceData);
      setProfiles(profileData);
      setDispatches(dispatchData);
      if (user?.role === "superadmin") {
        const [userData, smsData, pushData, auditData] = await Promise.all([
          api("/auth/users", { headers: authHeaders() }),
          api("/alerts/virtual-gateway/sms-logs", { headers: authHeaders() }),
          api("/alerts/virtual-gateway/push-logs", { headers: authHeaders() }),
          api("/operations/audit", { headers: authHeaders() })
        ]);
        setUsers(userData);
        setSmsLogs(smsData);
        setPushLogs(pushData);
        setAuditLogs(auditData);
      }
    } catch (err) {
      notify(err.message);
    } finally {
      setLoading(false);
    }
  }

  async function handleLogin(e) {
    e.preventDefault();
    setLoading(true);
    try {
      const data = await api("/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(login)
      });
      localStorage.setItem("token", data.access_token);
      localStorage.setItem("user", JSON.stringify(data.user));
      setToken(data.access_token);
      setUser(data.user);
      setPage(data.user.role === "public" ? "family" : "dashboard");
      notify(`Secure session started for ${data.user.name}`);
    } catch (err) {
      notify(err.message);
    } finally {
      setLoading(false);
    }
  }

  function logout() {
    localStorage.removeItem("token");
    localStorage.removeItem("user");
    setToken("");
    setUser(null);
    setPage("dashboard");
  }

  async function createAccount(e) {
    e.preventDefault();
    try {
      await api("/auth/register", { method: "POST", headers: jsonHeaders(), body: JSON.stringify(newAccount) });
      setNewAccount(emptyAccount);
      notify("Government account registered");
      fetchAll();
    } catch (err) { notify(err.message); }
  }

  async function changePassword(e) {
    e.preventDefault();
    try {
      await api("/auth/change-password", { method: "PATCH", headers: jsonHeaders(), body: JSON.stringify(passwordForm) });
      setPasswordForm({ current_password: "", new_password: "" });
      notify("Login password changed");
    } catch (err) { notify(err.message); }
  }

  async function resetUserPassword(userId) {
    try {
      await api(`/auth/users/${userId}/password`, { method: "PATCH", headers: jsonHeaders(), body: JSON.stringify({ new_password: resetPassword[userId] || "" }) });
      setResetPassword({ ...resetPassword, [userId]: "" });
      notify("Account password reset");
    } catch (err) { notify(err.message); }
  }

  async function addStation(e) {
    e.preventDefault();
    try {
      await api("/stations", { method: "POST", headers: jsonHeaders(), body: JSON.stringify({ ...newStation, latitude: Number(newStation.latitude), longitude: Number(newStation.longitude) }) });
      setNewStation(emptyStation);
      notify("Station registered");
      fetchAll();
    } catch (err) { notify(err.message); }
  }

  async function addVehicle(e) {
    e.preventDefault();
    try {
      const vehicle = await api("/vehicles", { method: "POST", headers: jsonHeaders(), body: JSON.stringify({ ...newVehicle, latitude: Number(newVehicle.latitude), longitude: Number(newVehicle.longitude) }) });
      setNewVehicle(emptyVehicle);
      setNewContact({ ...newContact, vehicle_id: String(vehicle.id) });
      notify("Vehicle registered. Add home contact next.");
      fetchAll();
    } catch (err) { notify(err.message); }
  }

  async function addContact(e) {
    e.preventDefault();
    try {
      await api("/emergency-contacts", { method: "POST", headers: jsonHeaders(), body: JSON.stringify({ ...newContact, vehicle_id: Number(newContact.vehicle_id) }) });
      setNewContact(emptyContact);
      notify("Emergency home contact linked");
    } catch (err) { notify(err.message); }
  }

  async function updateStatus(accidentId, role, status) {
    const path = role === "police" ? "police-status" : "hospital-status";
    const body = role === "police" ? { police_status: status } : { hospital_status: status };
    try {
      await api(`/accidents/${accidentId}/${path}`, { method: "PATCH", headers: jsonHeaders(), body: JSON.stringify(body) });
      notify("Responder status updated");
      fetchAll();
    } catch (err) { notify(err.message); }
  }

  async function triggerSimulation() {
    if (!vehicles.length) return notify("Register a vehicle first");
    const vehicle = vehicles[Math.floor(Math.random() * vehicles.length)];
    const payload = {
      vehicle_id: vehicle.id,
      latitude: +(8 + Math.random() * 29).toFixed(6),
      longitude: +(68 + Math.random() * 29).toFixed(6),
      severity: ["low", "medium", "high", "critical"][Math.floor(Math.random() * 4)],
      sensor_data: {
        impact_force: +(50 + Math.random() * 450).toFixed(2),
        gyroscope_x: +(-180 + Math.random() * 360).toFixed(2),
        gyroscope_y: +(-180 + Math.random() * 360).toFixed(2),
        speed_at_impact: +(40 + Math.random() * 140).toFixed(2)
      }
    };
    try {
      await api("/accidents/trigger", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) });
      notify("Simulated chip accident trigger sent");
      fetchAll();
    } catch (err) { notify(err.message); }
  }

  async function exportReport(format) {
    try {
      const res = await fetch(`${API}/reports/export?format=${format}`, { headers: authHeaders() });
      if (!res.ok) throw new Error("Export failed");
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = format === "pdf" ? "government_national_accident_report.pdf" : "government_accident_report.csv";
      link.click();
      URL.revokeObjectURL(url);
    } catch (err) { notify(err.message); }
  }

  async function registerDevice(e) {
    e.preventDefault();
    try {
      const result = await api("/operations/devices", { method: "POST", headers: jsonHeaders(), body: JSON.stringify({ ...newDevice, vehicle_id: Number(newDevice.vehicle_id) }) });
      setDeviceKey(`${result.device_uid}: ${result.api_key}`);
      setNewDevice({ vehicle_id: "", device_uid: "", firmware_version: "1.0.0" });
      notify("Secure vehicle device registered");
      fetchAll();
    } catch (err) { notify(err.message); }
  }

  async function saveEmergencyProfile(e) {
    e.preventDefault();
    try {
      await api("/operations/profiles", { method: "PUT", headers: jsonHeaders(), body: JSON.stringify({ ...profileForm, vehicle_id: Number(profileForm.vehicle_id) }) });
      setProfileForm({ vehicle_id: "", blood_group: "", allergies: "", medical_conditions: "", emergency_notes: "", consent_given: false });
      notify("Consent-based emergency profile saved");
      fetchAll();
    } catch (err) { notify(err.message); }
  }

  async function acknowledgeDispatch(dispatch) {
    const unit = window.prompt("Responder unit name", dispatch.assigned_unit || "Unit 01");
    if (!unit) return;
    const eta = Number(window.prompt("Estimated arrival time (minutes)", dispatch.eta_minutes || 10));
    try {
      await api(`/operations/dispatches/${dispatch.id}`, { method: "PATCH", headers: jsonHeaders(), body: JSON.stringify({ status: "acknowledged", assigned_unit: unit, eta_minutes: eta }) });
      notify("Dispatch acknowledged");
      fetchAll();
    } catch (err) { notify(err.message); }
  }

  async function escalateDispatch(id) {
    try {
      await api(`/operations/dispatches/${id}/escalate`, { method: "POST", headers: authHeaders() });
      notify("Dispatch escalated to the next response level");
      fetchAll();
    } catch (err) { notify(err.message); }
  }

  const activeAccidents = accidents.filter(a => !(a.police_status === "resolved" && a.hospital_status === "treated"));
  const filteredAccidents = accidents.filter(a => {
    const q = filters.q.toLowerCase();
    const text = `${a.location_address} ${a.vehicle?.plate_number || a.plate_number || ""} ${a.vehicle?.owner_name || a.owner_name || ""}`.toLowerCase();
    return (!q || text.includes(q)) && (!filters.severity || a.severity === filters.severity) && (!filters.status || a.police_status === filters.status || a.hospital_status === filters.status);
  });

  if (!token) return (
    <Login
      login={login}
      setLogin={setLogin}
      publicSignup={publicSignup}
      setPublicSignup={setPublicSignup}
      handleLogin={handleLogin}
      setToken={setToken}
      setUser={setUser}
      setPage={setPage}
      notify={notify}
      api={api}
      loading={loading}
      setLoading={setLoading}
      toast={toast}
    />
  );

  return (
    <div className="min-h-screen bg-white">
      <Header user={user} page={page} setPage={setPage} logout={logout} />
      {toast && <div className="fixed right-4 top-4 z-[9999] max-w-md rounded border border-borderBlue bg-white px-4 py-3 text-sm font-bold text-primary shadow-lg">{toast}</div>}
      <main className="mx-auto max-w-[1500px] px-4 py-5">
        {user?.role === "public" && <FamilyStatus user={user} accidents={accidents} fetchAll={fetchAll} loading={loading} />}
        {user?.role !== "public" && page === "dashboard" && <Dashboard vehicles={vehicles} stations={stations} accidents={accidents} activeAccidents={activeAccidents} daily={daily} selectedAccident={selectedAccident} setSelectedAccident={setSelectedAccident} triggerSimulation={triggerSimulation} updateStatus={updateStatus} />}
        {user?.role !== "public" && page === "alerts" && <Alerts accidents={filteredAccidents} filters={filters} setFilters={setFilters} updateStatus={updateStatus} setSelectedAccident={setSelectedAccident} setPage={setPage} />}
        {page === "tracker" && <Tracker vehicles={vehicles} stations={stations} accidents={accidents} selectedAccident={selectedAccident} />}
        {page === "history" && <History accidents={filteredAccidents} filters={filters} setFilters={setFilters} exportReport={exportReport} />}
        {page === "stations" && <Stations stations={stations} accidents={accidents} newStation={newStation} setNewStation={setNewStation} addStation={addStation} />}
        {page === "vehicles" && <Vehicles vehicles={vehicles} newVehicle={newVehicle} setNewVehicle={setNewVehicle} newContact={newContact} setNewContact={setNewContact} addVehicle={addVehicle} addContact={addContact} />}
        {page === "reports" && <Reports daily={daily} monthly={monthly} accidents={accidents} exportReport={exportReport} />}
        {page === "operations" && <Operations user={user} operations={operations} devices={devices} profiles={profiles} dispatches={dispatches} auditLogs={auditLogs} vehicles={vehicles} newDevice={newDevice} setNewDevice={setNewDevice} deviceKey={deviceKey} registerDevice={registerDevice} profileForm={profileForm} setProfileForm={setProfileForm} saveEmergencyProfile={saveEmergencyProfile} acknowledgeDispatch={acknowledgeDispatch} escalateDispatch={escalateDispatch} />}
        {page === "admin" && <Admin user={user} users={users} newAccount={newAccount} setNewAccount={setNewAccount} createAccount={createAccount} passwordForm={passwordForm} setPasswordForm={setPasswordForm} changePassword={changePassword} resetPassword={resetPassword} setResetPassword={setResetPassword} resetUserPassword={resetUserPassword} smsLogs={smsLogs} pushLogs={pushLogs} fetchAll={fetchAll} />}
      </main>
      {loading && <div className="fixed bottom-4 right-4 rounded bg-primary px-4 py-2 text-sm font-bold text-white shadow-lg">Loading secure data...</div>}
    </div>
  );
}

// -------------------------------------------------------------
// LOGIN & 2-STEP OTP SIGNUP COMPONENT
// -------------------------------------------------------------
function Login(props) {
  const { login, setLogin, publicSignup, setPublicSignup, handleLogin, setToken, setUser, setPage, notify, api, loading, setLoading, toast } = props;
  const [mode, setMode] = useState("family-login"); // "family-login" | "family-signup" | "staff-login"
  const [signupStep, setSignupStep] = useState("details"); // "details" | "otp_verify"
  const [otpCode, setOtpCode] = useState("");
  const [devOtpHint, setDevOtpHint] = useState("");

  const familySignup = mode === "family-signup";
  const staffLogin = mode === "staff-login";

  // Step 1: Request OTP
  async function handleSendOtp(e) {
    e.preventDefault();
    if (!publicSignup.name || !publicSignup.email || !publicSignup.password || !publicSignup.phone || !publicSignup.plate_number) {
      notify("Please fill in all required registration fields.");
      return;
    }
    setLoading(true);
    try {
      const res = await api("/auth/send-signup-otp", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: publicSignup.name,
          email: publicSignup.email,
          phone: publicSignup.phone,
          plate_number: publicSignup.plate_number
        })
      });
      if (res.dev_otp) {
        setDevOtpHint(res.dev_otp);
      }
      setSignupStep("otp_verify");
      notify(`Verification OTP sent to ${publicSignup.email} and ${publicSignup.phone}`);
    } catch (err) {
      notify(err.message);
    } finally {
      setLoading(false);
    }
  }

  // Step 2: Verify OTP & Complete Registration
  async function handleVerifyOtp(e) {
    e.preventDefault();
    if (!otpCode || otpCode.trim().length < 4) {
      notify("Please enter the verification OTP code.");
      return;
    }
    setLoading(true);
    try {
      const data = await api("/auth/verify-signup-otp", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          ...publicSignup,
          otp_code: otpCode.trim()
        })
      });
      localStorage.setItem("token", data.access_token);
      localStorage.setItem("user", JSON.stringify(data.user));
      setToken(data.access_token);
      setUser(data.user);
      setPage("family");
      notify(`Registration Complete! A confirmation welcome email has been sent to ${data.user.email}`);
    } catch (err) {
      notify(err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen bg-primary text-white">
      {toast && <div className="fixed right-4 top-4 z-50 max-w-md rounded border border-borderBlue bg-white px-4 py-3 text-sm font-bold text-primary shadow-xl">{toast}</div>}
      <div className="grid min-h-screen lg:grid-cols-[1fr_500px]">
        {/* Left hero banner */}
        <section className="flex flex-col justify-between p-8 md:p-12">
          <div className="flex items-center gap-3">
            <div className="grid h-12 w-12 place-items-center rounded border border-blue-300 bg-white text-primary">
              <Icon name="shield-alert" className="h-7 w-7" />
            </div>
            <div>
              <p className="text-xs font-black uppercase tracking-[.22em] text-blue-200">Government Emergency Portal</p>
              <h1 className="text-2xl font-black">Accident Family Status & Response</h1>
            </div>
          </div>
          <div className="max-w-3xl py-12">
            <p className="mb-4 inline-flex items-center gap-2 rounded border border-blue-300 bg-blue-800 px-3 py-1 text-xs font-black uppercase">
              <Icon name="heart-handshake" /> Verified Family Support Access
            </p>
            <h2 className="text-4xl md:text-5xl font-black leading-tight">
              See your family vehicle's accident location and emergency response in real-time.
            </h2>
            <p className="mt-5 max-w-2xl text-lg font-medium text-blue-100">
              Family accounts are securely verified against registered emergency contact numbers. Verify with a one-time OTP and receive an instant confirmation email upon account activation.
            </p>
          </div>
          <p className="text-xs font-bold text-blue-200">
            National Emergency Helpline: Contact <span className="underline font-black text-white">112</span> immediately for life-threatening emergencies.
          </p>
        </section>

        {/* Right Authentication Form */}
        <section className="flex items-center bg-white p-6 md:p-10 text-primary">
          <div className="w-full rounded-xl border border-borderBlue bg-card p-6 shadow-xl">
            {/* Mode selection tabs */}
            <div className="mb-6 grid grid-cols-3 rounded border border-borderBlue bg-white p-1 text-xs font-black">
              <button
                type="button"
                onClick={() => { setMode("family-login"); setSignupStep("details"); }}
                className={cls("rounded py-2 transition", mode === "family-login" ? "bg-primary text-white shadow" : "text-primary hover:bg-slate-50")}
              >
                Login
              </button>
              <button
                type="button"
                onClick={() => { setMode("family-signup"); setSignupStep("details"); }}
                className={cls("rounded py-2 transition", familySignup ? "bg-primary text-white shadow" : "text-primary hover:bg-slate-50")}
              >
                Sign Up (OTP)
              </button>
              <button
                type="button"
                onClick={() => { setMode("staff-login"); setSignupStep("details"); }}
                className={cls("rounded py-2 transition", staffLogin ? "bg-primary text-white shadow" : "text-primary hover:bg-slate-50")}
              >
                Staff Access
              </button>
            </div>

            {/* FAMILY SIGNUP FLOW WITH 2-STEP OTP */}
            {familySignup ? (
              signupStep === "details" ? (
                /* Step 1: Enter details and request OTP */
                <form onSubmit={handleSendOtp} className="space-y-3">
                  <div className="flex items-center gap-3 pb-1 border-b border-borderBlue">
                    <div className="grid h-11 w-11 place-items-center rounded bg-primary text-white">
                      <Icon name="user-plus" className="h-6 w-6" />
                    </div>
                    <div>
                      <h2 className="text-lg font-black">Create Family Account</h2>
                      <p className="text-xs font-semibold text-slate-500">Step 1 of 2: Details & Emergency Match</p>
                    </div>
                  </div>

                  <Input label="Your Full Name" value={publicSignup.name} onChange={v => setPublicSignup({ ...publicSignup, name: v })} placeholder="e.g. Priya Kumar" />
                  <Input label="Email Address (For Verification & Confirmation Mail)" type="email" value={publicSignup.email} onChange={v => setPublicSignup({ ...publicSignup, email: v })} placeholder="priya@example.com" />
                  <Input label="Create Password" type="password" value={publicSignup.password} onChange={v => setPublicSignup({ ...publicSignup, password: v })} placeholder="Minimum 6 characters" />
                  <Input label="Registered Family Phone Number" type="tel" value={publicSignup.phone} onChange={v => setPublicSignup({ ...publicSignup, phone: v })} placeholder="e.g. +919876543212" />
                  <Input label="Family Vehicle Plate Number" value={publicSignup.plate_number} onChange={v => setPublicSignup({ ...publicSignup, plate_number: v.toUpperCase() })} placeholder="e.g. DL-1CA-1234" />

                  <p className="text-[11px] font-semibold text-slate-500">
                    * Phone and Plate must match the emergency contact linked by the vehicle owner.
                  </p>

                  <button
                    type="submit"
                    disabled={loading}
                    className="flex w-full items-center justify-center gap-2 rounded bg-primary px-4 py-3 font-black text-white hover:bg-primaryLight shadow transition"
                  >
                    <Icon name="send" /> {loading ? "Verifying Vehicle..." : "Send Verification OTP"}
                  </button>
                </form>
              ) : (
                /* Step 2: Enter OTP Code */
                <form onSubmit={handleVerifyOtp} className="space-y-4">
                  <div className="flex items-center gap-3 pb-1 border-b border-borderBlue">
                    <div className="grid h-11 w-11 place-items-center rounded bg-success text-white">
                      <Icon name="shield-check" className="h-6 w-6" />
                    </div>
                    <div>
                      <h2 className="text-lg font-black">Verify One-Time Password</h2>
                      <p className="text-xs font-semibold text-slate-500">Step 2 of 2: OTP Verification</p>
                    </div>
                  </div>

                  <div className="rounded border border-blue-200 bg-blue-50 p-3 text-xs text-blue-900">
                    <p className="font-bold">A 6-digit OTP has been sent to:</p>
                    <p className="mt-1 font-semibold text-primary">&#9993; {publicSignup.email}</p>
                    <p className="font-semibold text-primary">&#128222; {publicSignup.phone}</p>
                  </div>

                  {devOtpHint && (
                    <div className="rounded border border-amber-300 bg-amber-50 p-2 text-center text-xs text-amber-900">
                      <span className="font-bold">Development Test OTP:</span> <span className="font-mono text-base font-black tracking-widest text-primary">{devOtpHint}</span>
                    </div>
                  )}

                  <div>
                    <label className="block text-xs font-black uppercase text-primary mb-1">
                      Enter 6-Digit OTP Code
                    </label>
                    <input
                      className="otp-input w-full rounded border border-borderBlue px-3 py-3 text-slate-900 shadow-inner"
                      type="text"
                      maxLength={6}
                      placeholder="······"
                      value={otpCode}
                      onChange={e => setOtpCode(e.target.value.replace(/\D/g, ""))}
                      autoFocus
                    />
                    <p className="mt-1 text-[11px] text-slate-500 text-center">Code is valid for 10 minutes</p>
                  </div>

                  <button
                    type="submit"
                    disabled={loading || otpCode.length < 4}
                    className="flex w-full items-center justify-center gap-2 rounded bg-success px-4 py-3 font-black text-white hover:bg-green-700 shadow transition"
                  >
                    <Icon name="check-circle" /> {loading ? "Verifying..." : "Verify & Complete Signup"}
                  </button>

                  <div className="flex items-center justify-between pt-2 text-xs">
                    <button
                      type="button"
                      onClick={handleSendOtp}
                      disabled={loading}
                      className="font-bold text-primary hover:underline flex items-center gap-1"
                    >
                      <Icon name="refresh-cw" className="w-3 h-3" /> Resend Code
                    </button>
                    <button
                      type="button"
                      onClick={() => setSignupStep("details")}
                      className="font-bold text-slate-500 hover:text-slate-800"
                    >
                      Edit Info &larr;
                    </button>
                  </div>
                </form>
              )
            ) : (
              /* LOGIN FORM (Family or Staff) */
              <form onSubmit={handleLogin} className="space-y-3">
                <div className="mb-3 flex items-center gap-3 pb-1 border-b border-borderBlue">
                  <div className="grid h-11 w-11 place-items-center rounded bg-primary text-white">
                    <Icon name={staffLogin ? "key-round" : "heart-handshake"} className="h-6 w-6" />
                  </div>
                  <div>
                    <h2 className="text-lg font-black">{staffLogin ? "Staff Portal Login" : "Family Portal Login"}</h2>
                    <p className="text-xs font-semibold text-slate-500">{staffLogin ? "Police, Hospital & Superadmin Access" : "Check Your Family's Vehicle Status"}</p>
                  </div>
                </div>

                <Input label="Login ID / Email Address" type="email" value={login.email} onChange={v => setLogin({ ...login, email: v })} />
                <Input label="Password" type="password" value={login.password} onChange={v => setLogin({ ...login, password: v })} />

                <button
                  type="submit"
                  disabled={loading}
                  className="flex w-full items-center justify-center gap-2 rounded bg-primary px-4 py-3 font-black text-white hover:bg-primaryLight shadow transition"
                >
                  <Icon name="log-in" /> {loading ? "Authenticating..." : "Sign In"}
                </button>

                {staffLogin ? (
                  <div className="rounded border border-borderBlue bg-blue-50 p-2.5 text-xs text-slate-600">
                    <p className="font-bold text-primary">Default Staff Demo Accounts:</p>
                    <p className="mt-0.5"><span className="font-semibold">Superadmin:</span> admin@gov.in / admin123</p>
                    <p className="mt-0.5"><span className="font-semibold">Police:</span> police_delhi@gov.in / police123</p>
                    <p className="mt-0.5"><span className="font-semibold">Hospital:</span> hospital_delhi@gov.in / hospital123</p>
                  </div>
                ) : (
                  <p className="text-xs text-center text-slate-500">
                    Don't have an account yet? Switch to the <button type="button" onClick={() => { setMode("family-signup"); setSignupStep("details"); }} className="font-black text-primary underline">Sign Up (OTP)</button> tab.
                  </p>
                )}
              </form>
            )}
          </div>
        </section>
      </div>
    </div>
  );
}

// -------------------------------------------------------------
// FAMILY ACCIDENT STATUS COMPONENT
// -------------------------------------------------------------
function FamilyStatus({ user, accidents, fetchAll, loading }) {
  return (
    <main className="mx-auto max-w-5xl px-4 py-8">
      <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="text-xs font-black uppercase text-primaryLight">Family Incident Tracking</p>
          <h2 className="text-3xl font-black text-primary">Welcome, {user.name}</h2>
          <p className="mt-1 text-slate-600">Authorized access for your linked family vehicle. Real-time emergency dispatch updates appear below.</p>
        </div>
        <button onClick={fetchAll} disabled={loading} className="flex items-center gap-2 rounded border border-primary px-4 py-2 text-sm font-black text-primary hover:bg-card transition">
          <Icon name="refresh-cw" /> Refresh Status
        </button>
      </div>
      {accidents.length ? (
        <div className="space-y-4">
          {accidents.map(accident => (
            <article key={accident.id} className="border border-borderBlue bg-white p-5 rounded-lg shadow-sm">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <p className="text-xs font-black uppercase text-slate-500">Family Vehicle: <span className="text-primary font-black">{accident.vehicle_plate}</span></p>
                  <h3 className="mt-1 text-xl font-black text-primary">Incident Logged {formatDate(accident.timestamp)}</h3>
                </div>
                <span className={cls("rounded border px-3 py-1 text-xs font-black uppercase", severityClass(accident.severity))}>
                  Severity: {accident.severity}
                </span>
              </div>
              <div className="mt-5 grid gap-4 md:grid-cols-2">
                <div className="border-l-4 border-danger bg-red-50 p-4 rounded-r">
                  <p className="flex items-center gap-2 text-xs font-black uppercase text-danger">
                    <Icon name="map-pin" /> Incident Location
                  </p>
                  <p className="mt-2 font-bold text-slate-800">{accident.location_address}</p>
                  <a className="mt-3 inline-flex items-center gap-2 text-sm font-black text-primary underline" target="_blank" rel="noreferrer" href={`https://www.google.com/maps?q=${accident.latitude},${accident.longitude}`}>
                    <Icon name="map" /> Open in Google Maps
                  </a>
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <div className="border border-borderBlue p-4 rounded bg-card">
                    <p className="text-xs font-black uppercase text-slate-500">Police Response</p>
                    <p className="mt-2 font-black text-primary text-lg">{accident.police_status.replaceAll("_", " ").toUpperCase()}</p>
                  </div>
                  <div className="border border-borderBlue p-4 rounded bg-card">
                    <p className="text-xs font-black uppercase text-slate-500">Hospital Response</p>
                    <p className="mt-2 font-black text-primary text-lg">{accident.hospital_status.replaceAll("_", " ").toUpperCase()}</p>
                  </div>
                </div>
              </div>
            </article>
          ))}
        </div>
      ) : (
        <div className="border border-borderBlue bg-card p-12 text-center rounded-lg">
          <Icon name="circle-check-big" className="mx-auto h-12 w-12 text-success" />
          <h3 className="mt-3 text-xl font-black text-primary">All Clear &bull; No Incidents Reported</h3>
          <p className="mt-1 text-slate-600 max-w-md mx-auto">There are currently no active accident alerts or emergency dispatch jobs registered for your vehicle.</p>
        </div>
      )}
    </main>
  );
}

// -------------------------------------------------------------
// NAVIGATION HEADER
// -------------------------------------------------------------
function Header({ user, page, setPage, logout }) {
  if (user?.role === "public") {
    return (
      <header className="border-b border-borderBlue bg-primary text-white">
        <div className="mx-auto flex max-w-5xl items-center justify-between gap-4 px-4 py-3">
          <div className="flex items-center gap-3">
            <div className="grid h-10 w-10 place-items-center rounded border border-blue-300 bg-white text-primary">
              <Icon name="heart-handshake" className="h-5 w-5" />
            </div>
            <div>
              <h1 className="text-base font-black">Accident Family Status Portal</h1>
              <p className="text-xs font-bold text-blue-200">Logged in as {user.name} ({user.email})</p>
            </div>
          </div>
          <button onClick={logout} className="flex items-center gap-2 rounded border border-red-300 bg-danger px-3 py-2 text-xs font-black text-white hover:bg-red-700">
            <Icon name="log-out" /> Logout
          </button>
        </div>
      </header>
    );
  }

  const nav = [
    ["dashboard", "Dashboard", "layout-dashboard"],
    ["alerts", "Accident Alerts", "siren"],
    ["tracker", "Live Tracker", "map"],
    ["history", "History", "table"],
    ["stations", "Stations", "building-2"],
    ["vehicles", "Vehicles", "car"],
    ["reports", "Reports", "bar-chart-3"],
    ["operations", "Real-Life Ops", "activity"],
    ["admin", "Admin Panel", "shield-check"]
  ].filter(item => item[0] !== "admin" || user?.role === "superadmin");

  return (
    <header className="border-b border-borderBlue bg-primary text-white">
      <div className="mx-auto flex max-w-[1500px] flex-wrap items-center justify-between gap-4 px-4 py-3">
        <div className="flex items-center gap-3">
          <div className="grid h-11 w-11 place-items-center rounded border border-blue-300 bg-white text-primary">
            <Icon name="shield-alert" className="h-7 w-7" />
          </div>
          <div>
            <h1 className="text-lg font-black">Government Emergency Portal</h1>
            <p className="text-xs font-bold text-blue-200">{roleLabel(user.role)} &mdash; {user.name}</p>
          </div>
        </div>
        <nav className="flex flex-wrap gap-1">
          {nav.map(([id, label, icon]) => (
            <button key={id} onClick={() => setPage(id)} className={cls("flex items-center gap-2 rounded px-3 py-2 text-xs font-black transition", page === id ? "bg-white text-primary shadow" : "text-blue-100 hover:bg-blue-800")}>
              <Icon name={icon} /> {label}
            </button>
          ))}
          <button onClick={logout} className="flex items-center gap-2 rounded bg-danger px-3 py-2 text-xs font-black text-white hover:bg-red-700">
            <Icon name="log-out" /> Logout
          </button>
        </nav>
      </div>
    </header>
  );
}

// -------------------------------------------------------------
// DASHBOARD & MAP PANELS
// -------------------------------------------------------------
function Dashboard(props) {
  const { vehicles, stations, accidents, activeAccidents, daily, triggerSimulation, updateStatus } = props;
  const policeDispatched = accidents.filter(a => a.police_status === "dispatched").length;
  const ambulances = accidents.filter(a => a.hospital_status === "dispatched").length;
  const resolved = accidents.filter(a => a.police_status === "resolved" && a.hospital_status === "treated").length;
  return (
    <div className="grid gap-5 lg:grid-cols-[1fr_420px]">
      <section className="space-y-5">
        <div className="grid gap-3 md:grid-cols-5">
          <Stat label="Accidents Today" value={daily?.total_accidents || 0} icon="calendar-days" />
          <Stat label="Active Alerts" value={activeAccidents.length} icon="radio-tower" tone="danger" />
          <Stat label="Police Dispatched" value={policeDispatched} icon="shield" />
          <Stat label="Ambulances Dispatched" value={ambulances} icon="ambulance" />
          <Stat label="Resolved Cases" value={resolved} icon="check-circle-2" tone="success" />
        </div>
        <div className="h-[620px] rounded-lg border border-borderBlue bg-card p-3">
          <MapPanel vehicles={vehicles} stations={stations} accidents={accidents} selected={props.selectedAccident} />
        </div>
      </section>
      <aside className="space-y-4">
        <button onClick={triggerSimulation} className="flex w-full items-center justify-center gap-2 rounded bg-danger px-4 py-3 font-black text-white shadow hover:bg-red-700 transition">
          <Icon name="zap" /> Simulate Chip Accident Trigger
        </button>
        <Panel title="Real-Time Accident Alert Panel" icon="siren">
          <div className="max-h-[660px] space-y-3 overflow-y-auto pr-1">
            {activeAccidents.length === 0 && <Empty text="No active accidents. Dispatch network is clear." />}
            {activeAccidents.map(a => <AccidentCard key={a.id} accident={a} updateStatus={updateStatus} />)}
          </div>
        </Panel>
      </aside>
    </div>
  );
}

function Stat({ label, value, icon, tone }) {
  const color = tone === "danger" ? "bg-danger" : tone === "success" ? "bg-success" : "bg-primary";
  return (
    <div className="rounded-lg border border-borderBlue bg-card p-4">
      <div className={cls("mb-3 grid h-9 w-9 place-items-center rounded text-white", color)}><Icon name={icon} /></div>
      <p className="text-2xl font-black">{value}</p>
      <p className="text-xs font-black uppercase text-slate-500">{label}</p>
    </div>
  );
}

function MapPanel({ vehicles, stations, accidents, selected }) {
  const divRef = useRef(null);
  const mapRef = useRef(null);
  const layerRef = useRef(null);
  const indiaCenter = [22.9734, 78.6569];
  const indiaBounds = L.latLngBounds([6.5, 67.0], [37.8, 98.5]);

  useEffect(() => {
    if (!divRef.current) return;

    const map = L.map(divRef.current, {
      maxBounds: indiaBounds,
      maxBoundsViscosity: 1.0,
      minZoom: 4,
      maxZoom: 18,
      worldCopyJump: false,
      preferCanvas: true
    }).setView(indiaCenter, 5);

    mapRef.current = map;
    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
      maxZoom: 19,
      attribution: "&copy; OpenStreetMap",
      updateWhenIdle: false,
      keepBuffer: 4,
      crossOrigin: true
    }).addTo(map);
    layerRef.current = L.layerGroup().addTo(map);
    L.rectangle(indiaBounds, {
      color: "#1E3A8A",
      weight: 2,
      fill: false,
      dashArray: "6 6"
    }).addTo(map);

    let animationFrame;
    const refreshMapSize = () => {
      cancelAnimationFrame(animationFrame);
      animationFrame = requestAnimationFrame(() => map.invalidateSize({ pan: false }));
    };
    const resizeObserver = new ResizeObserver(refreshMapSize);
    resizeObserver.observe(divRef.current);
    window.addEventListener("resize", refreshMapSize);
    const handleVisibility = () => {
      if (!document.hidden) refreshMapSize();
    };
    document.addEventListener("visibilitychange", handleVisibility);

    const sizeTimers = [0, 100, 350].map(delay => setTimeout(refreshMapSize, delay));

    return () => {
      sizeTimers.forEach(clearTimeout);
      cancelAnimationFrame(animationFrame);
      resizeObserver.disconnect();
      window.removeEventListener("resize", refreshMapSize);
      document.removeEventListener("visibilitychange", handleVisibility);
      map.remove();
      mapRef.current = null;
      layerRef.current = null;
    };
  }, []);

  useEffect(() => {
    const map = mapRef.current;
    const markerLayer = layerRef.current;
    if (!map || !markerLayer) return;

    markerLayer.clearLayers();
    vehicles.forEach(v => addMarker(v.latitude, v.longitude, v.status === "accident" ? "bg-danger pulse" : v.status === "parked" ? "bg-slate-500" : "bg-success", vehicleIcon(v.type), `${v.plate_number}<br/>${v.owner_name}<br/>${v.status}`));
    stations.forEach(s => addMarker(s.latitude, s.longitude, s.type === "police" ? "bg-primary" : "bg-white text-danger border-danger", s.type === "police" ? "P" : "+", `${s.name}<br/>${s.phone}`));
    accidents.forEach(a => addMarker(a.latitude, a.longitude, "bg-danger pulse", "!", `${a.vehicle?.plate_number || a.plate_number || "Vehicle"}<br/>${a.severity?.toUpperCase()}<br/>${a.location_address}`));
    if (selected?.latitude != null && selected?.longitude != null && indiaBounds.contains([selected.latitude, selected.longitude])) {
      map.setView([selected.latitude, selected.longitude], 12);
    }
    function addMarker(lat, lon, classes, label, popup) {
      if (lat == null || lon == null) return;
      const icon = L.divIcon({ className: "", html: `<div class="marker-dot ${classes}">${label}</div>`, iconSize: [24, 24], iconAnchor: [12, 12] });
      L.marker([lat, lon], { icon }).bindPopup(popup).addTo(markerLayer);
    }
  }, [vehicles, stations, accidents, selected]);

  return <div ref={divRef} className="h-full w-full"></div>;
}

function Panel({ title, icon, children }) {
  return <section className="rounded-lg border border-borderBlue bg-white p-4 shadow-sm"><div className="mb-4 flex items-center gap-2 border-b border-borderBlue pb-3 text-primary"><Icon name={icon} /><h2 className="font-black">{title}</h2></div>{children}</section>;
}
function Empty({ text }) { return <div className="rounded border border-dashed border-borderBlue bg-card p-6 text-center text-sm font-bold text-slate-500">{text}</div>; }

function AccidentCard({ accident: a, updateStatus, compact }) {
  return (
    <article className="rounded-lg border border-red-200 bg-white shadow-sm">
      <div className="flex items-center justify-between rounded-t-lg bg-danger px-3 py-2 text-white">
        <div className="flex items-center gap-2 font-black"><Icon name="siren" /> Incident #{a.id}</div>
        <span className={cls("rounded border px-2 py-1 text-xs font-black", severityClass(a.severity))}>{a.severity?.toUpperCase()}</span>
      </div>
      <div className="space-y-3 p-3 text-sm">
        <div className="grid gap-2 md:grid-cols-2">
          <Info label="Vehicle" value={`${a.vehicle?.plate_number || a.plate_number || "N/A"} (${a.vehicle?.type || a.vehicle_type || "vehicle"})`} />
          <Info label="Owner" value={`${a.vehicle?.owner_name || a.owner_name || "N/A"} ${a.vehicle?.owner_phone || a.owner_phone || ""}`} />
          <Info label="GPS" value={`${Number(a.latitude).toFixed(4)}, ${Number(a.longitude).toFixed(4)}`} />
          <Info label="Time" value={formatDate(a.timestamp)} />
        </div>
        <Info label="Address" value={a.location_address} />
        {!compact && <div className="grid gap-2 md:grid-cols-2"><Info label="Impact Force" value={`${a.sensor_data?.impact_force || "N/A"} N`} /><Info label="Speed At Impact" value={`${a.sensor_data?.speed_at_impact || "N/A"} km/h`} /></div>}
        <div className="grid gap-2 md:grid-cols-2">
          <Status label="Police" value={a.police_status} />
          <Status label="Hospital" value={a.hospital_status} />
        </div>
        <div className="grid gap-2 md:grid-cols-2">
          <button onClick={() => updateStatus(a.id, "police", a.police_status === "resolved" ? "pending" : "resolved")} className="rounded bg-primary px-3 py-2 text-xs font-black text-white hover:bg-primaryLight">Mark Police Resolved</button>
          <button onClick={() => updateStatus(a.id, "hospital", a.hospital_status === "treated" ? "pending" : "treated")} className="rounded bg-success px-3 py-2 text-xs font-black text-white hover:bg-green-700">Mark Hospital Treated</button>
        </div>
      </div>
    </article>
  );
}
function Info({ label, value }) { return <div><p className="text-[10px] font-black uppercase text-slate-500">{label}</p><p className="font-bold text-slate-800">{value}</p></div>; }
function Status({ label, value }) { return <div className="rounded border border-borderBlue bg-card p-2"><p className="text-[10px] font-black uppercase text-slate-500">{label}</p><p className="font-black text-primary">{value?.toUpperCase()}</p></div>; }

function Filters({ filters, setFilters }) {
  return (
    <div className="grid gap-3 md:grid-cols-3">
      <input className="rounded border border-borderBlue px-3 py-2" placeholder="Search plate, owner, location" value={filters.q} onChange={e => setFilters({ ...filters, q: e.target.value })} />
      <select className="rounded border border-borderBlue px-3 py-2" value={filters.severity} onChange={e => setFilters({ ...filters, severity: e.target.value })}>
        <option value="">All severity</option>
        <option>low</option>
        <option>medium</option>
        <option>high</option>
        <option>critical</option>
      </select>
      <select className="rounded border border-borderBlue px-3 py-2" value={filters.status} onChange={e => setFilters({ ...filters, status: e.target.value })}>
        <option value="">All status</option>
        <option>call_confirmation</option>
        <option>pending</option>
        <option>dispatched</option>
        <option>resolved</option>
        <option>treated</option>
      </select>
    </div>
  );
}

function Alerts({ accidents, filters, setFilters, updateStatus, setSelectedAccident, setPage }) {
  return (
    <Panel title="Accident Alerts" icon="siren">
      <Filters filters={filters} setFilters={setFilters} />
      <div className="mt-4 grid gap-4 xl:grid-cols-2">
        {accidents.map(a => (
          <div key={a.id}>
            <AccidentCard accident={a} updateStatus={updateStatus} />
            <button onClick={() => { setSelectedAccident(a); setPage("tracker"); }} className="mt-2 rounded border border-borderBlue px-3 py-2 text-xs font-black text-primary hover:bg-card">
              View on Map
            </button>
          </div>
        ))}
      </div>
      {!accidents.length && <Empty text="No accident records match the filter." />}
    </Panel>
  );
}

function Tracker({ vehicles, stations, accidents, selectedAccident }) {
  return (
    <Panel title="Live Vehicle Tracker" icon="map">
      <div className="h-[720px] rounded-lg border border-borderBlue bg-card p-3">
        <MapPanel vehicles={vehicles} stations={stations} accidents={accidents} selected={selectedAccident} />
      </div>
    </Panel>
  );
}

function History({ accidents, filters, setFilters, exportReport }) {
  return (
    <Panel title="Accident History" icon="table">
      <Filters filters={filters} setFilters={setFilters} />
      <div className="mt-4 overflow-x-auto">
        <table className="w-full min-w-[1000px] text-left text-sm">
          <thead className="bg-primary text-white">
            <tr>{["Vehicle","Owner","Location","Severity","Time","Police","Hospital","Alerts"].map(h => <th className="px-3 py-2" key={h}>{h}</th>)}</tr>
          </thead>
          <tbody>
            {accidents.map(a => (
              <tr className="border-b border-borderBlue" key={a.id}>
                <td className="px-3 py-2 font-black">{a.vehicle?.plate_number || a.plate_number}</td>
                <td className="px-3 py-2">{a.vehicle?.owner_name || a.owner_name}</td>
                <td className="px-3 py-2">{a.location_address}</td>
                <td className="px-3 py-2"><span className={cls("rounded border px-2 py-1 text-xs font-black", severityClass(a.severity))}>{a.severity}</span></td>
                <td className="px-3 py-2">{formatDate(a.timestamp)}</td>
                <td className="px-3 py-2">{a.police_status}</td>
                <td className="px-3 py-2">{a.hospital_status}</td>
                <td className="px-3 py-2">{a.alerts?.length || "View API"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <ExportButtons exportReport={exportReport} />
    </Panel>
  );
}

function ExportButtons({ exportReport }) {
  return (
    <div className="mt-4 flex gap-2">
      <button onClick={() => exportReport("csv")} className="rounded bg-primary px-4 py-2 text-sm font-black text-white hover:bg-primaryLight">Export CSV</button>
      <button onClick={() => exportReport("pdf")} className="rounded bg-danger px-4 py-2 text-sm font-black text-white hover:bg-red-700">Export PDF</button>
    </div>
  );
}

function Stations({ stations, accidents, newStation, setNewStation, addStation }) {
  return (
    <div className="grid gap-5 lg:grid-cols-[420px_1fr]">
      <Panel title="Add Station" icon="building-2"><StationForm value={newStation} setValue={setNewStation} submit={addStation} /></Panel>
      <Panel title="Stations Management" icon="list">
        <div className="grid gap-3 md:grid-cols-2">
          {stations.map(s => (
            <div className="rounded border border-borderBlue bg-card p-3" key={s.id}>
              <h3 className="font-black">{s.name}</h3>
              <p className="text-sm font-bold text-slate-600">{s.type.toUpperCase()} - {s.jurisdiction_area}</p>
              <p className="text-sm">{s.address}</p>
              <p className="text-sm font-bold">{s.phone}</p>
              <p className="mt-2 text-xs text-slate-500">Handled accidents: {accidents.filter(a => a.assigned_police_id === s.id || a.assigned_hospital_id === s.id).length}</p>
            </div>
          ))}
        </div>
      </Panel>
    </div>
  );
}

function StationForm({ value, setValue, submit }) {
  return (
    <form onSubmit={submit} className="space-y-3">
      <Input label="Name" value={value.name} onChange={v => setValue({ ...value, name: v })} />
      <Select label="Type" value={value.type} onChange={v => setValue({ ...value, type: v })} options={["police","hospital"]} />
      <Input label="Address" value={value.address} onChange={v => setValue({ ...value, address: v })} />
      <Input label="Jurisdiction Area" value={value.jurisdiction_area} onChange={v => setValue({ ...value, jurisdiction_area: v })} />
      <Input label="Phone" value={value.phone} onChange={v => setValue({ ...value, phone: v })} />
      <div className="grid grid-cols-2 gap-2">
        <Input label="Latitude" value={value.latitude} onChange={v => setValue({ ...value, latitude: v })} />
        <Input label="Longitude" value={value.longitude} onChange={v => setValue({ ...value, longitude: v })} />
      </div>
      <Submit label="Register Station" />
    </form>
  );
}

function Vehicles({ vehicles, newVehicle, setNewVehicle, newContact, setNewContact, addVehicle, addContact }) {
  return (
    <div className="grid gap-5 lg:grid-cols-[420px_1fr]">
      <div className="space-y-5">
        <Panel title="Register Vehicle" icon="car"><VehicleForm value={newVehicle} setValue={setNewVehicle} submit={addVehicle} /></Panel>
        <Panel title="Add Emergency Home Contact" icon="phone-call"><ContactForm vehicles={vehicles} value={newContact} setValue={setNewContact} submit={addContact} /></Panel>
      </div>
      <Panel title="Vehicle Registry" icon="list">
        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
          {vehicles.map(v => (
            <div className="rounded border border-borderBlue bg-card p-3" key={v.id}>
              <h3 className="font-black">{v.plate_number}</h3>
              <p className="text-sm font-bold text-slate-600">{v.type.toUpperCase()} - {v.status}</p>
              <p className="text-sm">{v.owner_name} / {v.owner_phone}</p>
              <p className="text-xs text-slate-500">{v.latitude}, {v.longitude}</p>
            </div>
          ))}
        </div>
      </Panel>
    </div>
  );
}

function VehicleForm({ value, setValue, submit }) {
  return (
    <form onSubmit={submit} className="space-y-3">
      <Input label="Owner Name" value={value.owner_name} onChange={v => setValue({ ...value, owner_name: v })} />
      <Input label="Owner Phone" value={value.owner_phone} onChange={v => setValue({ ...value, owner_phone: v })} />
      <Input label="Owner Address" value={value.owner_address} onChange={v => setValue({ ...value, owner_address: v })} />
      <Input label="Plate Number" value={value.plate_number} onChange={v => setValue({ ...value, plate_number: v.toUpperCase() })} />
      <div className="grid grid-cols-2 gap-2">
        <Select label="Type" value={value.type} onChange={v => setValue({ ...value, type: v })} options={["car","bus","truck"]} />
        <Select label="Status" value={value.status} onChange={v => setValue({ ...value, status: v })} options={["on_road","accident","parked"]} />
      </div>
      <div className="grid grid-cols-2 gap-2">
        <Input label="Latitude" value={value.latitude} onChange={v => setValue({ ...value, latitude: v })} />
        <Input label="Longitude" value={value.longitude} onChange={v => setValue({ ...value, longitude: v })} />
      </div>
      <Submit label="Register Vehicle" />
    </form>
  );
}

function ContactForm({ vehicles, value, setValue, submit }) {
  return (
    <form onSubmit={submit} className="space-y-3">
      <label className="block text-xs font-black uppercase text-primary">Vehicle</label>
      <select className="w-full rounded border border-borderBlue px-3 py-2 text-slate-900" value={value.vehicle_id} onChange={e => setValue({ ...value, vehicle_id: e.target.value })}>
        <option value="">Select vehicle</option>
        {vehicles.map(v => <option key={v.id} value={v.id}>{v.plate_number} - {v.owner_name}</option>)}
      </select>
      <Input label="Contact Name" value={value.name} onChange={v => setValue({ ...value, name: v })} />
      <Input label="Phone" value={value.phone} onChange={v => setValue({ ...value, phone: v })} />
      <Input label="Relation" value={value.relation} onChange={v => setValue({ ...value, relation: v })} />
      <Input label="Address" value={value.address} onChange={v => setValue({ ...value, address: v })} />
      <Submit label="Link Contact" />
    </form>
  );
}

function Reports({ daily, monthly, accidents, exportReport }) {
  const chartRef = useRef(null);
  useEffect(() => {
    if (!chartRef.current || !monthly) return;
    const chart = new Chart(chartRef.current, {
      type: "bar",
      data: {
        labels: Object.keys(monthly.by_severity),
        datasets: [{
          label: "Accidents by severity",
          data: Object.values(monthly.by_severity),
          backgroundColor: ["#facc15","#fb923c","#ef4444","#dc2626"]
        }]
      },
      options: { responsive: true, plugins: { legend: { display: false } } }
    });
    return () => chart.destroy();
  }, [monthly]);

  return (
    <div className="grid gap-5 lg:grid-cols-[1fr_420px]">
      <Panel title="Reports & Charts" icon="bar-chart-3">
        <canvas ref={chartRef} height="120"></canvas>
        <div className="mt-5 grid gap-3 md:grid-cols-4">
          <Stat label="30-Day Total" value={monthly?.total_accidents || 0} icon="calendar-range" />
          <Stat label="Critical" value={monthly?.by_severity?.critical || 0} icon="siren" tone="danger" />
          <Stat label="Daily Total" value={daily?.total_accidents || 0} icon="calendar-days" />
          <Stat label="Resolved" value={monthly?.by_status?.resolved || 0} icon="check-circle-2" tone="success" />
        </div>
        <ExportButtons exportReport={exportReport} />
      </Panel>
      <Panel title="Accident Heatmap" icon="map">
        <div className="h-[450px]">
          <MapPanel vehicles={[]} stations={[]} accidents={accidents} />
        </div>
      </Panel>
    </div>
  );
}

function Operations(props) {
  const { user, operations, devices, profiles, dispatches, auditLogs, vehicles, newDevice, setNewDevice, deviceKey, registerDevice, profileForm, setProfileForm, saveEmergencyProfile, acknowledgeDispatch, escalateDispatch } = props;
  const metrics = operations?.metrics || {};
  const plateFor = id => vehicles.find(v => v.id === id)?.plate_number || `Vehicle #${id}`;
  const canHandle = d => user.role === "superadmin" || user.role === d.agency_type;

  return (
    <div className="space-y-5">
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-6">
        <Stat label="Registered Devices" value={metrics.registered_devices || 0} icon="cpu" />
        <Stat label="Online Devices" value={metrics.online_devices || 0} icon="wifi" tone="success" />
        <Stat label="Active Incidents" value={metrics.active_incidents || 0} icon="siren" tone="danger" />
        <Stat label="Pending Dispatch" value={metrics.pending_dispatches || 0} icon="ambulance" />
        <Stat label="Response Stations" value={metrics.stations || 0} icon="building-2" />
        <Stat label="Failed Alerts" value={metrics.failed_alerts || 0} icon="message-square-warning" tone={metrics.failed_alerts ? "danger" : "success"} />
      </div>

      <Panel title="Production Readiness" icon="shield-check">
        <div className="grid gap-2 md:grid-cols-2 xl:grid-cols-3">
          {(operations?.readiness || []).map(item => (
            <div key={item.name} className={cls("flex items-center justify-between rounded border p-3 text-sm font-bold", item.ready ? "border-green-200 bg-green-50 text-green-800" : "border-amber-200 bg-amber-50 text-amber-900")}>
              <span>{item.name}</span>
              <span className="ml-3 whitespace-nowrap">{item.ready ? "READY" : item.external ? "OFFICIAL APPROVAL" : "SETUP NEEDED"}</span>
            </div>
          ))}
        </div>
      </Panel>

      {user.role === "superadmin" && (
        <div className="grid gap-5 xl:grid-cols-2">
          <Panel title="Register Secure Vehicle Device" icon="cpu">
            <form onSubmit={registerDevice} className="space-y-3">
              <label className="block"><span className="mb-1 block text-xs font-black uppercase text-primary">Vehicle</span><select required className="w-full rounded border border-borderBlue px-3 py-2 text-slate-900" value={newDevice.vehicle_id} onChange={e => setNewDevice({ ...newDevice, vehicle_id: e.target.value })}><option value="">Select vehicle</option>{vehicles.map(v => <option key={v.id} value={v.id}>{v.plate_number} — {v.owner_name}</option>)}</select></label>
              <Input label="Hardware Device UID" value={newDevice.device_uid} onChange={v => setNewDevice({ ...newDevice, device_uid: v })} />
              <Input label="Firmware Version" value={newDevice.firmware_version} onChange={v => setNewDevice({ ...newDevice, firmware_version: v })} />
              <Submit label="Register Device & Generate Key" />
              {deviceKey && (
                <div className="rounded border border-amber-300 bg-amber-50 p-3 text-xs text-amber-900">
                  <p className="font-black">COPY THIS DEVICE KEY NOW</p>
                  <code className="break-all">{deviceKey}</code>
                </div>
              )}
            </form>
          </Panel>
          <Panel title="Consent-Based Emergency Profile" icon="heart-pulse">
            <form onSubmit={saveEmergencyProfile} className="space-y-3">
              <label className="block"><span className="mb-1 block text-xs font-black uppercase text-primary">Vehicle</span><select required className="w-full rounded border border-borderBlue px-3 py-2 text-slate-900" value={profileForm.vehicle_id} onChange={e => setProfileForm({ ...profileForm, vehicle_id: e.target.value })}><option value="">Select vehicle</option>{vehicles.map(v => <option key={v.id} value={v.id}>{v.plate_number} — {v.owner_name}</option>)}</select></label>
              <div className="grid gap-3 md:grid-cols-2">
                <Input label="Blood Group" value={profileForm.blood_group} onChange={v => setProfileForm({ ...profileForm, blood_group: v })} />
                <Input label="Allergies" value={profileForm.allergies} onChange={v => setProfileForm({ ...profileForm, allergies: v })} />
              </div>
              <Input label="Medical Conditions" value={profileForm.medical_conditions} onChange={v => setProfileForm({ ...profileForm, medical_conditions: v })} />
              <Input label="Emergency Notes" value={profileForm.emergency_notes} onChange={v => setProfileForm({ ...profileForm, emergency_notes: v })} />
              <label className="flex items-center gap-2 rounded border border-borderBlue p-3 text-sm font-bold text-primary">
                <input type="checkbox" checked={profileForm.consent_given} onChange={e => setProfileForm({ ...profileForm, consent_given: e.target.checked })} /> Owner consent recorded
              </label>
              <Submit label="Save Emergency Profile" />
            </form>
          </Panel>
        </div>
      )}

      <div className="grid gap-5 xl:grid-cols-2">
        <Panel title="Live Hardware Fleet" icon="radio-tower">
          <div className="max-h-[420px] space-y-2 overflow-y-auto">
            {devices.map(d => (
              <div key={d.id} className="grid grid-cols-[1fr_auto] gap-3 rounded border border-borderBlue bg-card p-3">
                <div>
                  <p className="font-black">{d.device_uid} &bull; {plateFor(d.vehicle_id)}</p>
                  <p className="text-xs text-slate-600">Firmware {d.firmware_version} &bull; Last signal {formatDate(d.last_seen)}</p>
                </div>
                <div className="text-right">
                  <span className={cls("rounded px-2 py-1 text-xs font-black", d.status === "online" ? "bg-green-100 text-green-800" : "bg-slate-200 text-slate-700")}>{d.status.toUpperCase()}</span>
                  <p className="mt-2 text-xs font-bold">Battery {d.battery_level}% &bull; Signal {d.network_signal}%</p>
                </div>
              </div>
            ))}
            {!devices.length && <Empty text="No authenticated hardware devices registered yet." />}
          </div>
        </Panel>
        <Panel title="Responder Dispatch Queue" icon="ambulance">
          <div className="max-h-[420px] space-y-2 overflow-y-auto">
            {dispatches.map(d => (
              <div key={d.id} className="rounded border border-borderBlue p-3">
                <div className="flex items-center justify-between">
                  <p className="font-black">Incident #{d.accident_id} &bull; {d.agency_type.toUpperCase()}</p>
                  <span className="rounded bg-card px-2 py-1 text-xs font-black">{d.status.toUpperCase()}</span>
                </div>
                <p className="mt-1 text-xs text-slate-600">Unit: {d.assigned_unit || "Unassigned"} &bull; ETA: {d.eta_minutes ? `${d.eta_minutes} min` : "Pending"} &bull; Escalation L{d.escalation_level}</p>
                <div className="mt-2 flex gap-2">
                  {canHandle(d) && <button onClick={() => acknowledgeDispatch(d)} className="rounded bg-success px-3 py-2 text-xs font-black text-white hover:bg-green-700">Acknowledge + ETA</button>}
                  {user.role === "superadmin" && <button onClick={() => escalateDispatch(d.id)} className="rounded bg-danger px-3 py-2 text-xs font-black text-white hover:bg-red-700">Escalate</button>}
                </div>
              </div>
            ))}
            {!dispatches.length && <Empty text="New accidents will create police and hospital dispatch jobs." />}
          </div>
        </Panel>
      </div>

      <div className="grid gap-5 xl:grid-cols-2">
        <Panel title="Emergency Medical Profiles" icon="heart-pulse">
          <div className="space-y-2">
            {profiles.map(p => (
              <div key={p.id} className="rounded border border-borderBlue p-3 text-sm">
                <p className="font-black">{plateFor(p.vehicle_id)} &bull; Blood {p.blood_group || "Not provided"}</p>
                <p>Allergies: {p.allergies || "None recorded"}</p>
                <p>Conditions: {p.medical_conditions || "None recorded"}</p>
                <p className={p.consent_given ? "font-bold text-green-700" : "font-bold text-danger"}>{p.consent_given ? "Consent recorded" : "Consent missing"}</p>
              </div>
            ))}
            {!profiles.length && <Empty text="No consent-based medical profiles recorded." />}
          </div>
        </Panel>
        <Panel title="Security Audit Trail" icon="scroll-text">
          <div className="max-h-72 space-y-2 overflow-y-auto">
            {auditLogs.slice(0, 30).map(log => (
              <div key={log.id} className="rounded border border-borderBlue p-2 text-xs">
                <p className="font-black">{log.action.replaceAll("_", " ").toUpperCase()}</p>
                <p>{log.actor_email} &bull; {log.entity_type} #{log.entity_id || "-"}</p>
                <p className="text-slate-500">{formatDate(log.created_at)}</p>
              </div>
            ))}
            {user.role !== "superadmin" && <Empty text="Audit history is restricted to super administrators." />}
            {user.role === "superadmin" && !auditLogs.length && <Empty text="Operational changes will appear here." />}
          </div>
        </Panel>
      </div>
    </div>
  );
}

function Admin(props) {
  const { user, users, newAccount, setNewAccount, createAccount, passwordForm, setPasswordForm, changePassword, resetPassword, setResetPassword, resetUserPassword, smsLogs, pushLogs, fetchAll } = props;
  return (
    <div className="grid gap-5 xl:grid-cols-[420px_1fr]">
      <div className="space-y-5">
        <Panel title="Register Government Account" icon="user-plus">
          <AccountForm value={newAccount} setValue={setNewAccount} submit={createAccount} />
        </Panel>
        <Panel title="Change My Login Password" icon="key-round">
          <form onSubmit={changePassword} className="space-y-3">
            <Input label="Current Password" type="password" value={passwordForm.current_password} onChange={v => setPasswordForm({ ...passwordForm, current_password: v })} />
            <Input label="New Password" type="password" value={passwordForm.new_password} onChange={v => setPasswordForm({ ...passwordForm, new_password: v })} />
            <Submit label="Change Password" />
          </form>
        </Panel>
      </div>
      <div className="space-y-5">
        <Panel title="Manage Official Accounts" icon="shield-check">
          <div className="overflow-x-auto">
            <table className="w-full min-w-[850px] text-left text-sm">
              <thead className="bg-primary text-white">
                <tr><th className="px-3 py-2">Name</th><th>Email / Login ID</th><th>Role</th><th>Station</th><th>Reset Password</th></tr>
              </thead>
              <tbody>
                {users.map(u => (
                  <tr className="border-b border-borderBlue" key={u.id}>
                    <td className="px-3 py-2 font-black">{u.name}</td>
                    <td>{u.email}</td>
                    <td>{roleLabel(u.role)}</td>
                    <td>{u.station_name || "Central"}</td>
                    <td className="py-2">
                      <div className="flex gap-2">
                        <input type="password" className="w-36 rounded border border-borderBlue px-2 py-1" placeholder="New pass" value={resetPassword[u.id] || ""} onChange={e => setResetPassword({ ...resetPassword, [u.id]: e.target.value })} />
                        <button onClick={() => resetUserPassword(u.id)} className="rounded bg-danger px-3 py-1 text-xs font-black text-white hover:bg-red-700">Reset</button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Panel>
        <Panel title="Alert Gateway Log Terminal" icon="message-square-warning">
          <button onClick={fetchAll} className="mb-3 rounded border border-borderBlue px-3 py-2 text-xs font-black text-primary hover:bg-card">
            Refresh Logs
          </button>
          <div className="grid gap-4 lg:grid-cols-2">
            <LogBox title="Twilio SMS & OTP Gateway" logs={smsLogs.map(l => `${l.to_phone} - ${l.message}`)} />
            <LogBox title="Firebase Push Gateway" logs={pushLogs.map(l => `${l.title} - ${l.body}`)} />
          </div>
        </Panel>
      </div>
    </div>
  );
}

function AccountForm({ value, setValue, submit }) {
  return (
    <form onSubmit={submit} className="space-y-3">
      <Input label="Name" value={value.name} onChange={v => setValue({ ...value, name: v })} />
      <Input label="Login ID / Email" value={value.email} onChange={v => setValue({ ...value, email: v })} />
      <Input label="Temporary Password" type="password" value={value.password} onChange={v => setValue({ ...value, password: v })} />
      <Select label="Role" value={value.role} onChange={v => setValue({ ...value, role: v })} options={["police","hospital","superadmin"]} />
      <Input label="Phone" value={value.phone} onChange={v => setValue({ ...value, phone: v })} />
      <Input label="Station Name" value={value.station_name} onChange={v => setValue({ ...value, station_name: v })} />
      <Input label="Station Address" value={value.station_address} onChange={v => setValue({ ...value, station_address: v })} />
      <Input label="Jurisdiction Area" value={value.jurisdiction_area} onChange={v => setValue({ ...value, jurisdiction_area: v })} />
      <Submit label="Register Account" />
    </form>
  );
}

function LogBox({ title, logs }) {
  return (
    <div>
      <h3 className="mb-2 text-xs font-black uppercase text-primary">{title}</h3>
      <div className="h-64 overflow-y-auto rounded bg-slate-950 p-3 font-mono text-xs text-blue-100 shadow-inner">
        {logs.length ? logs.map((l, i) => <p className="mb-2 border-b border-slate-800 pb-2" key={i}>{l}</p>) : <p className="text-slate-500">No events logged yet.</p>}
      </div>
    </div>
  );
}

function Input({ label, value, onChange, type = "text", placeholder = "" }) {
  return (
    <label className="block">
      <span className="mb-1 block text-xs font-black uppercase text-primary">{label}</span>
      <input className="w-full rounded border border-borderBlue px-3 py-2 text-slate-900 focus:outline-none focus:ring-2 focus:ring-primaryLight" type={type} value={value} onChange={e => onChange(e.target.value)} placeholder={placeholder} />
    </label>
  );
}

function Select({ label, value, onChange, options }) {
  return (
    <label className="block">
      <span className="mb-1 block text-xs font-black uppercase text-primary">{label}</span>
      <select className="w-full rounded border border-borderBlue px-3 py-2 text-slate-900 focus:outline-none focus:ring-2 focus:ring-primaryLight" value={value} onChange={e => onChange(e.target.value)}>
        {options.map(o => <option key={o} value={o}>{o}</option>)}
      </select>
    </label>
  );
}

function Submit({ label }) {
  return (
    <button className="flex w-full items-center justify-center gap-2 rounded bg-primary px-4 py-3 text-sm font-black text-white hover:bg-primaryLight shadow transition">
      <Icon name="save" /> {label}
    </button>
  );
}

ReactDOM.createRoot(document.getElementById("root")).render(<App />);
