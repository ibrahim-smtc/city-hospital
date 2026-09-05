/**
 * app.js — Doctor Portal
 *
 * Responsibilities:
 *  1. On load: check localStorage for a stored session token.
 *     If found, attempt GET /doctor/appointments.
 *     If 401, clear the token and show the login screen.
 *     If success, show the dashboard.
 *  2. Handle login form submission.
 *  3. Render the appointments table with real API data.
 *  4. Handle per-row "Confirm" button clicks.
 *  5. Handle "Log Out" (client-side token clear only).
 */

'use strict';

const TOKEN_KEY       = 'doctorSessionToken';
const DOCTOR_NAME_KEY = 'doctorName';
const DOCTOR_ID_KEY   = 'doctorId';

// ── Element references ─────────────────────────────────────
const loginScreen       = document.getElementById('login-screen');
const dashboardScreen   = document.getElementById('dashboard-screen');
const loginForm         = document.getElementById('login-form');
const loginBtn          = document.getElementById('login-btn');
const loginError        = document.getElementById('login-error');
const doctorNameDisplay = document.getElementById('doctor-name-display');
const dashSubtitle      = document.getElementById('dash-subtitle');
const appointmentsTbody = document.getElementById('appointments-tbody');
const logoutBtn         = document.getElementById('logout-btn');
const togglePwBtn       = document.getElementById('toggle-pw-btn');
const pwInput           = document.getElementById('password');

// ── Helpers ────────────────────────────────────────────────
function getToken()  { return localStorage.getItem(TOKEN_KEY); }

function saveSession(token, name, doctorId) {
  localStorage.setItem(TOKEN_KEY,       token);
  localStorage.setItem(DOCTOR_NAME_KEY, name);
  localStorage.setItem(DOCTOR_ID_KEY,   String(doctorId));
}

function clearSession() {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(DOCTOR_NAME_KEY);
  localStorage.removeItem(DOCTOR_ID_KEY);
}

function showLogin() {
  loginScreen.style.display      = '';
  dashboardScreen.classList.remove('visible');
  loginError.textContent = '';
  loginError.classList.remove('visible');
  loginForm.reset();
  if (pwInput) pwInput.type = 'password';
  if (togglePwBtn) {
    const eyeShow = togglePwBtn.querySelector('.eye-show');
    const eyeHide = togglePwBtn.querySelector('.eye-hide');
    if (eyeShow && eyeHide) {
      eyeShow.style.display = '';
      eyeHide.style.display = 'none';
    }
  }
}

function showDashboard() {
  loginScreen.style.display = 'none';
  dashboardScreen.classList.add('visible');
  doctorNameDisplay.textContent = localStorage.getItem(DOCTOR_NAME_KEY) || '';
}

function statusBadge(status) {
  const cls = status === 'confirmed' ? 'confirmed' : 'pending';
  return `<span class="status-badge ${cls}">${status}</span>`;
}

// Escape user-supplied text to avoid XSS (appointments come from the DB but
// it's good practice for a public-facing portal).
function esc(str) {
  return String(str ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

// ── Render one table row ────────────────────────────────────
function buildRow(appt) {
  const isPending = appt.status === 'pending';
  const actionCell = isPending
    ? `<button
         class="btn btn-confirm"
         id="confirm-btn-${esc(appt.id)}"
         data-appt-id="${esc(appt.id)}"
         type="button"
       >Confirm</button>
       <div class="inline-error" id="err-${esc(appt.id)}"></div>`
    : `—`;

  return `
    <tr id="row-${esc(appt.id)}">
      <td><span class="appt-id">${esc(appt.id)}</span></td>
      <td>${esc(appt.patient_name)}</td>
      <td>${esc(appt.patient_phone)}</td>
      <td>${esc(appt.date)}</td>
      <td>${esc(appt.slot)}</td>
      <td>${esc(appt.reason) || '<span style="color:var(--text-muted)">—</span>'}</td>
      <td id="status-${esc(appt.id)}">${statusBadge(appt.status)}</td>
      <td id="action-${esc(appt.id)}">${actionCell}</td>
    </tr>`;
}

// ── Fetch & render appointments ────────────────────────────
async function loadAppointments() {
  const token = getToken();
  if (!token) { showLogin(); return; }

  dashSubtitle.textContent = 'Loading appointments…';
  appointmentsTbody.innerHTML = `<tr><td colspan="8" class="loading-row"><span class="spinner"></span>&nbsp; Loading…</td></tr>`;

  let res;
  try {
    res = await fetch('/doctor/appointments', {
      headers: { 'Authorization': `Bearer ${token}` }
    });
  } catch {
    appointmentsTbody.innerHTML = `<tr><td colspan="8" class="empty-row">Network error — check your connection.</td></tr>`;
    dashSubtitle.textContent = '';
    return;
  }

  if (res.status === 401) {
    clearSession();
    showLogin();
    return;
  }

  const json = await res.json();
  const list = json.data ?? [];

  if (list.length === 0) {
    appointmentsTbody.innerHTML = `<tr><td colspan="8" class="empty-row">No appointments assigned to you yet.</td></tr>`;
    dashSubtitle.textContent = '0 appointments';
  } else {
    appointmentsTbody.innerHTML = list.map(buildRow).join('');
    dashSubtitle.textContent = `${list.length} appointment${list.length === 1 ? '' : 's'}`;
    attachConfirmListeners();
  }
}

// ── Wire up confirm buttons ────────────────────────────────
function attachConfirmListeners() {
  appointmentsTbody.querySelectorAll('.btn-confirm').forEach(btn => {
    btn.addEventListener('click', () => handleConfirm(btn.dataset.apptId));
  });
}

async function handleConfirm(apptId) {
  const token   = getToken();
  const btn     = document.getElementById(`confirm-btn-${apptId}`);
  const errEl   = document.getElementById(`err-${apptId}`);
  const statusEl = document.getElementById(`status-${apptId}`);
  const actionEl = document.getElementById(`action-${apptId}`);

  // Disable button, show loading state
  btn.disabled = true;
  btn.innerHTML = '<span class="spinner"></span>';
  errEl.classList.remove('visible');

  let res;
  try {
    res = await fetch(`/doctor/appointments/${encodeURIComponent(apptId)}/confirm`, {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${token}` }
    });
  } catch {
    btn.disabled = false;
    btn.textContent = 'Confirm';
    errEl.textContent = 'Network error. Please try again.';
    errEl.classList.add('visible');
    return;
  }

  if (res.ok) {
    // Update that row in place — no full page reload
    statusEl.innerHTML = statusBadge('confirmed');
    actionEl.innerHTML = '—';
  } else {
    const detail = await res.json().catch(() => ({}));
    btn.disabled = false;
    btn.textContent = 'Confirm';
    errEl.textContent = detail.detail ?? 'Could not confirm. Please try again.';
    errEl.classList.add('visible');
  }
}

// ── Password visibility toggle ──────────────────────────────
if (togglePwBtn && pwInput) {
  togglePwBtn.addEventListener('click', () => {
    const isPw = pwInput.type === 'password';
    pwInput.type = isPw ? 'text' : 'password';

    const eyeShow = togglePwBtn.querySelector('.eye-show');
    const eyeHide = togglePwBtn.querySelector('.eye-hide');
    if (eyeShow && eyeHide) {
      eyeShow.style.display = isPw ? 'none' : '';
      eyeHide.style.display = isPw ? '' : 'none';
    }
    togglePwBtn.setAttribute('aria-label', isPw ? 'Hide password' : 'Show password');
    togglePwBtn.setAttribute('title', isPw ? 'Hide password' : 'Show password');
  });
}

// ── Login form handler ─────────────────────────────────────
loginForm.addEventListener('submit', async (e) => {
  e.preventDefault();

  const email    = document.getElementById('email').value.trim();
  const password = document.getElementById('password').value;
  const btnText  = loginBtn.querySelector('.btn-text');

  loginError.textContent = '';
  loginError.classList.remove('visible');
  loginBtn.disabled = true;
  loginBtn.classList.add('loading');
  if (btnText) btnText.textContent = 'Signing in…';

  function resetLoginBtn() {
    loginBtn.disabled = false;
    loginBtn.classList.remove('loading');
    if (btnText) btnText.textContent = 'Sign In to Portal';
  }

  let res;
  try {
    res = await fetch('/doctor-login', {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify({ email, password }),
    });
  } catch {
    resetLoginBtn();
    loginError.textContent = 'Network error. Please check your connection.';
    loginError.classList.add('visible');
    return;
  }

  const json = await res.json().catch(() => ({}));

  if (!res.ok) {
    // Surface the backend's generic message — never add extra detail
    resetLoginBtn();
    loginError.textContent = json.detail ?? 'Invalid email or password';
    loginError.classList.add('visible');
    return;
  }

  // Success — store session and load dashboard
  saveSession(json.token, json.name, json.doctor_id);
  resetLoginBtn();
  showDashboard();
  loadAppointments();
});

// ── Logout handler ─────────────────────────────────────────
logoutBtn.addEventListener('click', () => {
  clearSession();
  showLogin();
});

// ── Boot ───────────────────────────────────────────────────
(async function boot() {
  const token = getToken();
  if (!token) {
    // No token — show login
    showLogin();
    return;
  }

  // Token exists — try to load appointments directly
  showDashboard();
  loadAppointments();
})();
