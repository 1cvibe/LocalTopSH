# LocalTopSH 🐧

**AI Agent with full system access, sandboxed per user.**

> 🔥 **Battle-tested by 1500+ hackers!**
> 
> Live in [**@neuraldeepchat**](https://t.me/neuraldeepchat) — community stress-tested with **1500+ attack attempts**:
> - Token extraction (env, /proc, base64 exfil, HTTP servers)
> - RAM/CPU exhaustion (zip bombs, infinite loops, fork bombs)
> - Container escape attempts
> 
> **Result: 0 secrets leaked, 0 downtime.**

## Architecture

```
┌──────────────────────────────────────────────────────────────────────────┐
│                              HOST (Docker)                               │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌──────────────┐     ┌──────────────────────┐     ┌──────────────────┐  │
│  │   Telegram   │     │       Gateway        │     │      Proxy       │  │
│  │    Users     │◄───►│   Bot + ReAct Agent  │────►│   /run/secrets/  │  │
│  └──────────────┘     │                      │     │  • api_key       │  │
│                       │  /workspace/_shared/ │     │  • telegram_token│  │
│                       │  • chats/*.md        │     │  • base_url      │  │
│                       │  • GLOBAL_LOG.md     │     └──────────────────┘  │
│                       └──────────┬───────────┘              │            │
│                                  │                          │            │
│                    Docker API    │              LLM API ◄───┘            │
│                                  ▼                                       │
│  ┌────────────────────────────────────────────────────────────────────┐  │
│  │                   Dynamic Sandbox Containers                       │  │
│  │                   (python:3.11-alpine per user)                    │  │
│  ├─────────────────┬─────────────────┬─────────────────┬──────────────┤  │
│  │ sandbox_123     │ sandbox_456     │ sandbox_789     │              │  │
│  │ ports:5000-5009 │ ports:5010-5019 │ ports:5020-5029 │    ...       │  │
│  │                 │                 │                 │              │  │
│  │ /workspace/123/ │ /workspace/456/ │ /workspace/789/ │              │  │
│  │ • MEMORY.md     │ • MEMORY.md     │ • MEMORY.md     │              │  │
│  │ • SESSION.json  │ • SESSION.json  │ • SESSION.json  │              │  │
│  │ • gdrive_token  │ • user files    │ • user files    │              │  │
│  │ • user files    │                 │                 │              │  │
│  └─────────────────┴─────────────────┴─────────────────┴──────────────┘  │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘
```

**Data Locations:**
- `/workspace/_shared/chats/` — chat history per chat (all users see context)
- `/workspace/{userId}/` — user files, memory, session, OAuth tokens
- `/run/secrets/` — API keys (only Proxy has access, never Agent)

**Key Security:**
- Each user runs in **isolated Docker container**
- Container sees only **own workspace** (not others)
- **No access** to `/run/secrets`, `/app`, host filesystem
- Limits: 512MB RAM, 50% CPU, 100 processes
- Auto-cleanup: 60 min inactive → container removed
- Secrets isolated via internal Proxy (agent never sees API keys)

## Features

- **ReAct Agent** with 13 tools (shell, files, web search, scheduler)
- **Per-user Docker sandbox** with resource limits
- **Secrets isolation** via Docker Secrets + internal Proxy
- **Smart reactions** on messages (LLM-powered)
- **Autonomous "thoughts"** in chat (LLM-generated from context)
- **Anti-abuse**: 247 regex patterns, rate limits, DoS prevention

## Tools (13)

| Tool | Description |
|------|-------------|
| `run_command` | Execute shell (runs in sandbox container) |
| `read_file` | Read file content |
| `write_file` | Create/overwrite file |
| `edit_file` | Edit file (find & replace) |
| `delete_file` | Delete file |
| `search_files` | Find files by glob |
| `search_text` | Search text in files |
| `list_directory` | List directory |
| `search_web` | Web search (Z.AI) |
| `fetch_page` | Fetch URL content |
| `send_file` | Send file to chat |
| `send_dm` | Send private message |
| `memory` | Persistent notes across sessions |

## Quick Start

```bash
# 1. Create secrets folder
mkdir secrets

# 2. Add required secrets
echo "your-telegram-token" > secrets/telegram_token.txt
echo "http://your-llm:8000/v1" > secrets/base_url.txt
echo "your-llm-key" > secrets/api_key.txt
echo "your-zai-key" > secrets/zai_api_key.txt

# 3. Start
docker compose up -d

# 4. Check
docker compose logs -f
```

## Secrets Configuration

All secrets are stored in `secrets/` folder (gitignored) and mounted via Docker Secrets.

| Secret File | Required | Description |
|-------------|----------|-------------|
| `telegram_token.txt` | ✅ Yes | Telegram Bot API token from [@BotFather](https://t.me/BotFather) |
| `base_url.txt` | ✅ Yes | LLM API endpoint (e.g., `http://your-llm:8000/v1`) |
| `api_key.txt` | ✅ Yes | LLM API key |
| `zai_api_key.txt` | ✅ Yes | Z.AI API key for web search ([z.ai](https://z.ai)) |
| `gdrive_client_id.txt` | ❌ Optional | Google Drive OAuth Client ID |
| `gdrive_client_secret.txt` | ❌ Optional | Google Drive OAuth Client Secret |

**Security:** Secrets are only accessible by the Proxy container. The Agent (Gateway) never sees API keys — it routes requests through the internal Proxy.

## Google Drive Integration

Users can connect their Google Drive to access files directly from the bot.

### Setup Google Drive (Optional)

1. **Create Google Cloud Project**
   - Go to [Google Cloud Console](https://console.cloud.google.com/)
   - Create new project or select existing
   - Enable **Google Drive API**

2. **Create OAuth 2.0 Credentials**
   - Go to **APIs & Services → Credentials**
   - Click **Create Credentials → OAuth client ID**
   - Application type: **Desktop app**
   - Download JSON or copy Client ID and Client Secret

3. **Configure OAuth Consent Screen**
   - Go to **APIs & Services → OAuth consent screen**
   - User type: **External** (or Internal for Workspace)
   - Add scopes: `https://www.googleapis.com/auth/drive.readonly`
   - Add test users (if in testing mode)

4. **Add Secrets**
   ```bash
   echo "your-client-id.apps.googleusercontent.com" > secrets/gdrive_client_id.txt
   echo "your-client-secret" > secrets/gdrive_client_secret.txt
   ```

5. **Restart**
   ```bash
   docker compose down && docker compose up -d
   ```

### User Flow

1. User sends `/gdrive` or asks to connect Google Drive
2. Bot returns OAuth URL
3. User opens URL, grants access, gets redirect with code
4. User sends code to bot
5. Bot exchanges code for tokens, stores in user's workspace
6. User can now: list files, search, download from their Drive

### Google Drive Tools

| Tool | Description |
|------|-------------|
| `gdrive_auth` | Start OAuth flow, get auth URL |
| `gdrive_callback` | Exchange auth code for tokens |
| `gdrive_list` | List files in Drive or folder |
| `gdrive_search` | Search files by name |
| `gdrive_download` | Download file to workspace |

**Per-user tokens:** Each user's OAuth tokens are stored in their isolated workspace (`/workspace/{userId}/gdrive_token.json`). Users only access their own Drive.

## Configuration

All settings in `src/config.ts`:

| Section | What it controls |
|---------|------------------|
| `rateLimit` | Telegram API limits |
| `timeouts` | Tool execution, API calls |
| `agent` | Max iterations, history |
| `sandbox` | Container limits, TTL |
| `reactions` | Emoji chance, weights |
| `thoughts` | Autonomous messages interval |

## Roadmap: Docker Sandboxes with MicroVM

> 🚀 **Coming soon: MicroVM isolation!**
> 
> Docker announced [Docker Sandboxes](https://www.docker.com/blog/docker-sandboxes-run-claude-code-and-other-coding-agents-unsupervised-but-safely/) with **MicroVM-based isolation** (Jan 2026).
> 
> When **Linux support** arrives, we'll migrate from container isolation to MicroVM:
> 
> | Current | Future |
> |---------|--------|
> | Container isolation | **MicroVM isolation** (hypervisor-level) |
> | Mount docker.sock | **Isolated Docker daemon** |
> | Manual limits | **Built-in sandboxing** |
> 
> This will provide even stronger security boundaries with zero changes for users.

## Security

**247 regex patterns** protecting against attacks:
- 191 BLOCKED (never allowed)
- 56 DANGEROUS (require approval)

Categories:
- Secrets: env, /proc/environ, /run/secrets, process.env
- Exfiltration: base64 encode, curl POST, HTTP servers reading secrets
- DoS: fork bombs, zip bombs, huge allocations
- Escape: other workspaces, host filesystem, Docker socket

Architecture:
- **Docker sandbox** per user (dynamic containers)
- **Docker Secrets** for all API keys  
- **Internal proxy** isolates secrets from agent
- **Per-user workspace** isolation (only own dir mounted)

## Structure

```
├── docker-compose.yml    # Gateway + Proxy
├── secrets/              # API keys (gitignored)
├── proxy/                # Internal API proxy
└── src/
    ├── config.ts         # All settings
    ├── agent/            # ReAct loop
    ├── bot/              # Telegram bot
    ├── approvals/        # Security patterns
    └── tools/            # 13 tools + Docker sandbox
```

## License

MIT
