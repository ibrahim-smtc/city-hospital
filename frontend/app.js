// --- Theme (noir / paper) ---
// The initial theme is resolved by the inline script in <head> before first paint;
// this only wires up the switch and keeps the choice sticky.
const THEME_KEY = 'ncmc-theme';
const THEME_COLORS = { dark: '#080808', light: '#f4f4f2' };

function applyTheme(theme) {
  document.documentElement.setAttribute('data-theme', theme);

  const toggle = document.getElementById('theme-toggle');
  const meta = document.getElementById('meta-theme-color');

  // The switch labels are static spans that crossfade in CSS — only the
  // assistive-tech state and the browser chrome colour need updating here.
  if (toggle) toggle.setAttribute('aria-checked', theme === 'light' ? 'true' : 'false');
  if (meta) meta.setAttribute('content', THEME_COLORS[theme]);
}

function toggleTheme() {
  const next = document.documentElement.getAttribute('data-theme') === 'light' ? 'dark' : 'light';
  applyTheme(next);
  try {
    localStorage.setItem(THEME_KEY, next);
  } catch (e) {
    // Storage unavailable (private mode) — the theme still applies for this session.
  }
}

// Sync the switch with whatever the pre-paint script decided.
applyTheme(document.documentElement.getAttribute('data-theme') || 'dark');
document.getElementById('theme-toggle').addEventListener('click', toggleTheme);

// Follow the OS only while the visitor has not made an explicit choice.
window.matchMedia('(prefers-color-scheme: light)').addEventListener('change', (e) => {
  let saved = null;
  try { saved = localStorage.getItem(THEME_KEY); } catch (err) { /* ignore */ }
  if (!saved) applyTheme(e.matches ? 'light' : 'dark');
});

// --- State ---
let state = {
  doctors: [],
  specialties: [],
  services: [],
  currentDoctor: null
};

// --- Navigation Tabs & Routing ---
document.querySelectorAll('.nav-link').forEach(link => {
  link.addEventListener('click', (e) => {
    e.preventDefault();
    // Update the URL hash instead of switching tabs directly
    window.location.hash = e.currentTarget.dataset.target;
  });
});

function switchTab(tabId) {
  // 1. Update active class on nav links
  document.querySelectorAll('.nav-link').forEach(l => l.classList.remove('active'));
  const activeLink = document.querySelector(`.nav-link[data-target="${tabId}"]`);
  if (activeLink) activeLink.classList.add('active');

  // 2. Show the correct view section
  document.querySelectorAll('.view-section').forEach(sec => sec.classList.remove('active'));
  const activeSection = document.getElementById(tabId);
  if (activeSection) activeSection.classList.add('active');
  
  // 2.5 Hide the hero image for non-home tabs
  const heroEl = document.querySelector('.hero');
  const heroStatsEl = document.querySelector('.hero-stats');
  if (heroEl) heroEl.style.display = (tabId === 'home') ? '' : 'none';
  if (heroStatsEl) heroStatsEl.style.display = (tabId === 'home') ? '' : 'none';
  
  // 3. Scroll to top when switching pages
  window.scrollTo(0, 0);
}

// Listen for browser Back/Forward navigation or manual hash changes
window.addEventListener('hashchange', () => {
  const tabId = window.location.hash.substring(1) || 'home';
  switchTab(tabId);
});

// Run once on initial load to catch any existing hash (e.g. if user refreshes the page on #status)
const initialTab = window.location.hash ? window.location.hash.substring(1) : 'home';
switchTab(initialTab);

// --- Fetch Data ---
async function init() {
  try {
    const [docRes, specRes, servRes] = await Promise.all([
      fetch('/doctors'), fetch('/specialties'), fetch('/services')
    ]);
    
    if(docRes.ok) state.doctors = (await docRes.json()).data;
    if(specRes.ok) state.specialties = (await specRes.json()).data;
    if(servRes.ok) state.services = (await servRes.json()).data;

    renderDoctors(state.doctors);
    renderSpecialties(state.specialties);
    renderServices(state.services);
    renderStats();

    // Setup Date picker min date
    document.getElementById('booking-date').min = new Date().toISOString().split('T')[0];

  } catch (err) {
    console.error("Failed to load data:", err);
  }
}

// --- Renderers ---
function renderStats() {
  const set = (id, value) => {
    const el = document.getElementById(id);
    if (el && value) el.textContent = value;
  };
  set('stat-doctors', state.doctors.length);
  set('stat-specialties', state.specialties.length);
  set('stat-services', state.services.length);
}

function renderDoctors(doctors) {
  const grid = document.getElementById('doctors-grid');
  grid.innerHTML = '';
  if (doctors.length === 0) {
    grid.innerHTML = `<div class="grid-empty">No doctors found.</div>`;
    return;
  }
  
  doctors.forEach(doc => {
    const card = document.createElement('div');
    card.className = 'card';

    // The card is the button here, so it has to answer to the keyboard too.
    card.tabIndex = 0;
    card.setAttribute('role', 'button');
    card.setAttribute('aria-label', `Book an appointment with ${doc.name}`);
    card.onclick = () => openBookingModal(doc.id);
    card.onkeydown = (e) => {
      if (e.key === 'Enter' || e.key === ' ') {
        e.preventDefault();
        openBookingModal(doc.id);
      }
    };

    const exp = doc.experience_years ? `${doc.experience_years} Yrs Exp.` : '';
    
    card.innerHTML = `
      <div class="card-subtitle">${doc.department}</div>
      <div class="card-title">${doc.name}</div>
      <div class="card-desc">${doc.designation}</div>
      <div class="card-footer">
        <span>${exp}</span>
        <span class="card-cta">Book →</span>
      </div>
    `;
    grid.appendChild(card);
  });
}

function renderSpecialties(specs) {
  const grid = document.getElementById('specialties-grid');
  grid.innerHTML = specs.map(s => `
    <div class="card card-static">
      <div class="card-title">${s.name}</div>
      <div class="card-desc" style="font-size: 14px;">${s.description || 'Advanced medical care.'}</div>
    </div>
  `).join('');
}

function renderServices(servs) {
  const grid = document.getElementById('services-grid');
  grid.innerHTML = servs.map(s => `
    <div class="card card-static">
      <div class="card-title">${s.name}</div>
      <div class="card-desc" style="font-size: 14px;">${s.description || 'Support clinic service.'}</div>
    </div>
  `).join('');
}

// --- Doctor Search ---
document.getElementById('doctor-search').addEventListener('input', (e) => {
  const q = e.target.value.toLowerCase();
  const filtered = state.doctors.filter(d => 
    d.department.toLowerCase().includes(q) || d.name.toLowerCase().includes(q)
  );
  renderDoctors(filtered);
});

// --- Modal Logic ---
let lastFocusedBeforeModal = null;

async function openBookingModal(doctorId) {
  // Fetch full details to get slots
  try {
    const res = await fetch(`/doctors/${doctorId}`);
    const data = await res.json();
    state.currentDoctor = data.data;
    
    document.getElementById('modal-doctor-name').textContent = state.currentDoctor.name;
    document.getElementById('modal-doctor-dept').textContent = state.currentDoctor.designation;
    document.getElementById('modal-doctor-id').value = state.currentDoctor.id;
    
    document.getElementById('available-days-hint').textContent = 
      `Doctor is usually available on: ${state.currentDoctor.available_days.join(', ')}`;
    
    // Reset form
    document.getElementById('booking-form').reset();
    document.getElementById('slot-container').innerHTML = '<div class="slot-empty">Select a date to see slots.</div>';
    document.getElementById('booking-error').textContent = '';
    
    // Show form, hide success
    document.getElementById('booking-step').style.display = 'block';
    document.getElementById('success-step').style.display = 'none';
    
    document.getElementById('booking-modal').classList.add('active');
    document.body.classList.add('modal-open');

    // Remember where focus came from so it can be handed back on close.
    lastFocusedBeforeModal = document.activeElement;
    const firstField = document.querySelector('#booking-form .form-control');
    if (firstField) firstField.focus();
  } catch (e) {
    alert("Failed to load doctor details.");
  }
}

function closeModal() {
  document.getElementById('booking-modal').classList.remove('active');
  document.body.classList.remove('modal-open');
  state.currentDoctor = null;

  // Hand focus back to whatever opened the dialog.
  if (lastFocusedBeforeModal && document.contains(lastFocusedBeforeModal)) {
    lastFocusedBeforeModal.focus();
  }
  lastFocusedBeforeModal = null;
}

// Click the backdrop (not the panel) to dismiss.
document.getElementById('booking-modal').addEventListener('click', (e) => {
  if (e.target === e.currentTarget) closeModal();
});

// Escape closes the modal if it's open.
document.addEventListener('keydown', (e) => {
  if (e.key !== 'Escape') return;
  const modal = document.getElementById('booking-modal');
  if (modal.classList.contains('active')) {
    closeModal();
  }
});

// --- Slot Selection ---
document.getElementById('booking-date').addEventListener('change', () => {
  if(!state.currentDoctor) return;
  const slots = state.currentDoctor.available_slots;
  const container = document.getElementById('slot-container');
  
  if(slots.length === 0) {
    container.innerHTML = '<div class="slot-empty warn">No slots available.</div>';
    return;
  }

  container.innerHTML = slots.map(slot => `
    <label class="slot-pill">
      <input type="radio" name="slot" value="${slot}" required onchange="selectSlot(this)">
      ${slot}
    </label>
  `).join('');
});

function selectSlot(radio) {
  document.querySelectorAll('.slot-pill').forEach(p => p.classList.remove('selected'));
  radio.parentElement.classList.add('selected');
}

// --- Submit Booking ---
document.getElementById('booking-form').addEventListener('submit', async (e) => {
  e.preventDefault();
  const form = e.target;
  const btn = document.getElementById('btn-submit');
  const errDiv = document.getElementById('booking-error');
  
  btn.disabled = true;
  btn.textContent = 'Booking...';
  errDiv.textContent = '';
  
  const payload = Object.fromEntries(new FormData(form));
  payload.doctor_id = parseInt(payload.doctor_id, 10);

  try {
    const res = await fetch('/appointments', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    
    const result = await res.json();
    
    if (!res.ok) {
      throw new Error(typeof result.detail === 'string' ? result.detail : result.detail?.message || "Booking failed");
    }

    // Show Success Step
    document.getElementById('booking-step').style.display = 'none';
    document.getElementById('success-step').style.display = 'block';
    document.getElementById('success-id').textContent = result.data.id;
    
  } catch (err) {
    errDiv.textContent = err.message;
  } finally {
    btn.disabled = false;
    btn.textContent = 'Confirm Booking';
  }
});

// --- Lookup Status ---
document.getElementById('lookup-form').addEventListener('submit', async (e) => {
  e.preventDefault();
  const input = document.getElementById('lookup-id').value.trim().toUpperCase();
  const resultDiv = document.getElementById('status-result');
  
  try {
    let url = `/appointments?phone=${encodeURIComponent(input)}`;
    if (input.startsWith('APPT-')) {
      url = `/appointments?appointment_id=${encodeURIComponent(input)}`;
    }

    const res = await fetch(url);
    if (!res.ok) throw new Error();
    
    const dataArr = (await res.json()).data;
    if (!dataArr || dataArr.length === 0) {
      throw new Error("No appointments found");
    }
    
    resultDiv.style.display = 'block';
    resultDiv.innerHTML = dataArr.map(data => {
      let badgeClass = 'badge-pending';
      if(data.status === 'confirmed') badgeClass = 'badge-confirmed';
      if(data.status === 'cancelled') badgeClass = 'badge-cancelled';
      
      return `
        <div class="status-details">
          <div class="status-row">
            <span class="status-key">ID</span>
            <span class="status-val">${data.id}</span>
          </div>
          <div class="status-row">
            <span class="status-key">Patient</span>
            <span class="status-val">${data.patient_name}</span>
          </div>
          <div class="status-row">
            <span class="status-key">Doctor</span>
            <span class="status-val">${data.doctor_name}</span>
          </div>
          <div class="status-row">
            <span class="status-key">Date & Time</span>
            <span class="status-val">${data.date} at ${data.slot}</span>
          </div>
          <div class="status-row" style="margin-top: 15px;">
            <span class="status-key">Status</span>
            <span class="badge ${badgeClass}">${data.status}</span>
          </div>
          <div class="status-actions">
            <button type="button" class="btn btn-danger-outline btn-sm" onclick="handleDeleteAppointment('${data.id}')">
              <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="margin-right: 5px; vertical-align: -2px;"><polyline points="3 6 5 6 21 6"></polyline><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path></svg>
              Cancel / Delete
            </button>
          </div>
        </div>
      `;
    }).join('');
  } catch (err) {
    resultDiv.style.display = 'block';
    resultDiv.innerHTML = `<div class="notice-error">No appointments found. Please check your ID or phone number.</div>`;
  }
});

// --- Delete Appointment Handler ---
window.handleDeleteAppointment = async function(appointmentId) {
  if (!confirm(`Are you sure you want to cancel and delete appointment ${appointmentId}?`)) {
    return;
  }

  try {
    const res = await fetch(`/appointments/${encodeURIComponent(appointmentId)}`, {
      method: 'DELETE'
    });

    const result = await res.json();

    if (!res.ok) {
      throw new Error(result.detail || 'Failed to delete appointment');
    }

    alert(`Appointment ${appointmentId} has been successfully deleted.`);

    // Refresh the status list
    const form = document.getElementById('lookup-form');
    if (form) {
      form.dispatchEvent(new Event('submit'));
    }
  } catch (err) {
    alert(`Error deleting appointment: ${err.message}`);
  }
};


// Initialize
init();

