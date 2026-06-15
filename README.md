# 🛒 ShopWave AI Customer Support Agent

<div align="center">

![ShopWave](https://img.shields.io/badge/ShopWave-AI%20Support-7c3aed?style=for-the-badge&logo=openai&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688?style=for-the-badge&logo=fastapi&logoColor=white)
![LangGraph](https://img.shields.io/badge/LangGraph-Powered-ff6b6b?style=for-the-badge)
![GPT-4o](https://img.shields.io/badge/GPT--4o-OpenAI-412991?style=for-the-badge&logo=openai)
![SQLite](https://img.shields.io/badge/SQLite-Database-003B57?style=for-the-badge&logo=sqlite)

**A premium AI-powered e-commerce customer support system with real-time agent reasoning, voice input, and a live admin dashboard.**

</div>

---

## ✨ Features

### 💬 Customer Chat Interface
- **AI Refund Agent** — GPT-4o + LangGraph agentic pipeline that processes refund requests end-to-end
- **Voice Input** — Animated microphone orb using Web Speech API + OpenAI Whisper transcription
- **Voice Responses** — Optional text-to-speech playback of agent replies
- **Real-time reasoning** — Live sidebar showing agent's decision steps as they happen
- **Session persistence** — Auth token stored in sessionStorage; auto-reconnecting WebSocket

### 📊 Admin Dashboard
- **Real-time reasoning logs** — Live WebSocket feed of every agent tool call and decision
- **Session management** — All active chat sessions with refund decision status
- **Customer profile panel** — User details, order history, payment methods, return status
- **⚠️ No-order detection** — Users with zero orders display a warning badge; the agent automatically declines refunds
- **Log filtering** — Filter by Info / Success / Error / Warning level
- **Create New User** — Admin form to add users to the CRM with auto-generated IDs
- **User list browser** — Browse all CRM users with their order count badges

### 🔒 Business Logic
| Scenario | Agent Behaviour |
|---|---|
| User has no orders + asks for refund | Returns "no order found" immediately — no tool calls made |
| Order not in return window | Denied with exact policy section cited |
| Gift Card payment | Denied (non-refundable) |
| Already refunded order | Blocked as duplicate |
| Defective / damaged / wrong item | Always eligible regardless of window |
| New admin-created user asks for refund | Agent checks → no orders found → decline |

---

## 🖥️ Screenshots

| Customer Chat | Admin Dashboard |
|---|---|
| Login with demo accounts | Real-time reasoning logs |
| Voice orb + reasoning sidebar | Create User modal |
| Refund approval/denial banners | Customer profile + order cards |

---

## 🗂️ Project Structure

```
AI Customer Support Agent/
├── backend/
│   ├── main.py                  # FastAPI app — mounts all routers + static frontend
│   ├── config.py                # Settings (OpenAI key, SMTP, model names)
│   ├── verify.py                # Startup self-check script
│   ├── requirements.txt
│   ├── .env                     # Your secrets (not committed)
│   ├── .env.example
│   │
│   ├── agent/
│   │   ├── graph.py             # LangGraph StateGraph — agent + tools nodes
│   │   ├── prompts.py           # System prompt with no-order refund rule
│   │   ├── state.py             # AgentState TypedDict
│   │   └── tools.py             # 6 tools: policy, orders, lookup, eligibility, refund, date
│   │
│   ├── api/
│   │   ├── auth.py              # POST /api/auth/login|logout, GET /api/auth/me
│   │   ├── chat.py              # WebSocket /ws/chat/{id} — streams reasoning to frontend
│   │   ├── voice.py             # POST /api/voice/transcribe (Whisper STT)
│   │   └── admin.py             # WebSocket /ws/admin + REST user/session endpoints
│   │
│   ├── data/
│   │   ├── crm_database.py      # SQLite accessors (users, orders) + create_user()
│   │   ├── auth_db.py           # In-memory session store
│   │   ├── db.py                # SQLite connection helper
│   │   ├── setup_db.py          # DB creation + seed script
│   │   ├── refund_policy.py     # Policy text + rules constants
│   │   └── crm.db               # SQLite database (auto-created)
│   │
│   └── services/
│       └── email_service.py     # Refund confirmation emails (dev: stdout, prod: SMTP)
│
└── frontend/
    ├── index.html               # Customer chat UI
    ├── admin.html               # Admin dashboard UI
    ├── css/
    │   ├── main.css             # Premium dark chat styles
    │   └── admin.css            # Premium dark admin styles
    └── js/
        ├── chat.js              # Chat WebSocket, voice, login flow
        └── admin.js             # Admin WS, session list, user creation
```

---

## 🚀 Getting Started

### Prerequisites
- Python 3.11+
- An [OpenAI API key](https://platform.openai.com/api-keys)

### 1. Clone & Install

```bash
git clone https://github.com/ShubhamZoro/Customer-Support-Agent.git
cd "AI Customer Support Agent"

# Create virtual environment
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # macOS/Linux

pip install -r backend/requirements.txt
```

### 2. Configure Environment

```bash
cp backend/.env.example backend/.env
```

Edit `backend/.env`:

```env
OPENAI_API_KEY=sk-...your-key-here...
OPENAI_MODEL=gpt-4o

# Optional SMTP (leave blank for dev-mode email logging)
SMTP_HOST=
SMTP_PORT=587
SMTP_USER=
SMTP_PASSWORD=
EMAIL_FROM=
```

### 3. Seed the Database

```bash
cd backend
python data/setup_db.py
```

This creates `backend/data/crm.db` with **8 demo users** and **16 orders** covering all refund scenarios.

### 4. Run the Server

```bash
cd backend
python main.py
```

The server starts at **http://localhost:8000** with hot-reload enabled.

```
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000
```

### 5. Open in Browser

| Page | URL |
|---|---|
| 🛒 Customer Chat | http://localhost:8000 |
| 📊 Admin Dashboard | http://localhost:8000/admin |
| 📖 API Docs | http://localhost:8000/docs |

---

## 🧪 Demo Accounts

All demo accounts use password: **`password123`**

| Email | User ID | Scenario |
|---|---|---|
| `alice.johnson@demo.com` | USR-001 | ✅ Electronics (within window) + expired |
| `bob.martinez@demo.com` | USR-002 | ✅ Home (active) + Clothing (window expired) |
| `carol.white@demo.com` | USR-003 | ❌ Already refunded (duplicate test) |
| `david.chen@demo.com` | USR-004 | ❌ Gift Card payment (non-refundable) |
| `emma.davis@demo.com` | USR-005 | ❌ Subscription window expired |
| `frank.wilson@demo.com` | USR-006 | ✅ Electronics $499 (active) |
| `grace.lee@demo.com` | USR-007 | ✅ Clothing (within 15-day window) |
| `henry.brown@demo.com` | USR-008 | ❌ Returned (already processed) |

> **No-Order Test:** Create a new user via the Admin Dashboard → "Create User", then log in as that user and ask for a refund. The agent will respond: *"I wasn't able to find any orders associated with your account."*

---

## 🤖 Agent Architecture

```
Customer Message
      │
      ▼
 ┌─────────────┐
 │  Agent Node │ ← GPT-4o with tool bindings
 │  (LangGraph)│
 └──────┬──────┘
        │ tool_calls?
   ┌────┴────┐
  YES       NO → Final Response
   │
   ▼
┌──────────────┐
│  Tools Node  │
│  (ToolNode)  │
└──────┬───────┘
       │ returns ToolMessage
       └──────────────────→ back to Agent Node
```

### The 6 Agent Tools

| Tool | Purpose |
|---|---|
| `get_my_orders` | Lists all orders for authenticated user. Returns `status: no_orders` if none exist. |
| `lookup_order` | Fetches specific order — enforces user ownership |
| `check_refund_eligibility` | Full policy gate: window + duplicate + payment method |
| `initiate_refund` | Writes DB update + sends confirmation email |
| `get_refund_policy` | Returns full policy doc or named section |
| `get_current_date` | Returns today's date for window calculations |

### No-Order Refund Guard (Critical Path)

```
User: "I want a refund"
  │
  ▼
Agent calls get_my_orders(user_id)
  │
  ├─ status: "no_orders" ──→ STOP
  │                           Agent: "No orders found on your account.
  │                            Refund cannot be processed."
  │
  └─ status: "found" ──→ Continue normal refund workflow
```

---

## 🛠️ API Reference

### Auth
| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/auth/login` | `{email, password}` → `{session_id, user_id, email}` |
| `POST` | `/api/auth/logout` | `{session_id}` → invalidate session |
| `GET` | `/api/auth/me?session_id=` | Returns current user |

### Chat
| Method | Endpoint | Description |
|---|---|---|
| `WS` | `/ws/chat/{session_id}?auth={token}` | Bidirectional chat + reasoning stream |
| `GET` | `/api/sessions` | List all sessions |
| `GET` | `/api/sessions/{id}` | Session detail + message history |

### Voice
| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/voice/transcribe` | `multipart/form-data` audio → `{text}` |

### Admin
| Method | Endpoint | Description |
|---|---|---|
| `WS` | `/ws/admin` | Live session updates + reasoning log stream |
| `GET` | `/api/admin/sessions` | All active sessions |
| `GET` | `/api/admin/sessions/{id}/logs` | Full reasoning log for session |
| `GET` | `/api/admin/users` | All CRM users with order counts |
| `POST` | `/api/admin/users` | Create new user |
| `GET` | `/api/admin/users/{user_id}` | User profile + full order list |

---

## ⚙️ Refund Policy Summary

| Category | Return Window |
|---|---|
| Electronics | 30 days |
| Home | 30 days |
| Clothing | 15 days |
| Toys | 21 days |
| Books | 14 days |
| Subscription | 7 days |
| Services | 7 days |

**Always eligible** (no window limit): Defective, damaged, wrong item, not received.

**Never eligible**: Gift Card payments · Already refunded orders · No orders on account.

---

## 🔧 Troubleshooting

**Server won't start**
```bash
# Run the self-check script
cd backend
python verify.py
```

**Login fails — "Invalid email or password"**
```bash
# Re-seed the database
cd backend
python data/setup_db.py
```

**OpenAI errors**
- Check `OPENAI_API_KEY` is set in `backend/.env`
- Verify the model name `gpt-4o` is available on your account

**Voice transcription not working**
- Ensure browser microphone permissions are granted
- Voice transcription requires `OPENAI_API_KEY` with Whisper access

**WebSocket disconnects immediately**
- Make sure you're logged in (auth token required)
- Check browser console for `code 1008` (auth failure)

---

## 🧹 Development Notes

- **Hot reload** is enabled — save any backend `.py` file and uvicorn restarts automatically
- **Emails** in dev mode print to the terminal (no SMTP config needed)
- **Database** resets with `python data/setup_db.py --force` (⚠️ deletes all data)
- **Admin WebSocket** broadcasts all reasoning logs to all connected admin tabs in real-time

---

## 📦 Tech Stack

| Layer | Technology |
|---|---|
| Backend framework | FastAPI + Uvicorn |
| AI agent | LangGraph + LangChain |
| LLM | OpenAI GPT-4o |
| Voice STT | OpenAI Whisper |
| Voice TTS | Web Speech API |
| Database | SQLite (via Python `sqlite3`) |
| Real-time | WebSockets (FastAPI native) |
| Frontend | Vanilla HTML + CSS + JS (no framework) |
| Fonts | Inter (Google Fonts) |

---

<div align="center">
Built with ❤️ using FastAPI · LangGraph · GPT-4o
</div>
