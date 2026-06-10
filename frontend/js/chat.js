/* =====================================================
   ShopWave Chat JS — WebSocket + Voice Pipeline
   ===================================================== */

const API_BASE = 'http://localhost:8000';
const WS_BASE  = 'ws://localhost:8000';

// ─── State ──────────────────────────────────────────────
let sessionId     = generateSessionId();
let ws            = null;
let mediaRecorder = null;
let audioChunks   = [];
let isRecording   = false;
let isSending     = false;
let currentAudio  = null;
let autoSpeak     = false;

// ─── DOM Refs ────────────────────────────────────────────
const messagesEl      = document.getElementById('messages');
const welcomeEl       = document.getElementById('welcome-screen');
const inputEl         = document.getElementById('message-input');
const sendBtn         = document.getElementById('send-btn');
const micBtn          = document.getElementById('mic-btn');
const voiceStatusEl   = document.getElementById('voice-status');
const typingEl        = document.getElementById('typing-indicator');
const sessionIdEl     = document.getElementById('session-id-display');
const customerInfoEl  = document.getElementById('customer-info');
const autoSpeakToggle = document.getElementById('auto-speak-toggle');
const connectionDot   = document.getElementById('connection-dot');
const connectionLabel = document.getElementById('connection-label');

// ─── Init ────────────────────────────────────────────────
window.addEventListener('DOMContentLoaded', () => {
  sessionIdEl.textContent = sessionId;
  connectWebSocket();
  setupInputAutoResize();
  inputEl.focus();
});

// ─── WebSocket ───────────────────────────────────────────
function connectWebSocket() {
  ws = new WebSocket(`${WS_BASE}/ws/chat/${sessionId}`);

  ws.onopen = () => {
    setConnectionStatus(true);
  };

  ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    handleServerMessage(data);
  };

  ws.onclose = () => {
    setConnectionStatus(false);
    setTimeout(connectWebSocket, 3000); // auto-reconnect
  };

  ws.onerror = () => {
    setConnectionStatus(false);
  };
}

function setConnectionStatus(connected) {
  connectionDot.classList.toggle('connected', connected);
  connectionLabel.textContent = connected ? 'Connected' : 'Reconnecting...';
}

// ─── Message Handler ─────────────────────────────────────
function handleServerMessage(data) {
  switch (data.type) {
    case 'typing':
      showTyping(data.status);
      break;
    case 'message':
      appendMessage('assistant', data.content, data.timestamp, data.refund_decision);
      if (autoSpeak && data.content) speakText(data.content);
      break;
    case 'reasoning_log':
      // Sidebar mini-log (optional)
      appendMiniLog(data.log);
      break;
    case 'error':
      appendMessage('assistant', `⚠️ ${data.message}`, new Date().toISOString());
      break;
  }
}

// ─── Send Message ────────────────────────────────────────
async function sendMessage(text) {
  text = text.trim();
  if (!text || isSending) return;

  if (!ws || ws.readyState !== WebSocket.OPEN) {
    showToast('Not connected. Reconnecting…', 'error');
    return;
  }

  isSending = true;
  sendBtn.disabled = true;

  hideWelcome();
  appendMessage('user', text, new Date().toISOString());
  inputEl.value = '';
  inputEl.style.height = 'auto';

  ws.send(JSON.stringify({ message: text }));

  isSending = false;
  sendBtn.disabled = false;
  inputEl.focus();
}

// ─── DOM: Append message ──────────────────────────────────
function appendMessage(role, content, timestamp, decision = null) {
  // Remove welcome screen
  hideWelcome();

  const isUser = role === 'user';
  const time = formatTime(timestamp);
  const initials = isUser ? '👤' : '🤖';
  const avatarClass = isUser ? 'user-av' : 'bot';

  const wrapper = document.createElement('div');
  wrapper.className = `message-wrapper ${role}`;

  // Format markdown-like content
  const formattedContent = formatContent(content);

  // Decision badge
  let decisionBadge = '';
  if (decision) {
    const icons = { approved: '✅', denied: '❌', escalated: '⚠️' };
    decisionBadge = `
      <div class="decision-badge decision-${decision}">
        ${icons[decision] || ''} Refund ${decision}
      </div>`;
  }

  wrapper.innerHTML = `
    <div class="msg-avatar ${avatarClass}">${initials}</div>
    <div>
      <div class="bubble ${role}">
        ${formattedContent}
        ${decisionBadge}
      </div>
      <div class="msg-meta">${time}</div>
    </div>
  `;

  typingEl.insertAdjacentElement('beforebegin', wrapper);
  scrollToBottom();
}

function hideWelcome() {
  if (welcomeEl) welcomeEl.style.display = 'none';
}

// ─── Typing indicator ─────────────────────────────────────
function showTyping(show) {
  typingEl.classList.toggle('visible', show);
  if (show) scrollToBottom();
}

// ─── Mini reasoning log in sidebar ───────────────────────
function appendMiniLog(log) {
  const container = document.getElementById('mini-log');
  if (!container) return;

  const icons = { info: 'ℹ️', success: '✅', error: '❌', warning: '⚠️' };
  const el = document.createElement('div');
  el.className = 'mini-log-entry';
  el.innerHTML = `
    <span class="mini-log-icon">${icons[log.level] || 'ℹ️'}</span>
    <span class="mini-log-msg">${log.message.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')}</span>
  `;
  container.prepend(el);

  // Keep only last 20
  while (container.children.length > 20) {
    container.removeChild(container.lastChild);
  }
}

// ─── Voice: Record audio ──────────────────────────────────
async function toggleRecording() {
  if (isRecording) {
    stopRecording();
  } else {
    await startRecording();
  }
}

async function startRecording() {
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    audioChunks = [];
    mediaRecorder = new MediaRecorder(stream, { mimeType: 'audio/webm' });

    mediaRecorder.ondataavailable = (e) => {
      if (e.data.size > 0) audioChunks.push(e.data);
    };

    mediaRecorder.onstop = async () => {
      stream.getTracks().forEach(t => t.stop());
      await transcribeAudio();
    };

    mediaRecorder.start();
    isRecording = true;
    micBtn.classList.add('recording');
    micBtn.title = 'Stop recording';
    micBtn.textContent = '⏹';
    voiceStatusEl.classList.add('visible');
  } catch (err) {
    showToast('Microphone access denied', 'error');
  }
}

function stopRecording() {
  if (mediaRecorder && mediaRecorder.state !== 'inactive') {
    mediaRecorder.stop();
  }
  isRecording = false;
  micBtn.classList.remove('recording');
  micBtn.title = 'Voice input';
  micBtn.textContent = '🎤';
  voiceStatusEl.classList.remove('visible');
}

async function transcribeAudio() {
  if (!audioChunks.length) return;

  const blob = new Blob(audioChunks, { type: 'audio/webm' });
  const formData = new FormData();
  formData.append('audio', blob, 'recording.webm');

  showToast('Transcribing…', 'info');

  try {
    const res = await fetch(`${API_BASE}/api/voice/transcribe`, {
      method: 'POST',
      body: formData,
    });
    if (!res.ok) throw new Error(await res.text());
    const data = await res.json();
    if (data.text) {
      inputEl.value = data.text;
      inputEl.dispatchEvent(new Event('input'));
      showToast('Transcribed! Press Send or Enter.', 'success');
    }
  } catch (err) {
    showToast('Transcription failed: ' + err.message, 'error');
  }
}

// ─── Voice: TTS playback ──────────────────────────────────
async function speakText(text) {
  if (currentAudio) {
    currentAudio.pause();
    currentAudio = null;
  }

  // Trim to 500 chars for quick playback
  const trimmed = text.replace(/[#*`]/g, '').substring(0, 500);

  try {
    const res = await fetch(`${API_BASE}/api/voice/synthesize`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text: trimmed, voice: 'alloy' }),
    });
    if (!res.ok) return;

    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    currentAudio = new Audio(url);
    currentAudio.play();
    currentAudio.onended = () => { URL.revokeObjectURL(url); };
  } catch (err) {
    console.error('TTS error:', err);
  }
}

// ─── Quick Suggestion Chips ───────────────────────────────
function sendSuggestion(text) {
  inputEl.value = text;
  sendMessage(text);
}

// ─── Auto-speak toggle ────────────────────────────────────
function toggleAutoSpeak() {
  autoSpeak = !autoSpeak;
  if (autoSpeakToggle) {
    autoSpeakToggle.classList.toggle('active', autoSpeak);
    autoSpeakToggle.title = autoSpeak ? 'Auto-speak ON' : 'Auto-speak OFF';
    autoSpeakToggle.textContent = autoSpeak ? '🔊' : '🔇';
  }
}

// ─── New Session ──────────────────────────────────────────
function newSession() {
  sessionId = generateSessionId();
  sessionIdEl.textContent = sessionId;

  // Clear messages UI
  const msgs = messagesEl.querySelectorAll('.message-wrapper');
  msgs.forEach(m => m.remove());
  if (welcomeEl) welcomeEl.style.display = 'flex';

  // Clear mini log
  const miniLog = document.getElementById('mini-log');
  if (miniLog) miniLog.innerHTML = '';

  // Reset customer info
  updateCustomerInfo(null);

  // Reconnect
  if (ws) ws.close();
  connectWebSocket();
}

// ─── Customer info sidebar ────────────────────────────────
function updateCustomerInfo(customer) {
  if (!customerInfoEl) return;
  if (!customer) {
    customerInfoEl.innerHTML = `
      <div class="sidebar-label">Customer</div>
      <div class="text-sm text-muted" style="padding:8px 0">No customer identified yet</div>
    `;
    return;
  }

  const tierClass = `tier-${customer.tier}`;
  const initials = customer.name.split(' ').map(n => n[0]).join('');
  customerInfoEl.innerHTML = `
    <div class="sidebar-label">Customer</div>
    <div class="customer-card">
      <div class="flex items-center gap-2 mb-2">
        <div class="customer-avatar">${initials}</div>
        <div class="customer-info">
          <div class="customer-name">${customer.name}</div>
          <div class="customer-email">${customer.email}</div>
        </div>
      </div>
      <div class="tier-badge ${tierClass}">⭐ ${customer.tier}</div>
      <div class="flex gap-2 mt-2" style="flex-wrap:wrap">
        <div class="text-xs text-muted">Refunds: <strong>${customer.total_refunds_this_year}/3</strong></div>
        <div class="text-xs text-muted">Points: <strong>${customer.loyalty_points.toLocaleString()}</strong></div>
      </div>
    </div>
  `;
}

// ─── Input handling ───────────────────────────────────────
function setupInputAutoResize() {
  inputEl.addEventListener('input', () => {
    inputEl.style.height = 'auto';
    inputEl.style.height = Math.min(inputEl.scrollHeight, 120) + 'px';
  });

  inputEl.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage(inputEl.value);
    }
  });
}

// ─── Helpers ─────────────────────────────────────────────
function generateSessionId() {
  return 'sess-' + Math.random().toString(36).substring(2, 10).toUpperCase();
}

function formatTime(iso) {
  try {
    return new Date(iso).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  } catch { return ''; }
}

function formatContent(text) {
  if (!text) return '';
  return text
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.*?)\*/g, '<em>$1</em>')
    .replace(/`(.*?)`/g, '<code>$1</code>')
    .replace(/\n/g, '<br>');
}

function scrollToBottom() {
  messagesEl.scrollTop = messagesEl.scrollHeight;
}

function showToast(message, type = 'info') {
  const existing = document.querySelector('.toast');
  if (existing) existing.remove();

  const colors = { info: '#38bdf8', success: '#22c55e', error: '#ef4444' };
  const toast = document.createElement('div');
  toast.className = 'toast';
  toast.style.cssText = `
    position:fixed; bottom:20px; right:20px; z-index:9999;
    padding:10px 16px; border-radius:8px;
    background:#1c202a; border:1px solid ${colors[type]};
    color:${colors[type]}; font-size:0.82rem; font-weight:500;
    animation:message-in 0.2s ease-out;
    box-shadow:0 4px 20px rgba(0,0,0,0.5);
  `;
  toast.textContent = message;
  document.body.appendChild(toast);
  setTimeout(() => toast.remove(), 3000);
}
