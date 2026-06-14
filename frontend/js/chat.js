/**
 * ShopWave AI Support — Chat Frontend
 *
 * Auth Flow:
 *   1. On load: check sessionStorage for saved auth session → if found, skip login.
 *   2. User logs in via modal → POST /api/auth/login → stores session_id + user info.
 *   3. WebSocket URL: ws://host/ws/chat/{chatSessionId}?auth={authSessionId}
 *   4. Backend resolves auth token → user_id is injected into agent state.
 *   5. Logout: POST /api/auth/logout → clear sessionStorage → show login modal.
 */

// ─── State ────────────────────────────────────────────────────────────────────
let socket         = null;
let chatSessionId  = null;
let authSessionId  = null;
let currentUser    = null;   // { user_id, email, user_name }
let autoSpeak      = false;
let isRecording    = false;
let mediaRecorder  = null;
let audioChunks    = [];
let isConnected    = false;

const API_BASE = window.location.origin;
const WS_BASE  = API_BASE.replace(/^http/, "ws");

// ─── DOM refs ─────────────────────────────────────────────────────────────────
const loginOverlay      = () => document.getElementById("login-overlay");
const loginEmailEl      = () => document.getElementById("login-email");
const loginPasswordEl   = () => document.getElementById("login-password");
const loginBtnEl        = () => document.getElementById("login-btn");
const loginErrorEl      = () => document.getElementById("login-error");
const loginErrorMsg     = () => document.getElementById("login-error-msg");
const messagesEl        = () => document.getElementById("messages");
const typingEl          = () => document.getElementById("typing-indicator");
const messageInput      = () => document.getElementById("message-input");
const sendBtnEl         = () => document.getElementById("send-btn");
const miniLogEl         = () => document.getElementById("mini-log");
const connectionDot     = () => document.getElementById("connection-dot");
const connectionLabel   = () => document.getElementById("connection-label");
const sessionIdDisplay  = () => document.getElementById("session-id-display");
const userPillEl        = () => document.getElementById("user-pill");
const userPillAvatarEl  = () => document.getElementById("user-pill-avatar");
const userPillNameEl    = () => document.getElementById("user-pill-name");
const logoutBtnEl       = () => document.getElementById("logout-btn");
const sidebarUserInfo   = () => document.getElementById("sidebar-user-info");
const welcomeScreenEl   = () => document.getElementById("welcome-screen");

// ─── Init ─────────────────────────────────────────────────────────────────────
window.addEventListener("DOMContentLoaded", () => {
  setupInputListeners();

  // Try to restore auth from sessionStorage
  const saved = sessionStorage.getItem("shopwave_auth");
  if (saved) {
    try {
      const parsed = JSON.parse(saved);
      authSessionId = parsed.session_id;
      currentUser   = { user_id: parsed.user_id, email: parsed.email, user_name: parsed.user_name };
      showLoggedIn();
      initChat();
    } catch {
      sessionStorage.removeItem("shopwave_auth");
      showLoginModal();
    }
  } else {
    showLoginModal();
  }
});

// ─── Login Modal ──────────────────────────────────────────────────────────────
function showLoginModal() {
  loginOverlay().classList.remove("hidden");
  setTimeout(() => loginEmailEl()?.focus(), 100);
}

function hideLoginModal() {
  loginOverlay().classList.add("hidden");
}

async function handleLogin(event) {
  event.preventDefault();
  const email    = loginEmailEl().value.trim();
  const password = loginPasswordEl().value;

  if (!email || !password) return;

  const btn = loginBtnEl();
  btn.disabled = true;
  btn.classList.add("loading");
  btn.textContent = "Signing in…";
  loginErrorEl().classList.remove("visible");

  try {
    const resp = await fetch(`${API_BASE}/api/auth/login`, {
      method:  "POST",
      headers: { "Content-Type": "application/json" },
      body:    JSON.stringify({ email, password }),
    });

    if (!resp.ok) {
      const err = await resp.json().catch(() => ({}));
      showLoginError(err.detail || "Invalid email or password.");
      return;
    }

    const data = await resp.json();
    // data: { session_id, user_id, email, login_at }
    authSessionId = data.session_id;
    const firstName = data.email.split("@")[0].split(".")[0];
    currentUser = {
      user_id:   data.user_id,
      email:     data.email,
      user_name: firstName.charAt(0).toUpperCase() + firstName.slice(1),
    };

    // Persist
    sessionStorage.setItem("shopwave_auth", JSON.stringify({
      session_id: authSessionId,
      user_id:    currentUser.user_id,
      email:      currentUser.email,
      user_name:  currentUser.user_name,
    }));

    hideLoginModal();
    showLoggedIn();
    initChat();

  } catch (err) {
    showLoginError("Connection error. Is the server running?");
  } finally {
    btn.disabled = false;
    btn.classList.remove("loading");
    btn.textContent = "Sign In";
  }
}

function showLoginError(msg) {
  loginErrorMsg().textContent = msg;
  loginErrorEl().classList.add("visible");
}

function fillDemo(email) {
  loginEmailEl().value    = email;
  loginPasswordEl().value = "password123";
  loginEmailEl().focus();
}

// ─── Logout ───────────────────────────────────────────────────────────────────
async function handleLogout() {
  if (authSessionId) {
    try {
      await fetch(`${API_BASE}/api/auth/logout`, {
        method:  "POST",
        headers: { "Content-Type": "application/json" },
        body:    JSON.stringify({ session_id: authSessionId }),
      });
    } catch { /* best effort */ }
  }

  // Close WebSocket
  if (socket) { try { socket.close(); } catch {} }
  socket = null;

  // Clear state
  authSessionId = null;
  currentUser   = null;
  chatSessionId = null;
  sessionStorage.removeItem("shopwave_auth");

  // Reset UI
  userPillEl().style.display  = "none";
  logoutBtnEl().style.display = "none";
  sidebarUserInfo().textContent = "Not signed in";
  messagesEl().innerHTML = "";
  miniLogEl().innerHTML  = "";
  setConnectionStatus(false);

  // Show login
  showLoginModal();
}

// ─── Show logged-in UI ────────────────────────────────────────────────────────
function showLoggedIn() {
  if (!currentUser) return;
  const initials = currentUser.user_name.slice(0, 2).toUpperCase();
  userPillAvatarEl().textContent = initials;
  userPillNameEl().textContent   = currentUser.user_name;
  userPillEl().style.display     = "flex";
  logoutBtnEl().style.display    = "inline-flex";
  sidebarUserInfo().innerHTML =
    `<strong style="color:var(--text-primary)">${currentUser.user_name}</strong><br>
     <span style="font-size:0.72rem">${currentUser.email}</span><br>
     <span style="font-size:0.7rem;color:var(--text-muted)">${currentUser.user_id}</span>`;
}

// ─── Chat Init ────────────────────────────────────────────────────────────────
function initChat() {
  chatSessionId = generateSessionId();
  sessionIdDisplay().textContent = chatSessionId.slice(0, 12) + "…";
  connectWebSocket();
}

function generateSessionId() {
  return "sess-" + Math.random().toString(36).slice(2, 10) + Date.now().toString(36);
}

// ─── WebSocket ────────────────────────────────────────────────────────────────
function connectWebSocket() {
  if (!authSessionId) { showLoginModal(); return; }

  setConnectionStatus(false, "Connecting…");
  const wsUrl = `${WS_BASE}/ws/chat/${chatSessionId}?auth=${authSessionId}`;
  socket = new WebSocket(wsUrl);

  socket.onopen = () => {
    // status set after auth acknowledgement
  };

  socket.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data);
      handleServerMessage(data);
    } catch (err) {
      console.error("WS parse error", err);
    }
  };

  socket.onclose = (e) => {
    isConnected = false;
    if (e.code === 1008) {
      // Auth failure
      setConnectionStatus(false, "Auth failed — please log in");
      sessionStorage.removeItem("shopwave_auth");
      showLoginModal();
    } else {
      setConnectionStatus(false, "Disconnected");
      setTimeout(() => { if (authSessionId) connectWebSocket(); }, 3000);
    }
  };

  socket.onerror = () => {
    setConnectionStatus(false, "Connection error");
  };
}

function handleServerMessage(data) {
  switch (data.type) {

    case "authenticated":
      isConnected = true;
      setConnectionStatus(true, "Connected");
      // Update user info from server if different
      if (data.user_name && currentUser) currentUser.user_name = data.user_name;
      showLoggedIn();
      break;

    case "auth_error":
      setConnectionStatus(false, "Auth failed");
      sessionStorage.removeItem("shopwave_auth");
      showLoginModal();
      break;

    case "typing":
      typingEl().classList.toggle("visible", data.status);
      if (data.status) scrollToBottom();
      break;

    case "reasoning_log":
      appendMiniLog(data.log);
      break;

    case "message":
      typingEl().classList.remove("visible");
      appendMessage("assistant", data.content, data.refund_decision);
      break;

    case "error":
      typingEl().classList.remove("visible");
      appendSystemMessage("⚠️ " + data.message, "error");
      break;
  }
}

// ─── Send Message ─────────────────────────────────────────────────────────────
function sendMessage(text) {
  if (!text || !text.trim()) return;
  if (!socket || socket.readyState !== WebSocket.OPEN) {
    appendSystemMessage("Not connected. Reconnecting…", "warning");
    connectWebSocket();
    return;
  }

  const trimmed = text.trim();
  appendMessage("user", trimmed);
  messageInput().value = "";
  autoResizeTextarea(messageInput());
  welcomeScreenEl().style.display = "none";

  socket.send(JSON.stringify({ message: trimmed }));
}

function sendSuggestion(text) {
  messageInput().value = text;
  sendMessage(text);
}

// ─── Message Rendering ────────────────────────────────────────────────────────
function appendMessage(role, content, decision = null) {
  const wrapper = document.createElement("div");
  wrapper.className = `message-wrapper ${role}`;

  const avatar = document.createElement("div");
  avatar.className = role === "user" ? "msg-avatar user-av" : "msg-avatar bot";
  avatar.textContent = role === "user"
    ? (currentUser?.user_name?.charAt(0) || "U")
    : "🤖";

  const bubble = document.createElement("div");
  bubble.className = `bubble ${role}`;
  bubble.innerHTML = formatMessage(content);

  // Refund decision banner inside the bubble
  if (decision && role === "assistant") {
    const banner = document.createElement("div");
    if (decision === "refund_initiated") {
      banner.className = "refund-banner success";
      banner.innerHTML = `
        <div class="refund-banner-icon">✅</div>
        <div class="refund-banner-body">
          <div class="refund-banner-title">Refund Initiated</div>
          <div class="refund-banner-detail">Check your email for confirmation details.</div>
        </div>`;
    } else if (decision === "denied") {
      banner.className = "refund-banner denied";
      banner.innerHTML = `
        <div class="refund-banner-icon">❌</div>
        <div class="refund-banner-body">
          <div class="refund-banner-title">Refund Not Eligible</div>
          <div class="refund-banner-detail">See the explanation above for the policy reason.</div>
        </div>`;
    }
    if (banner.className) bubble.appendChild(banner);
  }

  const meta = document.createElement("div");
  meta.className = "msg-meta";
  meta.textContent = formatTime(new Date());

  const inner = document.createElement("div");
  inner.style.cssText = "display:flex;flex-direction:column;gap:2px;max-width:100%";
  inner.appendChild(bubble);
  inner.appendChild(meta);

  if (role === "user") {
    wrapper.appendChild(inner);
    wrapper.appendChild(avatar);
  } else {
    wrapper.appendChild(avatar);
    wrapper.appendChild(inner);
  }

  // Insert before typing indicator
  const typing = typingEl();
  messagesEl().insertBefore(wrapper, typing);
  scrollToBottom();

  // Auto-speak for assistant messages
  if (role === "assistant" && autoSpeak) {
    speakText(content);
  }
}

function appendSystemMessage(text, type = "info") {
  const el = document.createElement("div");
  el.style.cssText = `
    text-align:center;padding:8px 16px;font-size:0.8rem;border-radius:8px;
    background:var(--${type === "error" ? "error" : type === "warning" ? "warning" : "info"}-bg);
    color:var(--${type === "error" ? "error" : type === "warning" ? "warning" : "info"});
    border:1px solid rgba(0,0,0,0.1);margin:4px auto;max-width:400px;
  `;
  el.textContent = text;
  messagesEl().insertBefore(el, typingEl());
  scrollToBottom();
}

function formatMessage(text) {
  if (!text) return "";
  return text
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
    .replace(/\*(.+?)\*/g, "<em>$1</em>")
    .replace(/`([^`]+)`/g, '<code style="background:var(--bg-input);padding:1px 5px;border-radius:3px;font-family:monospace;font-size:0.88em">$1</code>')
    .replace(/\n/g, "<br>");
}

function formatTime(date) {
  return date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

// ─── Mini Reasoning Log ───────────────────────────────────────────────────────
function appendMiniLog(log) {
  const icons = { info: "🔍", success: "✅", error: "❌", warning: "⚠️" };
  const icon  = icons[log.level] || "•";

  const el = document.createElement("div");
  el.className = "mini-log-entry";
  el.innerHTML = `
    <span class="mini-log-icon">${icon}</span>
    <span class="mini-log-msg">${formatMessage(log.message)}</span>
  `;

  const container = miniLogEl();
  container.appendChild(el);
  container.scrollTop = container.scrollHeight;

  // Keep max 30 entries
  while (container.children.length > 30) {
    container.removeChild(container.firstChild);
  }
}

// ─── Connection Status ────────────────────────────────────────────────────────
function setConnectionStatus(connected, label = null) {
  isConnected = connected;
  const dot = connectionDot();
  const lbl = connectionLabel();
  dot.style.background   = connected ? "var(--success)" : "var(--error)";
  dot.style.boxShadow    = connected ? "0 0 6px var(--success)" : "0 0 6px var(--error)";
  lbl.textContent        = label || (connected ? "Connected" : "Disconnected");
}

// ─── New Session ─────────────────────────────────────────────────────────────
function newSession() {
  if (socket) { try { socket.close(); } catch {} }
  messagesEl().innerHTML = "";
  miniLogEl().innerHTML  = "";
  // Re-add welcome screen and typing indicator
  messagesEl().innerHTML = `
    <div class="welcome-screen" id="welcome-screen">
      <div class="welcome-icon">🤖</div>
      <h1 class="welcome-title">Hi, I'm ShopWave AI</h1>
      <p class="welcome-subtitle">Provide your Order ID to get started — I already know who you are!</p>
      <div class="suggestion-chips">
        <div class="chip" onclick="sendSuggestion('I want to initiate a refund for my order ORD-1001')">🔄 Refund order ORD-1001</div>
        <div class="chip" onclick="sendSuggestion('Show me all my orders')">📦 View my orders</div>
        <div class="chip" onclick="sendSuggestion('What is the return policy for Clothing?')">📋 Clothing policy</div>
      </div>
    </div>
    <div class="typing-indicator" id="typing-indicator">
      <div class="msg-avatar bot">🤖</div>
      <div class="typing-dots"><span></span><span></span><span></span></div>
    </div>
  `;
  initChat();
}

// ─── Voice ────────────────────────────────────────────────────────────────────
function toggleAutoSpeak() {
  autoSpeak = !autoSpeak;
  const btn = document.getElementById("auto-speak-toggle");
  btn.textContent = autoSpeak ? "🔊 Voice On" : "🔇 Voice";
  btn.classList.toggle("active", autoSpeak);
}

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
    mediaRecorder = new MediaRecorder(stream);
    audioChunks   = [];

    mediaRecorder.ondataavailable = (e) => { if (e.data.size > 0) audioChunks.push(e.data); };
    mediaRecorder.onstop = async () => {
      const blob = new Blob(audioChunks, { type: "audio/webm" });
      await transcribeAudio(blob);
      stream.getTracks().forEach(t => t.stop());
    };

    mediaRecorder.start();
    isRecording = true;
    document.getElementById("mic-btn").classList.add("recording");
    document.getElementById("voice-status").classList.add("visible");
  } catch {
    appendSystemMessage("Microphone access denied.", "error");
  }
}

function stopRecording() {
  if (mediaRecorder && mediaRecorder.state !== "inactive") {
    mediaRecorder.stop();
  }
  isRecording = false;
  document.getElementById("mic-btn").classList.remove("recording");
  document.getElementById("voice-status").classList.remove("visible");
}

async function transcribeAudio(blob) {
  const formData = new FormData();
  formData.append("audio", blob, "recording.webm");
  try {
    const resp = await fetch(`${API_BASE}/api/voice/transcribe`, {
      method: "POST",
      body:   formData,
    });
    if (resp.ok) {
      const { text } = await resp.json();
      if (text) sendMessage(text);
    }
  } catch {
    appendSystemMessage("Voice transcription failed.", "error");
  }
}

function speakText(text) {
  const plain = text.replace(/<[^>]+>/g, "").slice(0, 500);
  const utt   = new SpeechSynthesisUtterance(plain);
  utt.rate = 1.05;
  window.speechSynthesis.speak(utt);
}

// ─── Input helpers ────────────────────────────────────────────────────────────
function setupInputListeners() {
  const input = messageInput();
  if (!input) return;

  input.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage(input.value);
    }
  });
  input.addEventListener("input", () => autoResizeTextarea(input));
}

function autoResizeTextarea(el) {
  el.style.height = "auto";
  el.style.height = Math.min(el.scrollHeight, 120) + "px";
}

function scrollToBottom() {
  const el = messagesEl();
  el.scrollTop = el.scrollHeight;
}
