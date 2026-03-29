/* ── Config ─────────────────────────────────────────────────────────────── */
const API = 'http://127.0.0.1:8000/api';
let accessToken = localStorage.getItem('access') || '';
let currentUser  = JSON.parse(localStorage.getItem('user') || 'null');
let activePage   = '';

/* ── Helpers ─────────────────────────────────────────────────────────────── */
function toast(msg, type = 'inf') {
  const t = document.getElementById('toast');
  const el = document.createElement('div');
  el.className = `toast-item toast-${type}`;
  el.textContent = msg;
  t.appendChild(el);
  setTimeout(() => el.remove(), 3500);
}

async function api(method, path, body, auth = true) {
  const headers = { 'Content-Type': 'application/json' };
  if (auth && accessToken) headers['Authorization'] = `Bearer ${accessToken}`;
  const res = await fetch(API + path, {
    method, headers,
    body: body ? JSON.stringify(body) : undefined,
  });
  const data = res.status === 204 ? {} : await res.json();
  if (!res.ok) {
    const msg = Object.values(data).flat().join(' ') || `Erreur ${res.status}`;
    throw new Error(msg);
  }
  return data;
}

function fmt(dateStr) {
  if (!dateStr) return '—';
  const d = new Date(dateStr);
  return d.toLocaleDateString('fr-FR', { day: '2-digit', month: 'short', year: 'numeric' });
}
function fmtTime(t) { return t ? t.slice(0, 5) : ''; }

function badgeHtml(status) {
  const map = {
    pending: 'badge-pending', confirmed: 'badge-confirmed',
    cancelled: 'badge-cancelled', refused: 'badge-refused', completed: 'badge-completed',
  };
  const labels = {
    pending:'En attente', confirmed:'Confirmé', cancelled:'Annulé',
    refused:'Refusé', completed:'Terminé',
  };
  return `<span class="badge ${map[status]||''}">${labels[status]||status}</span>`;
}

function loader() { return `<div class="loader"><div class="spinner"></div> Chargement…</div>`; }
function empty(icon, msg) { return `<div class="empty"><div class="empty-icon">${icon}</div>${msg}</div>`; }

/* ── Auth ─────────────────────────────────────────────────────────────────── */
function switchTab(tab) {
  document.querySelectorAll('.tab').forEach((t, i) => t.classList.toggle('active', (i === 0) === (tab === 'login')));
  document.getElementById('login-form').classList.toggle('hidden', tab !== 'login');
  document.getElementById('register-form').classList.toggle('hidden', tab !== 'register');
}

document.querySelectorAll('input[name="role"]').forEach(r => {
  r.addEventListener('change', () => {
    document.getElementById('doctor-extra').style.display = r.value === 'doctor' ? '' : 'none';
  });
});
document.getElementById('doctor-extra').style.display = 'none';

async function login(e) {
  e.preventDefault();
  try {
    const data = await api('POST', '/auth/token/', {
      email: document.getElementById('l-email').value,
      password: document.getElementById('l-pass').value,
    }, false);
    accessToken = data.access;
    localStorage.setItem('access', data.access);
    localStorage.setItem('refresh', data.refresh);
    currentUser = { role: data.role, full_name: data.full_name, email: data.email };
    localStorage.setItem('user', JSON.stringify(currentUser));
    toast('Connexion réussie !', 'ok');
    initApp();
  } catch (err) { toast(err.message, 'err'); }
}

async function register(e) {
  e.preventDefault();
  const role = document.querySelector('input[name="role"]:checked').value;
  const body = {
    email: document.getElementById('r-email').value,
    first_name: document.getElementById('r-first').value,
    last_name: document.getElementById('r-last').value,
    password: document.getElementById('r-pass').value,
    password2: document.getElementById('r-pass').value,
  };
  if (role === 'doctor') {
    body.specialty = document.getElementById('r-spec').value;
    body.license_number = document.getElementById('r-lic').value || 'LIC-001';
    body.clinic_name = document.getElementById('r-clinic').value;
    body.city = document.getElementById('r-city').value;
  }
  try {
    await api('POST', `/auth/register/${role}/`, body, false);
    toast('Compte créé ! Connectez-vous.', 'ok');
    switchTab('login');
    document.getElementById('l-email').value = body.email;
  } catch (err) { toast(err.message, 'err'); }
}

function logout() {
  localStorage.clear(); accessToken = ''; currentUser = null;
  document.getElementById('auth-screen').classList.remove('hidden');
  document.getElementById('app-screen').classList.add('hidden');
}

/* ── App Bootstrap ───────────────────────────────────────────────────────── */
function initApp() {
  document.getElementById('auth-screen').classList.add('hidden');
  document.getElementById('app-screen').classList.remove('hidden');
  document.getElementById('user-badge').innerHTML =
    `<strong>${currentUser.full_name}</strong>${currentUser.email}`;
  buildNav();
}

function buildNav() {
  const nav = document.getElementById('sidebar-nav');
  const isDoc = currentUser.role === 'doctor';
  const items = isDoc
    ? [['schedule','📅','Mon Planning'],['requests','🔔','Demandes'],['slots','🕒','Mes Créneaux']]
    : [['search','🔍','Chercher un médecin'],['my-appts','📋','Mes Rendez-vous']];
  nav.innerHTML = items.map(([id, icon, label]) =>
    `<button class="nav-item" onclick="showPage('${id}')">${icon} ${label}</button>`
  ).join('');
  showPage(items[0][0]);
}

function showPage(id) {
  document.querySelectorAll('.page').forEach(p => p.classList.add('hidden'));
  document.querySelectorAll('.nav-item').forEach(b => b.classList.remove('active'));
  const page = document.getElementById(`page-${id}`);
  page.classList.remove('hidden');
  const btn = [...document.querySelectorAll('.nav-item')].find(b => b.textContent.includes(
    id === 'search' ? 'médecin' : id === 'my-appts' ? 'Mes Rendez' :
    id === 'schedule' ? 'Planning' : id === 'requests' ? 'Demandes' : 'Créneaux'
  ));
  if (btn) btn.classList.add('active');
  activePage = id;
  if (id === 'search')   renderSearch(page);
  if (id === 'my-appts') renderMyAppointments(page);
  if (id === 'schedule') renderSchedule(page);
  if (id === 'slots')    renderSlots(page);
  if (id === 'requests') renderRequests(page);
}

/* ── PATIENT: Search Doctors ─────────────────────────────────────────────── */
async function renderSearch(el) {
  el.innerHTML = `
    <div class="page-header"><h2>🔍 Chercher un médecin</h2></div>
    <div class="search-bar">
      <div class="field"><label>Spécialité</label>
        <select id="f-spec">
          <option value="">Toutes</option>
          <option value="cardiology">Cardiologie</option>
          <option value="dermatology">Dermatologie</option>
          <option value="general">Médecine Générale</option>
          <option value="neurology">Neurologie</option>
          <option value="pediatrics">Pédiatrie</option>
          <option value="dentistry">Dentisterie</option>
          <option value="ophthalmology">Ophtalmologie</option>
          <option value="orthopedics">Orthopédie</option>
          <option value="gynecology">Gynécologie</option>
          <option value="psychiatry">Psychiatrie</option>
          <option value="physiotherapy">Kinésithérapie</option>
        </select>
      </div>
      <div class="field"><label>Ville</label><input id="f-city" type="text" placeholder="Alger…"/></div>
      <div class="field"><label>Nom</label><input id="f-name" type="text" placeholder="Nom du médecin…"/></div>
      <button class="btn-primary" onclick="searchDoctors()">Rechercher</button>
    </div>
    <div id="doctors-result">${loader()}</div>`;
  searchDoctors();
}

async function searchDoctors() {
  const spec = document.getElementById('f-spec')?.value || '';
  const city = document.getElementById('f-city')?.value || '';
  const name = document.getElementById('f-name')?.value || '';
  let qs = [];
  if (spec) qs.push(`specialty=${spec}`);
  if (city) qs.push(`city=${city}`);
  if (name) qs.push(`search=${name}`);
  const res = document.getElementById('doctors-result');
  if (!res) return;
  res.innerHTML = loader();
  try {
    const data = await api('GET', `/doctors/list/?${qs.join('&')}`);
    const list = data.results || data;
    if (!list.length) { res.innerHTML = empty('👨‍⚕️', 'Aucun médecin trouvé'); return; }
    res.innerHTML = `<div class="doctors-grid">${list.map(doctorCard).join('')}</div>`;
  } catch (err) { res.innerHTML = empty('⚠️', err.message); }
}

function doctorCard(d) {
  const initials = `${d.full_name?.split(' ')[1]?.[0]||''}${d.full_name?.split(' ')[2]?.[0]||''}`;
  const slots = (d.next_available_slots || []).slice(0, 4);
  const slotsHtml = slots.length
    ? slots.map(s => `<span class="slot-chip" onclick="openBookModal(${d.id},${s.id},'${s.date}','${s.start_time}','${s.end_time}')">${fmtTime(s.start_time)}</span>`).join('')
    : '<span style="font-size:.78rem;color:var(--muted)">Aucun créneau</span>';
  return `<div class="doctor-card">
    <div class="doctor-card-top">
      <div class="doctor-avatar">${initials}</div>
      <div class="doctor-info">
        <h3>Dr. ${d.full_name}</h3>
        <div class="doctor-specialty">${d.specialty_display}</div>
        <div class="doctor-meta">📍 ${d.city||'—'} &nbsp;·&nbsp; ⭐ ${d.rating} (${d.total_reviews} avis) &nbsp;·&nbsp; ${d.experience_years} ans</div>
      </div>
    </div>
    <div class="slots-row">${slotsHtml}</div>
    ${slots.length ? `<button class="btn-secondary" onclick="openSlotsBrowser(${d.id},'${d.full_name}')">Voir tous les créneaux →</button>` : ''}
  </div>`;
}

/* ── Book Modal ──────────────────────────────────────────────────────────── */
function openBookModal(doctorId, slotId, date, start, end) {
  const overlay = document.createElement('div');
  overlay.className = 'modal-overlay';
  overlay.innerHTML = `<div class="modal">
    <h3>📋 Réserver un rendez-vous</h3>
    <p style="color:var(--muted);font-size:.85rem">📅 ${fmt(date)} · ⏰ ${fmtTime(start)} – ${fmtTime(end)}</p>
    <div class="field"><label>Motif de consultation</label>
      <textarea id="book-motif" rows="3" placeholder="Ex: Douleurs thoraciques, suivi diabète…"></textarea>
    </div>
    <div class="modal-actions">
      <button class="btn-secondary" onclick="this.closest('.modal-overlay').remove()">Annuler</button>
      <button class="btn-primary" onclick="bookAppointment(${doctorId},${slotId},this)">Confirmer</button>
    </div>
  </div>`;
  document.body.appendChild(overlay);
}

async function bookAppointment(doctorId, slotId, btn) {
  const motif = document.getElementById('book-motif').value;
  if (!motif.trim()) { toast('Veuillez préciser un motif', 'err'); return; }
  btn.disabled = true; btn.textContent = '…';
  try {
    await api('POST', '/appointments/', { doctor: doctorId, slot: slotId, motif });
    btn.closest('.modal-overlay').remove();
    toast('Rendez-vous réservé avec succès !', 'ok');
  } catch (err) { toast(err.message, 'err'); btn.disabled = false; btn.textContent = 'Confirmer'; }
}

async function openSlotsBrowser(doctorId, name) {
  const overlay = document.createElement('div');
  overlay.className = 'modal-overlay';
  overlay.innerHTML = `<div class="modal" style="width:500px">
    <h3>🕒 Créneaux de Dr. ${name}</h3>
    <div id="slot-browser-list">${loader()}</div>
    <div class="modal-actions"><button class="btn-secondary" onclick="this.closest('.modal-overlay').remove()">Fermer</button></div>
  </div>`;
  document.body.appendChild(overlay);
  try {
    const data = await api('GET', `/doctors/${doctorId}/slots/`);
    const list = data.results || data;
    const el = overlay.querySelector('#slot-browser-list');
    if (!list.length) { el.innerHTML = empty('🗓','Aucun créneau disponible'); return; }
    el.innerHTML = `<div class="slots-row" style="flex-wrap:wrap;gap:8px">${list.map(s =>
      `<span class="slot-chip" onclick="openBookModal(${doctorId},${s.id},'${s.date}','${s.start_time}','${s.end_time}');this.closest('.modal-overlay').remove()">
        📅 ${fmt(s.date)} ${fmtTime(s.start_time)}
      </span>`
    ).join('')}</div>`;
  } catch (err) { toast(err.message, 'err'); }
}

/* ── PATIENT: My Appointments ────────────────────────────────────────────── */
async function renderMyAppointments(el) {
  el.innerHTML = `
    <div class="page-header">
      <h2>📋 Mes Rendez-vous</h2>
      <div style="display:flex;gap:8px">
        <select id="appt-status-filter" onchange="renderMyAppointments(document.getElementById('page-my-appts'))">
          <option value="">Tous</option>
          <option value="pending">En attente</option>
          <option value="confirmed">Confirmés</option>
          <option value="cancelled">Annulés</option>
          <option value="completed">Terminés</option>
        </select>
      </div>
    </div>
    <div id="my-appts-list">${loader()}</div>`;
  const status = document.getElementById('appt-status-filter')?.value || '';
  try {
    const data = await api('GET', `/appointments/${status ? '?status=' + status : ''}`);
    const list = data.results || data;
    const res = document.getElementById('my-appts-list');
    if (!list.length) { res.innerHTML = empty('📭','Aucun rendez-vous'); return; }
    res.innerHTML = `<div class="appt-list">${list.map(apptCard).join('')}</div>`;
  } catch (err) { document.getElementById('my-appts-list').innerHTML = empty('⚠️', err.message); }
}

function apptCard(a) {
  const d = a.slot_date ? new Date(a.slot_date) : null;
  const canAct = !['cancelled','refused','completed'].includes(a.status);
  return `<div class="appt-card">
    <div class="appt-date-box">
      <div class="month">${d ? d.toLocaleDateString('fr-FR',{month:'short'}) : '—'}</div>
      <div class="day">${d ? d.getDate() : '—'}</div>
    </div>
    <div class="appt-info">
      <h4>${a.doctor_name || 'Médecin'} ${badgeHtml(a.status)}</h4>
      <p>${a.doctor_specialty||''} · ${fmtTime(a.slot_start_time)||'?'}–${fmtTime(a.slot_end_time)||'?'} · ${a.motif}</p>
      ${a.notes ? `<p style="color:var(--success);margin-top:4px">📝 ${a.notes}</p>` : ''}
      ${a.refusal_reason ? `<p style="color:var(--danger);margin-top:4px">❌ ${a.refusal_reason}</p>` : ''}
    </div>
    ${canAct ? `<div class="appt-actions">
      <button class="btn-danger" onclick="cancelAppt(${a.id})">Annuler</button>
      <button class="btn-warn" onclick="rescheduleAppt(${a.id},${a.doctor})">Reprogrammer</button>
    </div>` : ''}
  </div>`;
}

async function cancelAppt(id) {
  if (!confirm('Annuler ce rendez-vous ?')) return;
  try {
    await api('POST', `/appointments/${id}/cancel/`);
    toast('Rendez-vous annulé', 'ok');
    renderMyAppointments(document.getElementById('page-my-appts'));
  } catch (err) { toast(err.message, 'err'); }
}

async function rescheduleAppt(apptId, doctorId) {
  const overlay = document.createElement('div');
  overlay.className = 'modal-overlay';
  overlay.innerHTML = `<div class="modal"><h3>🔄 Reprogrammer</h3><div id="reschedule-slots">${loader()}</div>
    <div class="modal-actions"><button class="btn-secondary" onclick="this.closest('.modal-overlay').remove()">Fermer</button></div></div>`;
  document.body.appendChild(overlay);
  try {
    const data = await api('GET', `/doctors/${doctorId}/slots/`);
    const list = data.results || data;
    const el = overlay.querySelector('#reschedule-slots');
    if (!list.length) { el.innerHTML = empty('🗓','Aucun créneau disponible'); return; }
    el.innerHTML = `<div class="slots-row" style="flex-wrap:wrap">${list.map(s =>
      `<span class="slot-chip" onclick="doReschedule(${apptId},${s.id},this)">📅 ${fmt(s.date)} ${fmtTime(s.start_time)}</span>`
    ).join('')}</div>`;
  } catch (err) { toast(err.message, 'err'); }
}

async function doReschedule(apptId, slotId, btn) {
  btn.textContent = '…'; btn.style.opacity = '.5';
  try {
    await api('POST', `/appointments/${apptId}/reschedule/`, { slot_id: slotId });
    btn.closest('.modal-overlay').remove();
    toast('Rendez-vous reprogrammé !', 'ok');
    renderMyAppointments(document.getElementById('page-my-appts'));
  } catch (err) { toast(err.message, 'err'); btn.textContent = 'Choisir'; btn.style.opacity='1'; }
}

/* ── DOCTOR: Schedule ────────────────────────────────────────────────────── */
async function renderSchedule(el) {
  const today = new Date().toISOString().split('T')[0];
  el.innerHTML = `
    <div class="page-header">
      <h2>📅 Mon Planning</h2>
      <div style="display:flex;gap:10px;align-items:center">
        <input type="date" id="sched-date" value="${today}" onchange="loadSchedule()" style="background:var(--surface2);border:1px solid var(--border);border-radius:8px;padding:8px 12px;color:var(--text)"/>
        <button class="btn-primary" onclick="showPage('slots')">+ Créneau</button>
      </div>
    </div>
    <div class="schedule-grid">
      <div>
        <h3 style="margin-bottom:16px;font-size:.9rem;color:var(--muted);font-weight:600">PLANNING DU JOUR</h3>
        <div id="timeline-list">${loader()}</div>
      </div>
      <div>
        <h3 style="margin-bottom:16px;font-size:.9rem;color:var(--muted);font-weight:600">DEMANDES EN ATTENTE</h3>
        <div id="pending-sidebar">${loader()}</div>
      </div>
    </div>`;
  loadSchedule();
}

async function loadSchedule() {
  const date = document.getElementById('sched-date')?.value;
  const tl = document.getElementById('timeline-list');
  const ps = document.getElementById('pending-sidebar');
  if (!tl) return;
  try {
    const [dayData, pendingData] = await Promise.all([
      api('GET', `/doctor/appointments/${date ? '?date=' + date : ''}`),
      api('GET', '/doctor/appointments/?status=pending'),
    ]);
    const day = dayData.results || dayData;
    const pending = pendingData.results || pendingData;

    tl.innerHTML = day.length ? `<div class="timeline">${day.map(a => `
      <div class="timeline-item">
        <div class="timeline-time">${fmtTime(a.slot_start_time)}</div>
        <div class="timeline-body">
          <h4>${a.patient_name} ${badgeHtml(a.status)}</h4>
          <p>${a.motif} · ${a.appointment_type}</p>
        </div>
        ${a.status==='confirmed'?`<button class="btn-success" style="margin-left:auto" onclick="completeAppt(${a.id})">✓ Terminé</button>`:''}
      </div>`).join('')}</div>` : empty('📭','Aucun rendez-vous ce jour');

    ps.innerHTML = pending.length ? `<div class="pending-list">${pending.map(a => `
      <div class="pending-card">
        <h4>${a.patient_name} <span style="font-size:.75rem;color:var(--muted)">${fmt(a.slot_date)}</span></h4>
        <p>${a.motif}</p>
        <div class="pending-actions">
          <button class="btn-success" onclick="doctorAction(${a.id},'confirm')">✓ Confirmer</button>
          <button class="btn-danger" onclick="openRefuseModal(${a.id})">✕ Refuser</button>
        </div>
      </div>`).join('')}</div>` : empty('✅','Aucune demande en attente');
  } catch (err) { tl.innerHTML = empty('⚠️', err.message); }
}

async function completeAppt(id) {
  const notes = prompt('Notes de consultation (facultatif) :') || '';
  try {
    await api('POST', `/doctor/appointments/${id}/complete/`, { notes });
    toast('Marqué comme terminé', 'ok');
    loadSchedule();
  } catch (err) { toast(err.message, 'err'); }
}

async function doctorAction(id, action) {
  try {
    await api('POST', `/doctor/appointments/${id}/${action}/`);
    toast(action === 'confirm' ? 'Confirmé !' : 'Refusé', 'ok');
    loadSchedule();
    if (activePage === 'requests') renderRequests(document.getElementById('page-requests'));
  } catch (err) { toast(err.message, 'err'); }
}

function openRefuseModal(id) {
  const overlay = document.createElement('div');
  overlay.className = 'modal-overlay';
  overlay.innerHTML = `<div class="modal"><h3>✕ Refuser le rendez-vous</h3>
    <div class="field"><label>Raison (facultatif)</label><textarea id="refuse-reason" rows="3" placeholder="Ex: Indisponible ce jour…"></textarea></div>
    <div class="modal-actions">
      <button class="btn-secondary" onclick="this.closest('.modal-overlay').remove()">Annuler</button>
      <button class="btn-danger" onclick="doRefuse(${id},this)">Refuser</button>
    </div></div>`;
  document.body.appendChild(overlay);
}

async function doRefuse(id, btn) {
  const reason = document.getElementById('refuse-reason').value;
  btn.disabled = true;
  try {
    await api('POST', `/doctor/appointments/${id}/refuse/`, { reason });
    btn.closest('.modal-overlay').remove();
    toast('Rendez-vous refusé', 'ok');
    loadSchedule();
  } catch (err) { toast(err.message, 'err'); btn.disabled = false; }
}

/* ── DOCTOR: Requests ────────────────────────────────────────────────────── */
async function renderRequests(el) {
  el.innerHTML = `<div class="page-header"><h2>🔔 Toutes les Demandes</h2></div><div id="req-list">${loader()}</div>`;
  try {
    const data = await api('GET', '/doctor/appointments/');
    const list = data.results || data;
    const res = document.getElementById('req-list');
    if (!list.length) { res.innerHTML = empty('📭','Aucune demande'); return; }
    res.innerHTML = `<div class="appt-list">${list.map(a => `
      <div class="appt-card">
        <div class="appt-date-box">
          <div class="month">${a.slot_date ? new Date(a.slot_date).toLocaleDateString('fr-FR',{month:'short'}) : '—'}</div>
          <div class="day">${a.slot_date ? new Date(a.slot_date).getDate() : '—'}</div>
        </div>
        <div class="appt-info">
          <h4>${a.patient_name}, ${a.patient_age||'?'} ans ${badgeHtml(a.status)}</h4>
          <p>${a.motif} · ${fmtTime(a.slot_start_time)} – ${fmtTime(a.slot_end_time)}</p>
          ${a.refusal_reason ? `<p style="color:var(--danger);margin-top:4px">❌ ${a.refusal_reason}</p>` : ''}
        </div>
        ${a.status==='pending' ? `<div class="appt-actions">
          <button class="btn-success" onclick="doctorAction(${a.id},'confirm')">✓</button>
          <button class="btn-danger" onclick="openRefuseModal(${a.id})">✕</button>
        </div>` : ''}
        ${a.status==='confirmed' ? `<button class="btn-secondary" onclick="completeAppt(${a.id})">Terminé</button>` : ''}
      </div>`).join('')}</div>`;
  } catch (err) { document.getElementById('req-list').innerHTML = empty('⚠️', err.message); }
}

/* ── DOCTOR: Slots Manager ───────────────────────────────────────────────── */
async function renderSlots(el) {
  el.innerHTML = `
    <div class="page-header"><h2>🕒 Gérer mes Créneaux</h2></div>
    <div class="slots-manager">
      <div class="slot-form-card">
        <h3 style="font-size:1rem;font-weight:600">Nouveau Créneau</h3>
        <div class="field"><label>Date</label><input type="date" id="sl-date" /></div>
        <div class="field-row">
          <div class="field"><label>Début</label><input type="time" id="sl-start" /></div>
          <div class="field"><label>Fin</label><input type="time" id="sl-end" /></div>
        </div>
        <div class="field"><label>Type</label>
          <select id="sl-type">
            <option value="in_person">En cabinet</option>
            <option value="tele">Téléconsultation</option>
            <option value="home">Visite à domicile</option>
          </select>
        </div>
        <button class="btn-primary" onclick="addSlot()">Ajouter le créneau</button>
      </div>
      <div>
        <div style="display:flex;gap:10px;margin-bottom:16px">
          <input type="date" id="sl-filter-date" onchange="loadSlots()" style="background:var(--surface2);border:1px solid var(--border);border-radius:8px;padding:8px;color:var(--text)"/>
          <select id="sl-filter-booked" onchange="loadSlots()" style="background:var(--surface2);border:1px solid var(--border);border-radius:8px;padding:8px;color:var(--text)">
            <option value="">Tous</option><option value="false">Disponibles</option><option value="true">Réservés</option>
          </select>
        </div>
        <div class="slots-table-wrap"><div id="slots-table">${loader()}</div></div>
      </div>
    </div>`;
  loadSlots();
}

async function loadSlots() {
  const date = document.getElementById('sl-filter-date')?.value || '';
  const booked = document.getElementById('sl-filter-booked')?.value || '';
  let qs = [];
  if (date) qs.push(`date=${date}`);
  if (booked !== '') qs.push(`is_booked=${booked}`);
  const res = document.getElementById('slots-table');
  if (!res) return;
  try {
    const data = await api('GET', `/doctors/slots/?${qs.join('&')}`);
    const list = data.results || data;
    if (!list.length) { res.innerHTML = empty('🗓','Aucun créneau'); return; }
    res.innerHTML = `<table>
      <thead><tr><th>Date</th><th>Début</th><th>Fin</th><th>Type</th><th>Statut</th><th>Action</th></tr></thead>
      <tbody>${list.map(s => `<tr>
        <td>${fmt(s.date)}</td>
        <td>${fmtTime(s.start_time)}</td>
        <td>${fmtTime(s.end_time)}</td>
        <td>${s.slot_type_display}</td>
        <td>${s.is_booked ? '<span class="badge badge-confirmed">Réservé</span>' : '<span class="badge badge-pending">Libre</span>'}</td>
        <td>${!s.is_booked ? `<button class="btn-danger" onclick="deleteSlot(${s.id})">Supprimer</button>` : '—'}</td>
      </tr>`).join('')}</tbody>
    </table>`;
  } catch (err) { res.innerHTML = empty('⚠️', err.message); }
}

async function addSlot() {
  const date = document.getElementById('sl-date').value;
  const start = document.getElementById('sl-start').value;
  const end = document.getElementById('sl-end').value;
  const type = document.getElementById('sl-type').value;
  if (!date || !start || !end) { toast('Remplissez tous les champs', 'err'); return; }
  try {
    await api('POST', '/doctors/slots/', { date, start_time: start, end_time: end, slot_type: type });
    toast('Créneau ajouté !', 'ok');
    loadSlots();
  } catch (err) { toast(err.message, 'err'); }
}

async function deleteSlot(id) {
  if (!confirm('Supprimer ce créneau ?')) return;
  try {
    await api('DELETE', `/doctors/slots/${id}/`);
    toast('Créneau supprimé', 'ok');
    loadSlots();
  } catch (err) { toast(err.message, 'err'); }
}

/* ── Boot ─────────────────────────────────────────────────────────────────── */
if (currentUser && accessToken) initApp();
