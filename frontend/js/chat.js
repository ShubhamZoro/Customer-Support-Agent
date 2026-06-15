/**
 * ShopWave AI Support — Chat Frontend JS
 *
 * Auth flow:
 *  1. Load → check sessionStorage for saved auth → skip login if found.
 *  2. Login via modal → POST /api/auth/login → store session_id + user info.
 *  3. WebSocket: ws://host/ws/chat/{chatSessionId}?auth={authSessionId}
 *  4. Backend resolves auth token → user_id injected into agent state.
 *  5. Logout → POST /api/auth/logout → clear sessionStorage → show login modal.
 */

// ─── State ────────────────────────────────────────────────────────────────────
let socket        = null;
let chatSessionId = null;
let authSessionId = null;
let currentUser   = null;   // { user_id, email, user_name }
let autoSpeak     = false;
let isRecording   = false;
let mediaRecorder = null;
let audioChunks   = [];
let isConnected   = false;

const API_BASE = (window.location.origin && window.location.origin !== 'null' && !window.location.origin.startsWith('file'))
  ? window.location.origin
  : 'http://localhost:8000';
const WS_BASE  = API_BASE.replace(/^http/, 'ws');

// ─── Init ─────────────────────────────────────────────────────────────────────
window.addEventListener('DOMContentLoaded', () => {
  setupInputListeners();

  const saved = sessionStorage.getItem('shopwave_auth');
  if (saved) {
    try {
      const parsed = JSON.parse(saved);
      // Verify the session is still valid on the server before connecting
      fetch(`${API_BASE}/api/auth/me?session_id=${parsed.session_id}`)
        .then(r => {
          if (r.ok) {
            authSessionId = parsed.session_id;
            currentUser   = { user_id: parsed.user_id, email: parsed.email, user_name: parsed.user_name };
            showLoggedIn();
            initChat();
          } else {
            // Session expired / server restarted — force re-login
            sessionStorage.removeItem('shopwave_auth');
            showLoginModal();
          }
        })
        .catch(() => {
          // Server unreachable — still try with saved creds
          authSessionId = parsed.session_id;
          currentUser   = { user_id: parsed.user_id, email: parsed.email, user_name: parsed.user_name };
          showLoggedIn();
          initChat();
        });
    } catch {
      sessionStorage.removeItem('shopwave_auth');
      showLoginModal();
    }
  } else {
    showLoginModal();
  }
});

// ─── Login / Logout ───────────────────────────────────────────────────────────
function showLoginModal() {
  const overlay = document.getElementById('login-overlay');
  overlay.classList.remove('hidden');
  setTimeout(() => document.getElementById('login-email')?.focus(), 100);
}

function hideLoginModal() {
  document.getElementById('login-overlay').classList.add('hidden');
}

async function handleLogin(event) {
  event.preventDefault();
  const email    = document.getElementById('login-email').value.trim();
  const password = document.getElementById('login-password').value;
  if (!email || !password) return;

  const btn = document.getElementById('login-btn');
  btn.disabled = true;
  btn.classList.add('loading');
  document.getElementById('login-error').classList.remove('visible');

  try {
    const resp = await fetch(`${API_BASE}/api/auth/login`, {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify({ email, password }),
    });

    if (!resp.ok) {
      const err = await resp.json().catch(() => ({}));
      showLoginError(err.detail || 'Invalid email or password.');
      return;
    }

    const data = await resp.json();
    authSessionId = data.session_id;
    const firstName = data.email.split('@')[0].split('.')[0];
    currentUser = {
      user_id:   data.user_id,
      email:     data.email,
      user_name: firstName.charAt(0).toUpperCase() + firstName.slice(1),
    };

    sessionStorage.setItem('shopwave_auth', JSON.stringify({
      session_id: authSessionId,
      user_id:    currentUser.user_id,
      email:      currentUser.email,
      user_name:  currentUser.user_name,
    }));

    hideLoginModal();
    showLoggedIn();
    initChat();

  } catch {
    showLoginError('Connection error. Is the server running?');
  } finally {
    btn.disabled = false;
    btn.classList.remove('loading');
  }
}

function showLoginError(msg) {
  const el = document.getElementById('login-error');
  document.getElementById('login-error-msg').textContent = msg;
  el.classList.add('visible');
}

function fillDemo(email) {
  document.getElementById('login-email').value    = email;
  document.getElementById('login-password').value = 'password123';
  document.getElementById('login-email').focus();
}

async function handleLogout() {
  if (authSessionId) {
    try {
      await fetch(`${API_BASE}/api/auth/logout`, {
        method:  'POST',
        headers: { 'Content-Type': 'application/json' },
        body:    JSON.stringify({ session_id: authSessionId }),
      });
    } catch { /* best effort */ }
  }

  if (socket) { try { socket.close(); } catch {} }
  socket = null;
  authSessionId = null;
  currentUser   = null;
  chatSessionId = null;
  sessionStorage.removeItem('shopwave_auth');

  // Reset UI
  document.getElementById('user-pill').style.display  = 'none';
  document.getElementById('logout-btn').style.display = 'none';
  document.getElementById('sidebar-user-info').innerHTML = '<div class="user-info-placeholder">Not signed in</div>';
  document.getElementById('messages').innerHTML = buildWelcomeHTML();
  document.getElementById('mini-log').innerHTML  = '';
  setConnectionStatus(false, 'Disconnected');

  showLoginModal();
}

// ─── Show logged-in UI ────────────────────────────────────────────────────────
function showLoggedIn() {
  if (!currentUser) return;
  const initials = currentUser.user_name.slice(0, 2).toUpperCase();

  document.getElementById('user-pill-avatar').textContent = initials;
  document.getElementById('user-pill-name').textContent   = currentUser.user_name;
  document.getElementById('user-pill').style.display      = 'flex';
  document.getElementById('logout-btn').style.display     = 'inline-flex';

  document.getElementById('sidebar-user-info').innerHTML = `
    <div class="user-info-name">${currentUser.user_name}</div>
    <div class="user-info-email">${currentUser.email}</div>
    <div class="user-info-id">${currentUser.user_id}</div>
  `;
}

// ─── Chat init / session ──────────────────────────────────────────────────────
function initChat() {
  chatSessionId = generateSessionId();
  const display = document.getElementById('session-id-display');
  if (display) display.textContent = chatSessionId.slice(0, 12) + '…';
  connectWebSocket();
}

function generateSessionId() {
  return 'sess-' + Math.random().toString(36).slice(2, 10) + Date.now().toString(36);
}

function newSession() {
  if (socket) { try { socket.close(); } catch {} }
  document.getElementById('messages').innerHTML = buildWelcomeHTML();
  document.getElementById('mini-log').innerHTML  = '';
  initChat();
}

function buildWelcomeHTML() {
  return `
    <div class="welcome-screen" id="welcome-screen">
      <div class="welcome-icon-wrap">
        <div class="welcome-icon">🤖</div>
        <div class="welcome-icon-pulse"></div>
      </div>
      <h1 class="welcome-title">Hi, I'm ShopWave AI</h1>
      <p class="welcome-subtitle">I can help you with refunds, returns, and policy questions.<br/>I already know who you are — just tell me what you need!</p>
      <div class="suggestion-chips">
        <div class="chip" onclick="sendSuggestion('I want a refund on my recent order')">🔄 Request a refund</div>
        <div class="chip" onclick="sendSuggestion('Show me all my orders')">📦 View my orders</div>
        <div class="chip" onclick="sendSuggestion('My item arrived damaged')">💥 Damaged item</div>
        <div class="chip" onclick="sendSuggestion('What is the return policy for Electronics?')">📋 Return policy</div>
        <div class="chip" onclick="sendSuggestion('I received the wrong item')">❌ Wrong item</div>
      </div>
    </div>
    <div class="typing-indicator" id="typing-indicator">
      <div class="msg-avatar bot">🤖</div>
      <div class="typing-bubble">
        <div class="typing-dots"><span></span><span></span><span></span></div>
      </div>
    </div>
  `;
}

// ─── WebSocket ────────────────────────────────────────────────────────────────
function connectWebSocket() {
  if (!authSessionId) { showLoginModal(); return; }
  setConnectionStatus(false, 'Connecting…');

  socket = new WebSocket(`${WS_BASE}/ws/chat/${chatSessionId}?auth=${authSessionId}`);

  socket.onopen  = () => {};
  socket.onmessage = (event) => {
    try { handleServerMessage(JSON.parse(event.data)); } catch (e) { console.error('WS parse error', e); }
  };
  socket.onclose = (e) => {
    isConnected = false;
    if (e.code === 1008) {
      setConnectionStatus(false, 'Auth failed — please log in');
      sessionStorage.removeItem('shopwave_auth');
      showLoginModal();
    } else {
      setConnectionStatus(false, 'Disconnected');
      setTimeout(() => { if (authSessionId) connectWebSocket(); }, 3000);
    }
  };
  socket.onerror = () => setConnectionStatus(false, 'Connection error');
}

function handleServerMessage(data) {
  switch (data.type) {

    case 'authenticated':
      isConnected = true;
      setConnectionStatus(true, 'Connected');
      if (data.user_name && currentUser) currentUser.user_name = data.user_name;
      showLoggedIn();
      break;

    case 'auth_error':
      setConnectionStatus(false, 'Auth failed');
      sessionStorage.removeItem('shopwave_auth');
      showLoginModal();
      break;

    case 'typing':
      const ti = document.getElementById('typing-indicator');
      if (ti) ti.classList.toggle('visible', data.status);
      if (data.status) scrollToBottom();
      break;

    case 'reasoning_log':
      appendMiniLog(data.log);
      break;

    case 'message':
      const ti2 = document.getElementById('typing-indicator');
      if (ti2) ti2.classList.remove('visible');
      appendMessage('assistant', data.content, data.refund_decision);
      break;

    case 'error':
      const ti3 = document.getElementById('typing-indicator');
      if (ti3) ti3.classList.remove('visible');
      appendSystemMessage('⚠️ ' + data.message, 'error');
      break;
  }
}

// ─── Send ─────────────────────────────────────────────────────────────────────
function sendMessage(text) {
  if (!text || !text.trim()) return;
  if (!socket || socket.readyState !== WebSocket.OPEN) {
    appendSystemMessage('Not connected. Reconnecting…', 'warning');
    connectWebSocket();
    return;
  }

  const trimmed = text.trim();
  appendMessage('user', trimmed);

  const input = document.getElementById('message-input');
  if (input) { input.value = ''; autoResizeTextarea(input); }

  // Hide welcome screen
  const ws = document.getElementById('welcome-screen');
  if (ws) ws.style.display = 'none';

  socket.send(JSON.stringify({ message: trimmed }));
}

function sendSuggestion(text) {
  const input = document.getElementById('message-input');
  if (input) input.value = text;
  sendMessage(text);
}

// ─── Message rendering ────────────────────────────────────────────────────────
function appendMessage(role, content, decision = null) {
  const wrapper = document.createElement('div');
  wrapper.className = `message-wrapper ${role}`;

  const avatar = document.createElement('div');
  avatar.className = role === 'user' ? 'msg-avatar user-av' : 'msg-avatar bot';
  avatar.textContent = role === 'user' ? (currentUser?.user_name?.charAt(0) || 'U') : '🤖';

  const bubble = document.createElement('div');
  bubble.className = `bubble ${role}`;
  bubble.innerHTML = formatMessage(content);

  // Refund decision banner
  if (decision && role === 'assistant') {
    const banner = document.createElement('div');
    if (decision === 'refund_initiated') {
      banner.className = 'refund-banner success';
      banner.innerHTML = `
        <div class="refund-banner-icon">✅</div>
        <div class="refund-banner-body">
          <div class="refund-banner-title">Refund Initiated</div>
          <div class="refund-banner-detail">Check your email for confirmation details.</div>
        </div>`;
    } else if (decision === 'denied') {
      banner.className = 'refund-banner denied';
      banner.innerHTML = `
        <div class="refund-banner-icon">❌</div>
        <div class="refund-banner-body">
          <div class="refund-banner-title">Refund Not Eligible</div>
          <div class="refund-banner-detail">See the explanation above for the policy reason.</div>
        </div>`;
    }
    if (banner.className) bubble.appendChild(banner);
  }

  const meta = document.createElement('div');
  meta.className = 'msg-meta';
  meta.textContent = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

  const inner = document.createElement('div');
  inner.style.cssText = 'display:flex;flex-direction:column;gap:2px;max-width:100%;';
  inner.appendChild(bubble);
  inner.appendChild(meta);

  if (role === 'user') {
    wrapper.appendChild(inner);
    wrapper.appendChild(avatar);
  } else {
    wrapper.appendChild(avatar);
    wrapper.appendChild(inner);
  }

  const typing = document.getElementById('typing-indicator');
  const messages = document.getElementById('messages');
  if (messages && typing) messages.insertBefore(wrapper, typing);
  scrollToBottom();

  if (role === 'assistant' && autoSpeak) speakText(content);
}

function appendSystemMessage(text, type = 'info') {
  const el = document.createElement('div');
  el.className = `system-message ${type}`;
  el.textContent = text;
  const typing = document.getElementById('typing-indicator');
  const messages = document.getElementById('messages');
  if (messages && typing) messages.insertBefore(el, typing);
  scrollToBottom();
}

function formatMessage(text) {
  if (!text) return '';
  return text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.+?)\*/g, '<em>$1</em>')
    .replace(/`([^`]+)`/g, '<code style="background:var(--bg-input);padding:1px 6px;border-radius:4px;font-family:monospace;font-size:0.86em">$1</code>')
    .replace(/\n/g, '<br>');
}

// ─── Reasoning mini log ───────────────────────────────────────────────────────
function appendMiniLog(log) {
  const icons = { info: '🔍', success: '✅', error: '❌', warning: '⚠️' };
  const icon  = icons[log.level] || '•';
  const container = document.getElementById('mini-log');
  if (!container) return;

  const el = document.createElement('div');
  el.className = 'mini-log-entry';
  el.innerHTML = `<span class="mini-log-icon">${icon}</span><span class="mini-log-msg">${formatMessage(log.message)}</span>`;
  container.appendChild(el);
  container.scrollTop = container.scrollHeight;

  while (container.children.length > 50) container.removeChild(container.firstChild);
}

// ─── Connection status ────────────────────────────────────────────────────────
function setConnectionStatus(connected, label = null) {
  isConnected = connected;
  const dot = document.getElementById('connection-dot');
  const lbl = document.getElementById('connection-label');
  if (dot) dot.classList.toggle('connected', connected);
  if (lbl) lbl.textContent = label || (connected ? 'Connected' : 'Disconnected');
}

// ─── Voice ────────────────────────────────────────────────────────────────────
function toggleAutoSpeak() {
  autoSpeak = !autoSpeak;
  const btn = document.getElementById('auto-speak-toggle');
  if (btn) {
    btn.classList.toggle('active', autoSpeak);
    btn.innerHTML = autoSpeak
      ? '<svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor"><path d="M3 9v6h4l5 5V4L7 9H3zm13.5 3c0-1.77-1.02-3.29-2.5-4.03v8.05c1.48-.73 2.5-2.25 2.5-4.02zM14 3.23v2.06c2.89.86 5 3.54 5 6.71s-2.11 5.85-5 6.71v2.06c4.01-.91 7-4.49 7-8.77s-2.99-7.86-7-8.77z"/></svg> Voice On'
      : '<svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor"><path d="M3 9v6h4l5 5V4L7 9H3zm13.5 3c0-1.77-1.02-3.29-2.5-4.03v8.05c1.48-.73 2.5-2.25 2.5-4.02z"/></svg> Voice';
  }
}

async function toggleRecording() {
  if (isRecording) stopRecording();
  else await startRecording();
}

async function startRecording() {
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    mediaRecorder = new MediaRecorder(stream);
    audioChunks   = [];

    mediaRecorder.ondataavailable = (e) => { if (e.data.size > 0) audioChunks.push(e.data); };
    mediaRecorder.onstop = async () => {
      const blob = new Blob(audioChunks, { type: 'audio/webm' });
      await transcribeAudio(blob);
      stream.getTracks().forEach(t => t.stop());
    };

    mediaRecorder.start();
    isRecording = true;

    // Update mic button
    const micBtn = document.getElementById('mic-btn');
    if (micBtn) micBtn.classList.add('recording');

    // Update voice orb
    const orb = document.getElementById('voice-orb');
    if (orb) orb.classList.add('recording');

    const voiceLabel = document.getElementById('voice-label');
    if (voiceLabel) voiceLabel.textContent = 'Recording… click to stop';

    const waveBars = document.getElementById('voice-wave-bars');
    if (waveBars) waveBars.classList.add('active');

  } catch {
    appendSystemMessage('Microphone access denied.', 'error');
  }
}

function stopRecording() {
  if (mediaRecorder && mediaRecorder.state !== 'inactive') mediaRecorder.stop();
  isRecording = false;

  const micBtn = document.getElementById('mic-btn');
  if (micBtn) micBtn.classList.remove('recording');

  const orb = document.getElementById('voice-orb');
  if (orb) orb.classList.remove('recording');

  const voiceLabel = document.getElementById('voice-label');
  if (voiceLabel) voiceLabel.textContent = 'Click to speak';

  const waveBars = document.getElementById('voice-wave-bars');
  if (waveBars) waveBars.classList.remove('active');
}

async function transcribeAudio(blob) {
  const formData = new FormData();
  formData.append('audio', blob, 'recording.webm');
  try {
    const resp = await fetch(`${API_BASE}/api/voice/transcribe`, { method: 'POST', body: formData });
    if (resp.ok) {
      const { text } = await resp.json();
      if (text) sendMessage(text);
    }
  } catch {
    appendSystemMessage('Voice transcription failed.', 'error');
  }
}

function speakText(text) {
  const plain = text.replace(/<[^>]+>/g, '').slice(0, 500);
  const utt   = new SpeechSynthesisUtterance(plain);
  utt.rate = 1.05;
  window.speechSynthesis.speak(utt);
}

// ─── Input helpers ────────────────────────────────────────────────────────────
function setupInputListeners() {
  const input = document.getElementById('message-input');
  if (!input) return;
  input.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage(input.value);
    }
  });
  input.addEventListener('input', () => autoResizeTextarea(input));
}

function autoResizeTextarea(el) {
  el.style.height = 'auto';
  el.style.height = Math.min(el.scrollHeight, 120) + 'px';
}

function scrollToBottom() {
  const el = document.getElementById('messages');
  if (el) el.scrollTop = el.scrollHeight;
}
