/* =====================================================
   ShopWave Admin Dashboard JS — v2.0
   Real-time reasoning logs · Session management
   User creation & listing · No-order refund guard
   ===================================================== */

const API_BASE = (window.location.origin && window.location.origin !== 'null' && !window.location.origin.startsWith('file'))
  ? window.location.origin
  : 'http://localhost:8000';
const WS_BASE  = API_BASE.replace(/^http/, 'ws');

// ─── State ──────────────────────────────────────────────────────────────────
let adminWs       = null;
let sessions      = {};
let activeSession = null;
let logFilter     = 'all';
let autoScroll    = true;
let allUsers      = [];

let stats = { total: 0, approved: 0, denied: 0 };

// ─── DOM refs ────────────────────────────────────────────────────────────────
const $  = (id) => document.getElementById(id);
const sessionListEl  = $('session-list');
const logStreamEl    = $('log-stream');
const detailContent  = $('detail-content');

// ─── Init ────────────────────────────────────────────────────────────────────
window.addEventListener('DOMContentLoaded', () => {
  connectAdminWS();
  loadInitialSessions();
  loadUsers();
  setInterval(loadInitialSessions, 30000);
});

// ─── WebSocket ───────────────────────────────────────────────────────────────
function connectAdminWS() {
  adminWs = new WebSocket(`${WS_BASE}/ws/admin`);

  adminWs.onopen = () => setWsStatus(true);

  adminWs.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data);
      handleAdminMessage(data);
    } catch (e) { console.error('WS parse error', e); }
  };

  adminWs.onclose = () => {
    setWsStatus(false);
    setTimeout(connectAdminWS, 3000);
  };

  adminWs.onerror = () => setWsStatus(false);
}

function setWsStatus(connected) {
  const dot   = $('ws-dot');
  const label = $('ws-label');
  if (dot)   dot.classList.toggle('connected', connected);
  if (label) label.textContent = connected ? 'Live' : 'Reconnecting…';
}

// ─── Message Handler ──────────────────────────────────────────────────────────
function handleAdminMessage(data) {
  switch (data.type) {
    case 'init':
      data.sessions.forEach(s => upsertSession(s));
      renderSessionList();
      break;

    case 'session_update':
      upsertSession(data.session);
      renderSessionList();
      updateStats();
      break;

    case 'reasoning_log':
      if (!activeSession || data.session_id === activeSession) {
        appendLogEntry(data.log, data.session_id);
      }
      break;
  }
}

// ─── Sessions via REST ────────────────────────────────────────────────────────
async function loadInitialSessions() {
  try {
    const res  = await fetch(`${API_BASE}/api/admin/sessions`);
    const data = await res.json();
    data.forEach(s => upsertSession(s));
    renderSessionList();
    updateStats();
  } catch (err) {
    console.error('Failed to load sessions:', err);
  }
}

function upsertSession(session) {
  sessions[session.session_id] = { ...sessions[session.session_id], ...session };
}

// ─── Render Session List ──────────────────────────────────────────────────────
function renderSessionList() {
  if (!sessionListEl) return;

  const sorted = Object.values(sessions).sort(
    (a, b) => new Date(b.created_at) - new Date(a.created_at)
  );

  const countEl = $('session-count');
  if (countEl) countEl.textContent = sorted.length;

  if (sorted.length === 0) {
    sessionListEl.innerHTML = `
      <div class="empty-state">
        <div class="empty-icon">📭</div>
        <div>No active sessions yet.<br/>Start a chat to see sessions here.</div>
      </div>`;
    return;
  }

  sessionListEl.innerHTML = sorted.map(s => renderSessionItem(s)).join('');
}

function renderSessionItem(s) {
  const decision = s.refund_decision || 'pending';
  const isActive = s.session_id === activeSession;
  const shortId  = s.session_id.substring(0, 14) + '…';
  const email    = s.user_email || 'Unknown';
  const time     = formatRelTime(s.created_at);
  const msgs     = s.message_count || 0;

  return `
    <div class="session-item ${isActive ? 'active' : ''}"
         id="sess-${s.session_id}"
         onclick="selectSession('${s.session_id}')">
      <div class="session-id">${shortId}</div>
      <div class="session-email">${escHtml(email)}</div>
      <div class="session-meta">
        <div class="decision-dot ${decision}"></div>
        <span>${decision}</span>
        <span>·</span>
        <span>${msgs} msg${msgs !== 1 ? 's' : ''}</span>
        <span>·</span>
        <span>${time}</span>
      </div>
    </div>`;
}

function filterSessions(q) {
  document.querySelectorAll('.session-item').forEach(item => {
    const show = !q || item.textContent.toLowerCase().includes(q.toLowerCase());
    item.style.display = show ? '' : 'none';
  });
}

// ─── Select Session ───────────────────────────────────────────────────────────
async function selectSession(sessionId) {
  activeSession = sessionId;
  renderSessionList();
  clearLogs();

  try {
    const res  = await fetch(`${API_BASE}/api/admin/sessions/${sessionId}/logs`);
    const data = await res.json();

    // Render stored logs
    (data.reasoning_log || []).forEach(log => appendLogEntry(log, sessionId));

    // Load user profile if user_id present
    if (data.user_id) {
      loadUserProfile(data.user_id, data.refund_decision);
    } else {
      renderDetailEmpty();
    }
  } catch (err) {
    console.error('Failed to load session logs:', err);
    renderDetailEmpty();
  }
}

// ─── Log Rendering ────────────────────────────────────────────────────────────
function appendLogEntry(log, sessionId) {
  if (!logStreamEl) return;
  if (logFilter !== 'all' && log.level !== logFilter) return;

  const icons = { info: 'ℹ️', success: '✅', error: '❌', warning: '⚠️' };
  const icon  = icons[log.level] || '📋';
  const time  = formatLogTime(log.timestamp);
  const hasDetail = log.detail && Object.keys(log.detail).length > 0;
  const detailJson = hasDetail ? JSON.stringify(log.detail, null, 2) : '';

  const entry = document.createElement('div');
  entry.className = `log-entry ${log.level || 'info'}`;
  entry.innerHTML = `
    <div class="log-icon">${icon}</div>
    <div class="log-content">
      <div class="log-node">${escHtml(log.node || 'agent')}</div>
      <div class="log-message">${renderLogMessage(log.message)}</div>
      ${hasDetail ? `
        <button class="log-expand-btn" onclick="toggleLogDetail(this)">▶ Show details</button>
        <div class="log-detail">${escHtml(detailJson)}</div>
      ` : ''}
    </div>
    <div class="log-time">${time}</div>
  `;

  // Remove empty state
  const empty = logStreamEl.querySelector('.empty-state');
  if (empty) empty.remove();

  logStreamEl.appendChild(entry);

  // Update count
  const countEl = $('log-count');
  if (countEl) countEl.textContent = logStreamEl.querySelectorAll('.log-entry').length;

  if (autoScroll) {
    const body = $('log-panel-body');
    if (body) body.scrollTop = body.scrollHeight;
  }
}

function toggleLogDetail(btn) {
  const entry = btn.closest('.log-entry');
  const expanded = entry.classList.toggle('expanded');
  btn.textContent = expanded ? '▼ Hide details' : '▶ Show details';
}

function renderLogMessage(msg) {
  if (!msg) return '';
  return msg
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    .replace(/`(.*?)`/g, '<code>$1</code>');
}

function clearLogs() {
  if (!logStreamEl) return;
  logStreamEl.innerHTML = `
    <div class="empty-state">
      <div class="empty-icon">🧠</div>
      <div>Select a session to view reasoning logs</div>
    </div>`;
  const countEl = $('log-count');
  if (countEl) countEl.textContent = '0';
}

// ─── Filter ───────────────────────────────────────────────────────────────────
function setLogFilter(filter) {
  logFilter = filter;
  document.querySelectorAll('.log-filter-btn').forEach(btn => {
    btn.classList.toggle('active', btn.dataset.filter === filter);
  });
  if (activeSession) selectSession(activeSession);
}

// ─── User Profile (detail panel) ─────────────────────────────────────────────
async function loadUserProfile(userId, decision) {
  try {
    const res  = await fetch(`${API_BASE}/api/admin/users/${userId}`);
    if (!res.ok) { renderDetailEmpty(); return; }
    const user = await res.json();
    renderUserDetail(user, decision);
  } catch {
    renderDetailEmpty();
  }
}

function renderUserDetail(user, decision) {
  if (!detailContent) return;

  const initials = (user.email || '?').split('@')[0].slice(0, 2).toUpperCase();
  const hasOrders = user.order_count > 0;

  // Decision badge
  let decisionBadge = '';
  if (decision === 'refund_initiated') {
    decisionBadge = `<span class="badge badge-refund_initiated">✅ Refund Initiated</span>`;
  } else if (decision === 'denied') {
    decisionBadge = `<span class="badge badge-denied">❌ Denied</span>`;
  } else {
    decisionBadge = `<span class="badge badge-pending">⏳ Pending</span>`;
  }

  // No-order warning
  const noOrderWarning = !hasOrders ? `
    <div class="no-orders-warning">
      <div class="no-orders-warning-icon">⚠️</div>
      <div class="no-orders-warning-text">
        <strong>No Orders Found</strong>
        This user has no orders. Any refund request will be automatically declined by the agent.
      </div>
    </div>` : '';

  // Orders HTML
  const ordersHtml = (user.orders || []).map(o => {
    const statusClass =
      o.return_status === 'Refund Initiated' ? 'refunded' :
      o.return_status === 'Returned'         ? 'returned' : 'pending';
    const statusLabel =
      o.return_status === 'Refund Initiated' ? '💸 Refunded' :
      o.return_status === 'Returned'         ? '✅ Returned' : '📦 Active';
    const total = ((o.product_price * o.order_quantity) - o.discount_applied).toFixed(2);
    return `
      <div class="order-card">
        <div class="order-top">
          <span class="order-id-tag">${o.order_id}</span>
          <span class="order-status ${statusClass}">${statusLabel}</span>
        </div>
        <div class="order-mid">
          <span class="order-cat">${o.product_category}</span>
          <span class="order-amt">$${total}</span>
        </div>
        <div style="display:flex;justify-content:space-between">
          <span class="order-date">📅 ${o.order_date}</span>
          <span class="order-pay">💳 ${o.payment_method}</span>
        </div>
      </div>`;
  }).join('');

  detailContent.innerHTML = `
    <div class="customer-profile">
      <div class="profile-avatar">${initials}</div>
      <div class="profile-name">${escHtml(user.email.split('@')[0])}</div>
      <div class="profile-email">${escHtml(user.email)}</div>
      <div class="profile-id">${user.user_id}</div>
      <div class="profile-badges">
        ${decisionBadge}
        <span class="badge ${hasOrders ? 'badge-refund_initiated' : 'badge-no-orders'}">
          ${hasOrders ? `📦 ${user.order_count} order${user.order_count !== 1 ? 's' : ''}` : '⚠️ No orders'}
        </span>
      </div>
      <div class="profile-stats">
        <div class="stat-box">
          <div class="stat-box-val">${user.user_age || '—'}</div>
          <div class="stat-box-key">Age</div>
        </div>
        <div class="stat-box">
          <div class="stat-box-val">${user.user_gender || '—'}</div>
          <div class="stat-box-key">Gender</div>
        </div>
        <div class="stat-box" style="grid-column:span 2">
          <div class="stat-box-val" style="font-size:0.85rem">${user.user_location || '—'}</div>
          <div class="stat-box-key">Location</div>
        </div>
      </div>
    </div>
    ${noOrderWarning}
    <div class="orders-section">
      <div class="orders-title">📦 Orders (${user.order_count})</div>
      ${hasOrders ? ordersHtml : '<div style="color:var(--text-muted);font-size:0.8rem;padding:8px 0">No orders on record for this account.</div>'}
    </div>
  `;
}

function renderDetailEmpty() {
  if (!detailContent) return;
  detailContent.innerHTML = `
    <div class="empty-state">
      <div class="empty-icon">👤</div>
      <div>Select a session to view<br/>customer details here.</div>
    </div>`;
}

// ─── Stats ────────────────────────────────────────────────────────────────────
function updateStats() {
  stats = { total: 0, approved: 0, denied: 0 };
  Object.values(sessions).forEach(s => {
    stats.total++;
    const d = s.refund_decision;
    if (d === 'refund_initiated' || d === 'approved') stats.approved++;
    else if (d === 'denied') stats.denied++;
  });

  const t = $('stat-total');
  const a = $('stat-approved');
  const d = $('stat-denied');
  if (t) t.textContent = stats.total;
  if (a) a.textContent = stats.approved;
  if (d) d.textContent = stats.denied;
}

// ─── Users ────────────────────────────────────────────────────────────────────
async function loadUsers() {
  try {
    const res  = await fetch(`${API_BASE}/api/admin/users`);
    allUsers   = await res.json();
    const el   = $('stat-users');
    if (el) el.textContent = allUsers.length;
  } catch {
    allUsers = [];
  }
}

// ─── User List Modal ──────────────────────────────────────────────────────────
function openUserList() {
  const modal = $('user-list-modal');
  if (!modal) return;
  modal.classList.add('open');
  renderUserList(allUsers);
  // Refresh from server
  loadUsers().then(() => renderUserList(allUsers));
}

function closeUserList() {
  const modal = $('user-list-modal');
  if (modal) modal.classList.remove('open');
}

function filterUserList(q) {
  const filtered = allUsers.filter(u =>
    !q ||
    u.email.toLowerCase().includes(q.toLowerCase()) ||
    u.user_id.toLowerCase().includes(q.toLowerCase())
  );
  renderUserList(filtered);
}

function renderUserList(users) {
  const el = $('user-list-items');
  if (!el) return;

  if (!users.length) {
    el.innerHTML = `<div class="empty-state"><div class="empty-icon">👥</div><div>No users found.</div></div>`;
    return;
  }

  el.innerHTML = users.map(u => {
    const initials = u.email.split('@')[0].slice(0, 2).toUpperCase();
    const name     = u.email.split('@')[0].replace(/\./g, ' ');
    const hasOrders = u.has_orders;
    return `
      <div class="user-list-item" onclick="selectUserFromList('${u.user_id}')">
        <div class="user-avatar">${initials}</div>
        <div class="user-details">
          <div class="user-name">${escHtml(name)}</div>
          <div class="user-email">${escHtml(u.email)}</div>
        </div>
        <div class="user-meta">
          <span class="order-badge ${hasOrders ? 'has-orders' : 'no-orders'}">
            ${hasOrders ? `📦 ${u.order_count} order${u.order_count !== 1 ? 's' : ''}` : '⚠️ No orders'}
          </span>
          <span class="user-id-tag">${u.user_id}</span>
        </div>
      </div>`;
  }).join('');
}

function selectUserFromList(userId) {
  closeUserList();
  loadUserProfile(userId, null);
}

// ─── Create User Modal ────────────────────────────────────────────────────────
function openCreateUserModal() {
  const modal = $('create-user-modal');
  if (modal) modal.classList.add('open');

  // Reset form
  const form = $('create-user-form');
  if (form) form.reset();
  const err = $('cu-error');
  const suc = $('cu-success');
  if (err) err.style.display = 'none';
  if (suc) suc.style.display = 'none';
}

function closeCreateUserModal() {
  const modal = $('create-user-modal');
  if (modal) modal.classList.remove('open');
}

async function submitCreateUser(event) {
  event.preventDefault();

  const email    = $('cu-email')?.value.trim();
  const password = $('cu-password')?.value;
  const age      = parseInt($('cu-age')?.value) || null;
  const gender   = $('cu-gender')?.value || null;
  const location = $('cu-location')?.value.trim() || null;

  const errEl = $('cu-error');
  const sucEl = $('cu-success');
  const btn   = $('cu-submit-btn');

  if (errEl) errEl.style.display = 'none';
  if (sucEl) sucEl.style.display = 'none';
  if (btn)   { btn.disabled = true; btn.textContent = 'Creating…'; }

  try {
    const resp = await fetch(`${API_BASE}/api/admin/users`, {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify({
        email,
        password,
        user_age:      age,
        user_gender:   gender,
        user_location: location,
      }),
    });

    const data = await resp.json();

    if (!resp.ok) {
      if (errEl) {
        errEl.textContent = data.detail || 'Failed to create user.';
        errEl.style.display = 'block';
      }
      return;
    }

    // Success
    if (sucEl) {
      sucEl.textContent = `✅ User ${email} created with ID ${data.user_id}. They have no orders — refund requests will be declined.`;
      sucEl.style.display = 'block';
    }

    // Refresh user list & stats
    await loadUsers();

    // Reset form fields (keep modal open to show success)
    $('cu-email').value    = '';
    $('cu-password').value = '';
    $('cu-age').value      = '';
    $('cu-gender').value   = '';
    $('cu-location').value = '';

    // Add to user list if open
    renderUserList(allUsers);

  } catch (err) {
    if (errEl) {
      errEl.textContent = 'Connection error. Is the server running?';
      errEl.style.display = 'block';
    }
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.innerHTML = `<svg width="13" height="13" viewBox="0 0 24 24" fill="currentColor"><path d="M15 12c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm-9-2V7H4v3H1v2h3v3h2v-3h3v-2H6zm9 4c-2.67 0-8 1.34-8 4v2h16v-2c0-2.66-5.33-4-8-4z"/></svg> Create User`;
    }
  }
}

// Close modals on overlay click
document.addEventListener('click', (e) => {
  if (e.target.classList.contains('modal-overlay')) {
    closeUserList();
    closeCreateUserModal();
  }
});

// Escape key closes modals
document.addEventListener('keydown', (e) => {
  if (e.key === 'Escape') {
    closeUserList();
    closeCreateUserModal();
  }
});

// ─── Helpers ──────────────────────────────────────────────────────────────────
function formatRelTime(iso) {
  const diff = Date.now() - new Date(iso).getTime();
  if (diff < 60000)    return 'just now';
  if (diff < 3600000)  return Math.floor(diff / 60000) + 'm ago';
  if (diff < 86400000) return Math.floor(diff / 3600000) + 'h ago';
  return new Date(iso).toLocaleDateString();
}

function formatLogTime(iso) {
  try {
    return new Date(iso).toLocaleTimeString([], {
      hour: '2-digit', minute: '2-digit', second: '2-digit',
    });
  } catch { return '--:--:--'; }
}

function escHtml(str) {
  if (!str) return '';
  return str
    .replace(/&/g, '&amp;').replace(/</g, '&lt;')
    .replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}
