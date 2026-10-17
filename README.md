# ⚡ Nexus Arena — Real-Time TCP & WebSocket Chat Server

A gamified, enterprise-grade real-time chat platform combining a **multi-client Raw TCP Socket Server** and a **Spring Boot WebSocket (STOMP) Broker**, featuring a **Real-Time Leaderboard System**, an **Instagram-style 24-Hour Stories Feature**, an **In-Memory Caching Layer**, and an automated **Database Backup & Recovery Utility**.

---

## 🌟 Key Features

### 1. Dual-Protocol Communication Architecture
* **Raw TCP Socket Server (Port `8888`)**:
  * Multithreaded TCP server accepting terminal clients via `nc`, `telnet`, or Python/PowerShell scripts.
  * Command protocol: `/nick`, `/join`, `/msg`, `/whisper`, `/leaderboard`, `/stories`, `/stats`, `/help`, `/quit`.
* **WebSocket & STOMP Broker (Port `8081`)**:
  * Real-time STOMP over SockJS for responsive web clients.
  * Public channels (`/topic/public`), room channels (`/topic/room/{id}`), and private queues (`/user/queue/private`).
* **Bidirectional Protocol Bridge**:
  * Messages sent by TCP terminal users are broadcast instantaneously to web browser users, and vice-versa.

### 2. Real-Time Leaderboard System
*(Ref: [roadmap.sh/projects/realtime-leaderboard-system](https://roadmap.sh/projects/realtime-leaderboard-system))*
* **Gamification Engine**:
  * Earn **+10 XP** per chat message sent.
  * Earn **+50 XP** per 24-hour story published.
  * Dynamic leveling system (`Lv.1` Novice to `Lv.10` Grandmaster) with level-up celebrations.
  * Achievement Badges: *Pioneer*, *Chatterbox*, *Storyteller*, *Century Club*, *High Roller*, *Grandmaster*.
* **Live Broadcast**:
  * Live rankings pushed over WebSocket (`/topic/leaderboard`) on score changes.
  * Interactive 3D Gold/Silver/Bronze **Top 3 Podium** in the web interface.

### 3. Ephemeral 24-Hour Stories Feature
*(Ref: [roadmap.sh/projects/stories-feature](https://roadmap.sh/projects/stories-feature))*
* Story feed with animated gradient border rings for active stories.
* Instagram-style full-screen **Story Viewer** with 5-second automatic progression timers, tap/click navigation, and live view tracking (`POST /api/stories/{id}/view`).
* Automatic background cleanup of stories older than 24 hours.

### 4. Fast Retrieval In-Memory Caching Server
*(Ref: [roadmap.sh/projects/caching-server](https://roadmap.sh/projects/caching-server))*
* In-memory LRU + TTL cache to eliminate redundant database reads on hot endpoints (leaderboard, active stories).
* Telemetry widget in UI displaying **Cache HITS**, **Cache MISSES**, and Hit Rate percentage.
* `X-Cache: HIT` / `X-Cache: MISS` HTTP response headers.
* Instant cache clearing endpoint (`POST /api/cache/clear`).

### 5. Database Backup & Recovery Utility
*(Ref: [roadmap.sh/projects/database-backup-utility](https://roadmap.sh/projects/database-backup-utility))*
* Database-agnostic JSON snapshot utility with **GZIP compression** (`.json.gz`).
* Automated background hourly snapshots with retention rotation (keeps latest 10 snapshots).
* Manual trigger endpoint (`POST /api/backup/create`) and full restoration (`POST /api/backup/restore/{filename}`).

### 6. PostgreSQL & Embedded Fallback
* Native support for **PostgreSQL** (`docker-compose.yml` included).
* Zero-configuration default profile with embedded PostgreSQL-compatible mode so the server boots instantly without any setup prerequisites.

---

## 🚀 Getting Started

### Prerequisites
* **Java 11+**
* **Apache Maven 3.8+**
* *(Optional)* Docker Desktop (if using PostgreSQL container)

---

### Step 1: Start the Database (Optional PostgreSQL Mode)
If you want to use PostgreSQL:
```bash
docker compose up -d
```
*Database name: `realtime_chat_db`, User: `postgres`, Password: `password`*

---

### Step 2: Build & Run the Application

#### Option A: Quick Run (Default Profile)
```bash
mvn spring-boot:run
```

#### Option B: Run with PostgreSQL Profile
```bash
mvn spring-boot:run -Dspring-boot.run.profiles=postgres
```

The server will launch:
* **Web UI & REST API**: [http://localhost:8090](http://localhost:8090)
* **Raw TCP Socket Server**: Listening on `localhost:8888`

---

## 🖥️ Connecting via TCP Clients

### Using Netcat / Telnet:
```bash
nc localhost 8888
# OR
telnet localhost 8888
```

### Using Python:
```bash
python tcp-client.py
```

### Using Windows PowerShell:
```powershell
.\tcp-client.ps1
```

### TCP Command Reference:
| Command | Description |
|---|---|
| `/nick <username>` | Set or change your username |
| `/msg <text>` | Send a message to the current room |
| `/join <room>` | Join or switch to a room (e.g. `/join gaming`) |
| `/whisper <user> <text>` | Send a direct private message to another user |
| `/leaderboard` | View the live Top 10 rankings in the terminal |
| `/stories` | View active 24-hour stories |
| `/stats` | View your personal XP, level, score, and badges |
| `/help` | Print help instructions |
| `/quit` | Disconnect from the server |

---

## 📡 REST API Reference

### Leaderboard & Gamification
* `GET /api/leaderboard/top?limit=10` — Retrieve top ranked users (with `X-Cache` header).
* `GET /api/leaderboard/user/{username}` — Retrieve stats for a specific user.
* `POST /api/leaderboard/bonus` — Award bonus XP/points to a user.

### Caching
* `GET /api/cache/stats` — Retrieve cache hits, misses, hit rate, and capacity.
* `POST /api/cache/clear` — Clear in-memory cache.

### Stories
* `GET /api/stories/active` — Retrieve all active, non-expired stories.
* `POST /api/stories` — Create a new story (`{ "username": "...", "content": "...", "mediaUrl": "..." }`).
* `POST /api/stories/{id}/view` — Record a view on a story.

### Database Backup Utility
* `POST /api/backup/create` — Generate an immediate compressed backup snapshot.
* `GET /api/backup/list` — List all available backup snapshots with file sizes and timestamps.
* `POST /api/backup/restore/{filename}` — Restore database tables from a snapshot.
