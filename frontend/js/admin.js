/* =====================================================
   ShopWave Admin Dashboard JS — Realtime Reasoning Logs
   ===================================================== */

const API_BASE = 'http://localhost:8000';
const WS_BASE  = 'ws://localhost:8000';

// ─── State ──────────────────────────────────────────────
let adminWs       = null;
let sessions      = {};
let activeSession = null;
let logFilter     = 'all';
let autoScroll    = true;

// Stats counters
let stats = { total: 0, approved: 0, denied: 0, escalated: 0 };

// ─── DOM Refs ────────────────────────────────────────────
const sessionListEl   = document.getElementById('session-list');
const logStreamEl     = document.getElementById('log-stream');
const detailPanelEl   = document.getElementById('detail-content');
const wsDotEl         = document.getElementById('ws-dot');
const wsLabelEl       = document.getElementById('ws-label');
const logCountEl      = document.getElementById('log-count');
const sessionCountEl  = document.getElementById('session-count');

// Stat displays
const statTotal     = document.getElementById('stat-total');
const statApproved  = document.getElementById('stat-approved');
const statDenied    = document.getElementById('stat-denied');
const statEscalated = document.getElementById('stat-escalated');

// ─── Init ────────────────────────────────────────────────
window.addEventListener('DOMContentLoaded', () => {
  connectAdminWS();
  loadInitialSessions();
  setInterval(loadInitialSessions, 30000); // refresh every 30s
});

// ─── WebSocket ───────────────────────────────────────────
function connectAdminWS() {
  adminWs = new WebSocket(`${WS_BASE}/ws/admin`);

  adminWs.onopen = () => {
    setWsStatus(true);
  };

  adminWs.onmessage = (event) => {
    const data = JSON.parse(event.data);
    handleAdminMessage(data);
  };

  adminWs.onclose = () => {
    setWsStatus(false);
    setTimeout(connectAdminWS, 3000);
  };

  adminWs.onerror = () => setWsStatus(false);
}

function setWsStatus(connected) {
  wsDotEl.classList.toggle('connected', connected);
  wsLabelEl.textContent = connected ? 'Live' : 'Reconnecting…';
}

// ─── Message Handler ─────────────────────────────────────
function handleAdminMessage(data) {
  switch (data.type) {
    case 'init':
      data.sessions.forEach(s => upsertSession(s));
      renderSessionList();
      break;

    case 'session_update':
      upsertSession(data.session);
      renderSessionList();
      updateStats(data.session);
      break;

    case 'reasoning_log':
      // Always add to log stream if it matches the active session or no active session
      if (!activeSession || data.session_id === activeSession) {
        appendLogEntry(data.log, data.session_id);
      }
      break;
  }
}

// ─── Load sessions via REST ───────────────────────────────
async function loadInitialSessions() {
  try {
    const res = await fetch(`${API_BASE}/api/admin/sessions`);
    const data = await res.json();
    data.forEach(s => upsertSession(s));
    renderSessionList();
    updateAllStats();
  } catch (err) {
    console.error('Failed to load sessions:', err);
  }
}

// ─── Session Management ───────────────────────────────────
function upsertSession(session) {
  sessions[session.session_id] = { ...sessions[session.session_id], ...session };
}

function renderSessionList() {
  if (!sessionListEl) return;
  const sorted = Object.values(sessions).sort(
    (a, b) => new Date(b.created_at) - new Date(a.created_at)
  );

  if (sessionCountEl) sessionCountEl.textContent = sorted.length;

  sessionListEl.innerHTML = sorted.length === 0
    ? '<div class="log-empty"><div class="icon">📭</div><div>No active sessions yet</div></div>'
    : sorted.map(s => renderSessionItem(s)).join('');
}

function renderSessionItem(s) {
  const decision = s.refund_decision || 'pending';
  const time = formatRelTime(s.created_at);
  const isActive = s.session_id === activeSession;
  const shortId = s.session_id.substring(0, 12) + '…';
  const custLabel = s.customer_id ? s.customer_id : 'Unknown customer';

  return `
    <div class="session-item ${isActive ? 'active' : ''}"
         onclick="selectSession('${s.session_id}')"
         id="sess-${s.session_id}">
      <div class="session-id">${shortId}</div>
      <div class="session-customer">${custLabel}</div>
      <div class="session-meta">
        <div class="decision-dot ${decision}"></div>
        <span>${decision}</span>
        <span>·</span>
        <span>${s.message_count || 0} msgs</span>
        <span>·</span>
        <span>${time}</span>
      </div>
    </div>
  `;
}

async function selectSession(sessionId) {
  activeSession = sessionId;
  renderSessionList();
  clearLogs();

  // Load session logs
  try {
    const res = await fetch(`${API_BASE}/api/admin/sessions/${sessionId}/logs`);
    const data = await res.json();

    // Render existing logs
    (data.reasoning_log || []).forEach(log => appendLogEntry(log, sessionId));

    // Load customer detail if available
    if (data.customer_id) {
      loadCustomerDetail(data.customer_id, data.refund_decision);
    } else {
      renderDetailEmpty();
    }
  } catch (err) {
    console.error('Failed to load session logs:', err);
  }
}

// ─── Log Rendering ────────────────────────────────────────
function appendLogEntry(log, sessionId) {
  if (!logStreamEl) return;

  // Apply filter
  if (logFilter !== 'all' && log.level !== logFilter) return;

  const icons = { info: 'ℹ️', success: '✅', error: '❌', warning: '⚠️' };
  const time = formatLogTime(log.timestamp);
  const hasDetail = log.detail && Object.keys(log.detail).length > 0;
  const detailJson = hasDetail ? JSON.stringify(log.detail, null, 2) : '';

  const entry = document.createElement('div');
  entry.className = `log-entry ${log.level}`;
  entry.innerHTML = `
    <div class="log-icon">${icons[log.level] || '📋'}</div>
    <div class="log-content">
      <div class="log-node">${log.node}</div>
      <div class="log-message">${renderLogMessage(log.message)}</div>
      ${hasDetail ? `
        <button class="log-expand-btn" onclick="toggleLogDetail(this)">
          ▶ Show details
        </button>
        <div class="log-detail">${escapeHtml(detailJson)}</div>
      ` : ''}
    </div>
    <div class="log-time">${time}</div>
  `;

  // Remove empty state if present
  const empty = logStreamEl.querySelector('.log-empty');
  if (empty) empty.remove();

  logStreamEl.appendChild(entry);

  // Update count
  const count = logStreamEl.querySelectorAll('.log-entry').length;
  if (logCountEl) logCountEl.textContent = count;

  if (autoScroll) {
    const logPanel = document.getElementById('log-panel-body');
    if (logPanel) logPanel.scrollTop = logPanel.scrollHeight;
  }
}

function toggleLogDetail(btn) {
  const entry = btn.closest('.log-entry');
  const expanded = entry.classList.toggle('expanded');
  btn.textContent = expanded ? '▼ Hide details' : '▶ Show details';
}

function renderLogMessage(msg) {
  return msg
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    .replace(/`(.*?)`/g, '<code>$1</code>');
}

function clearLogs() {
  if (!logStreamEl) return;
  logStreamEl.innerHTML = `
    <div class="log-empty">
      <div class="icon">🧠</div>
      <div>Select a session to view reasoning logs</div>
    </div>
  `;
  if (logCountEl) logCountEl.textContent = '0';
}

// ─── Filter ───────────────────────────────────────────────
function setLogFilter(filter) {
  logFilter = filter;
  document.querySelectorAll('.log-filter-btn').forEach(btn => {
    btn.classList.toggle('active', btn.dataset.filter === filter);
  });
  // Re-render current session logs
  if (activeSession) selectSession(activeSession);
}

// ─── Customer Detail ──────────────────────────────────────
async function loadCustomerDetail(customerId, decision) {
  try {
    const res = await fetch(`${API_BASE}/api/admin/customers/${customerId}`);
    const customer = await res.json();
    renderCustomerDetail(customer, decision);
  } catch (err) {
    renderDetailEmpty();
  }
}

function renderCustomerDetail(customer, decision) {
  if (!detailPanelEl) return;
  const initials = customer.name.split(' ').map(n => n[0]).join('');
  const tierClass = `tier-${customer.tier}`;
  const decisionBadge = decision
    ? `<span class="badge badge-${decision}">${decision}</span>`
    : '<span class="badge badge-pending">Pending</span>';

  const ordersHtml = Object.values(customer.orders || {}).map(o => `
    <div class="order-item">
      <div class="order-id-tag">${o.order_id}</div>
      <div class="flex items-center gap-2">
        <span class="order-amount">$${o.total.toFixed(2)}</span>
        <span class="order-date">${o.date}</span>
      </div>
      <div style="font-size:0.72rem;color:var(--text-muted)">
        ${o.items.map(i => i.name).join(', ')}
      </div>
    </div>
  `).join('');

  detailPanelEl.innerHTML = `
    <div class="customer-profile">
      <div class="profile-avatar">${initials}</div>
      <div class="profile-name">${customer.name}</div>
      <div class="profile-email">${customer.email}</div>
      <div class="flex items-center gap-2">
        <span class="tier-badge ${tierClass}">⭐ ${customer.tier}</span>
        ${decisionBadge}
      </div>
      <div class="profile-stats">
        <div class="stat-box">
          <div class="sv" style="color:var(--accent)">${customer.total_refunds_this_year}/3</div>
          <div class="sk">Refunds</div>
        </div>
        <div class="stat-box">
          <div class="sv">$${customer.total_refund_amount_this_year.toFixed(0)}</div>
          <div class="sk">Total</div>
        </div>
        <div class="stat-box">
          <div class="sv">${Math.round(customer.account_age_days / 30)}mo</div>
          <div class="sk">Account Age</div>
        </div>
        <div class="stat-box">
          <div class="sv" style="color:var(--warning)">${customer.loyalty_points.toLocaleString()}</div>
          <div class="sk">Points</div>
        </div>
      </div>
    </div>
    <div class="panel-header" style="padding:10px 16px">
      <div class="panel-title"><span class="icon">📦</span> Orders</div>
    </div>
    ${ordersHtml || '<div class="log-empty" style="padding:20px">No orders found</div>'}
  `;
}

function renderDetailEmpty() {
  if (!detailPanelEl) return;
  detailPanelEl.innerHTML = `
    <div class="detail-empty">
      <div class="icon">👤</div>
      <div>Select a session to view<br>customer details</div>
    </div>
  `;
}

// ─── Stats ────────────────────────────────────────────────
function updateStats(session) {
  if (session.refund_decision) {
    // Avoid double counting
    if (!sessions[session.session_id]?.counted) {
      sessions[session.session_id] = { ...sessions[session.session_id], counted: true };
      if (session.refund_decision === 'approved') stats.approved++;
      else if (session.refund_decision === 'denied') stats.denied++;
      else if (session.refund_decision === 'escalated') stats.escalated++;
    }
  }
  stats.total = Object.keys(sessions).length;
  renderStats();
}

function updateAllStats() {
  stats = { total: 0, approved: 0, denied: 0, escalated: 0 };
  Object.values(sessions).forEach(s => {
    stats.total++;
    if (s.refund_decision === 'approved') stats.approved++;
    else if (s.refund_decision === 'denied') stats.denied++;
    else if (s.refund_decision === 'escalated') stats.escalated++;
  });
  renderStats();
}

function renderStats() {
  if (statTotal)     statTotal.textContent     = stats.total;
  if (statApproved)  statApproved.textContent  = stats.approved;
  if (statDenied)    statDenied.textContent    = stats.denied;
  if (statEscalated) statEscalated.textContent = stats.escalated;
}

// ─── Helpers ─────────────────────────────────────────────
function formatRelTime(iso) {
  const diff = Date.now() - new Date(iso).getTime();
  if (diff < 60000) return 'just now';
  if (diff < 3600000) return Math.floor(diff / 60000) + 'm ago';
  if (diff < 86400000) return Math.floor(diff / 3600000) + 'h ago';
  return new Date(iso).toLocaleDateString();
}

function formatLogTime(iso) {
  try {
    return new Date(iso).toLocaleTimeString([], {
      hour: '2-digit', minute: '2-digit', second: '2-digit'
    });
  } catch { return '--:--:--'; }
}

function escapeHtml(str) {
  return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}
