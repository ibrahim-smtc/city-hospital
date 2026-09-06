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

const completeModal     = document.getElementById('complete-modal');
const modalMeta         = document.getElementById('modal-meta');
const modalCloseBtn     = document.getElementById('modal-close-btn');
const modalCancelBtn    = document.getElementById('modal-cancel-btn');
const completeForm      = document.getElementById('complete-form');
const modalPatientEmail = document.getElementById('modal-patient-email');
const modalEmailError   = document.getElementById('modal-email-error');
const modalFormError    = document.getElementById('modal-form-error');
const modalSubmitBtn    = document.getElementById('modal-submit-btn');
const checkLabs         = document.getElementById('check-labs');
const checkImaging      = document.getElementById('check-imaging');
const checkMeds         = document.getElementById('check-meds');
const checkBilling      = document.getElementById('check-billing');
const checkFollowup     = document.getElementById('check-followup');

let currentCompleteApptId = null;

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
  let cls = 'pending';
  if (status === 'confirmed') cls = 'confirmed';
  else if (status === 'completed') cls = 'completed';
  return `<span class="status-badge ${cls}">${status}</span>`;
}

function getChecklistSummary(appt) {
  const parts = [];
  if (appt.labs_ordered) parts.push('Labs');
  if (appt.imaging_ordered) parts.push('Imaging');
  if (appt.meds_prescribed) parts.push('Meds prescribed');
  if (appt.billing_pending) parts.push('Billing pending');
  if (appt.followup_needed) parts.push('Follow-up needed');
  return parts.join(', ');
}

function renderStatusCell(appt) {
  const badge = statusBadge(appt.status);
  if (appt.status === 'completed') {
    const summary = getChecklistSummary(appt);
    return `
      <div class="status-cell-wrap">
        ${badge}
        ${summary ? `<span class="checklist-summary-text">${esc(summary)}</span>` : ''}
      </div>
    `;
  }
  return badge;
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
  const isPending   = appt.status === 'pending';
  const isConfirmed = appt.status === 'confirmed';

  let actionCell = '—';
  if (isPending) {
    actionCell = `
      <button
        class="btn btn-confirm"
        id="confirm-btn-${esc(appt.id)}"
        data-appt-id="${esc(appt.id)}"
        type="button"
      >Confirm</button>
      <div class="inline-error" id="err-${esc(appt.id)}"></div>`;
  } else if (isConfirmed) {
    actionCell = `
      <button
        class="btn btn-complete-trigger"
        id="complete-btn-${esc(appt.id)}"
        data-appt-id="${esc(appt.id)}"
        data-patient-name="${esc(appt.patient_name)}"
        data-patient-email="${esc(appt.patient_email || '')}"
        type="button"
      >Mark Consultation Complete</button>
      <div class="inline-error" id="err-comp-${esc(appt.id)}"></div>`;
  }

  return `
    <tr id="row-${esc(appt.id)}">
      <td><span class="appt-id">${esc(appt.id)}</span></td>
      <td>${esc(appt.patient_name)}</td>
      <td>${esc(appt.patient_phone)}</td>
      <td>${esc(appt.date)}</td>
      <td>${esc(appt.slot)}</td>
      <td>${esc(appt.reason) || '<span style="color:var(--text-muted)">—</span>'}</td>
      <td id="status-${esc(appt.id)}">${renderStatusCell(appt)}</td>
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
    attachCompleteListeners();
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
    // Update that row in place — status confirmed, action becomes Mark Consultation Complete
    statusEl.innerHTML = renderStatusCell({ status: 'confirmed' });
    actionEl.innerHTML = `
      <button
        class="btn btn-complete-trigger"
        id="complete-btn-${esc(apptId)}"
        data-appt-id="${esc(apptId)}"
        type="button"
      >Mark Consultation Complete</button>
      <div class="inline-error" id="err-comp-${esc(apptId)}"></div>`;
    attachCompleteListeners();
  } else {
    const detail = await res.json().catch(() => ({}));
    btn.disabled = false;
    btn.textContent = 'Confirm';
    errEl.textContent = detail.detail ?? 'Could not confirm. Please try again.';
    errEl.classList.add('visible');
  }
}

// ── Wire up complete consultation buttons & modal ──────────
function attachCompleteListeners() {
  appointmentsTbody.querySelectorAll('.btn-complete-trigger').forEach(btn => {
    btn.addEventListener('click', () => {
      openCompleteModal(btn.dataset.apptId, btn.dataset.patientName, btn.dataset.patientEmail);
    });
  });
}

function openCompleteModal(apptId, patientName, patientEmail) {
  currentCompleteApptId = apptId;
  if (modalMeta) {
    modalMeta.textContent = `${apptId} • Patient: ${patientName || 'Patient'}`;
  }

  // Reset form state
  if (modalPatientEmail) {
    modalPatientEmail.value = patientEmail || '';
    modalPatientEmail.classList.remove('error');
  }
  if (modalEmailError) {
    modalEmailError.textContent = '';
    modalEmailError.classList.remove('visible');
  }
  if (modalFormError) {
    modalFormError.textContent = '';
    modalFormError.classList.remove('visible');
  }

  if (checkLabs)     checkLabs.checked = false;
  if (checkImaging)  checkImaging.checked = false;
  if (checkMeds)     checkMeds.checked = false;
  if (checkBilling)  checkBilling.checked = false;
  if (checkFollowup) checkFollowup.checked = false;

  if (completeModal) {
    completeModal.style.setProperty('display', 'flex', 'important');
    completeModal.classList.add('visible');
    completeModal.setAttribute('aria-hidden', 'false');
  }
  setTimeout(() => {
    if (modalPatientEmail) modalPatientEmail.focus();
  }, 50);
}

function closeCompleteModal() {
  if (completeModal) {
    completeModal.style.setProperty('display', 'none', 'important');
    completeModal.classList.remove('visible');
    completeModal.setAttribute('aria-hidden', 'true');
  }
  currentCompleteApptId = null;
}

if (modalCloseBtn)  modalCloseBtn.addEventListener('click', closeCompleteModal);
if (modalCancelBtn) modalCancelBtn.addEventListener('click', closeCompleteModal);

if (completeModal) {
  completeModal.addEventListener('click', (e) => {
    if (e.target === completeModal) closeCompleteModal();
  });
}

document.addEventListener('keydown', (e) => {
  if (e.key === 'Escape' && completeModal && completeModal.classList.contains('visible')) {
    closeCompleteModal();
  }
});

if (modalPatientEmail) {
  modalPatientEmail.addEventListener('input', () => {
    if (modalPatientEmail.classList.contains('error')) {
      modalPatientEmail.classList.remove('error');
      modalEmailError.textContent = '';
      modalEmailError.classList.remove('visible');
    }
  });
}

if (completeForm) {
  completeForm.addEventListener('submit', async (e) => {
    e.preventDefault();

    const emailVal = (modalPatientEmail ? modalPatientEmail.value : '').trim();
    if (modalPatientEmail) modalPatientEmail.classList.remove('error');
    if (modalEmailError) {
      modalEmailError.textContent = '';
      modalEmailError.classList.remove('visible');
    }
    if (modalFormError) {
      modalFormError.textContent = '';
      modalFormError.classList.remove('visible');
    }

    // Optional check: only validate email format if doctor entered something
    if (emailVal) {
      const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
      if (!emailRegex.test(emailVal)) {
        if (modalEmailError) {
          modalEmailError.textContent = 'Please enter a valid email address';
          modalEmailError.classList.add('visible');
        }
        if (modalPatientEmail) {
          modalPatientEmail.classList.add('error');
          modalPatientEmail.focus();
        }
        return;
      }
    }

    const token = getToken();
    if (!token) {
      closeCompleteModal();
      showLogin();
      return;
    }

    const payload = {
      patient_email:   emailVal ? emailVal : null,
      labs_ordered:    checkLabs ? checkLabs.checked : false,
      imaging_ordered: checkImaging ? checkImaging.checked : false,
      meds_prescribed: checkMeds ? checkMeds.checked : false,
      billing_pending: checkBilling ? checkBilling.checked : false,
      followup_needed: checkFollowup ? checkFollowup.checked : false,
    };

    if (modalSubmitBtn) {
      modalSubmitBtn.disabled = true;
      modalSubmitBtn.classList.add('loading');
      const btnText = modalSubmitBtn.querySelector('.btn-text');
      if (btnText) btnText.textContent = 'Saving…';
    }

    function resetModalSubmitBtn() {
      if (modalSubmitBtn) {
        modalSubmitBtn.disabled = false;
        modalSubmitBtn.classList.remove('loading');
        const btnText = modalSubmitBtn.querySelector('.btn-text');
        if (btnText) btnText.textContent = 'Complete Consultation';
      }
    }

    const apptId = currentCompleteApptId;
    let res;
    try {
      res = await fetch(`/doctor/appointments/${encodeURIComponent(apptId)}/complete`, {
        method:  'POST',
        headers: {
          'Content-Type':  'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify(payload),
      });
    } catch {
      resetModalSubmitBtn();
      if (modalFormError) {
        modalFormError.textContent = 'Network error. Please try again.';
        modalFormError.classList.add('visible');
      }
      return;
    }

    resetModalSubmitBtn();

    if (!res.ok) {
      const errJson = await res.json().catch(() => ({}));
      if (modalFormError) {
        modalFormError.textContent = errJson.detail ?? 'Could not complete consultation. Please try again.';
        modalFormError.classList.add('visible');
      }
      return;
    }

    const resJson = await res.json().catch(() => ({}));
    const updatedData = resJson.data ?? payload;

    closeCompleteModal();

    // Update row in-place without page reload
    const statusEl = document.getElementById(`status-${apptId}`);
    const actionEl = document.getElementById(`action-${apptId}`);

    if (statusEl) {
      const summary = getChecklistSummary(updatedData);
      statusEl.innerHTML = `
        <div class="status-cell-wrap">
          ${statusBadge('completed')}
          ${summary ? `<span class="checklist-summary-text">${esc(summary)}</span>` : ''}
        </div>
      `;
    }
    if (actionEl) {
      actionEl.innerHTML = '—';
    }
  });
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
