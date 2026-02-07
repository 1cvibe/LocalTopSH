# LocalTopSH Improvements Roadmap

На основе тестирования 65 сценариев выявлены области для улучшения.

## 🔴 Критичные (блокируют функционал)

### 1. MCP Docker Tools не используются
**Проблема:** Агент пытается запустить `docker ps` в sandbox вместо MCP tools
**Затронуто:** Тесты #36-39 (docker категория)

**Решение:** Добавить в system.txt:
```
🐳 DOCKER MANAGEMENT:
Для работы с Docker используй специальные MCP tools:
- docker_ps: список контейнеров
- docker_logs: логи контейнера
- docker_images: список образов
- docker_restart: перезапуск контейнера
- docker_exec: выполнить команду в контейнере

⚠️ НЕ ИСПОЛЬЗУЙ run_command для docker! В sandbox нет Docker.
Пример: "покажи контейнеры" → вызови docker_ps tool
```

### 2. search_tools не используется для discovery
**Проблема:** Агент перечисляет tools из памяти вместо search_tools
**Затронуто:** Тесты #49-50

**Решение:** Улучшить описание search_tools:
```python
"search_tools": {
    "description": "🔍 ОБЯЗАТЕЛЬНО используй для поиска инструментов! Показывает ВСЕ доступные tools включая MCP и Skills. Пример: search_tools(query='docker') найдёт docker_ps, docker_logs и т.д."
}
```

---

## 🟡 Средний приоритет

### 3. Lazy Loading Tools (в разработке)

**Текущее состояние:**
- Все ~30 tools загружаются в каждый запрос к LLM
- Это ~3-4KB в каждом system prompt
- Увеличивает latency и cost

**Предлагаемая архитектура:**

```
┌─────────────────────────────────────────────────────────────┐
│                    LAZY LOADING TOOLS                        │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  БАЗОВЫЕ TOOLS (всегда загружены, ~10):                     │
│  ├── run_command                                            │
│  ├── read_file / write_file / edit_file                     │
│  ├── search_web / fetch_page                                │
│  ├── memory                                                 │
│  ├── search_tools  ← КЛЮЧЕВОЙ для discovery                │
│  └── manage_tasks                                           │
│                                                              │
│  РАСШИРЕННЫЕ TOOLS (загружаются по требованию):             │
│  ├── telegram_* (8 tools) → когда "telegram" в запросе     │
│  ├── docker_* (MCP, 17 tools) → когда "docker" в запросе   │
│  ├── gdrive_* (5 tools) → когда "drive/диск" в запросе     │
│  ├── schedule_task → когда "напомни/задача/schedule"       │
│  └── skill tools → когда skill name в запросе              │
│                                                              │
│  FLOW:                                                       │
│  1. User: "прочитай канал @NeuralShit"                      │
│  2. Agent видит только базовые tools                        │
│  3. Agent: search_tools(query="telegram channel")           │
│  4. System: добавляет telegram_channel в available tools    │
│  5. Agent: telegram_channel(channel="@NeuralShit")          │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

**Изменения в коде:**

```python
# core/agent.py

CORE_TOOLS = [
    "run_command", "read_file", "write_file", "edit_file", "delete_file",
    "search_files", "search_text", "list_directory",
    "search_web", "fetch_page", "memory", "manage_tasks", "search_tools"
]

TOOL_GROUPS = {
    "telegram": ["telegram_channel", "telegram_join", "telegram_send", ...],
    "docker": ["docker_ps", "docker_logs", "docker_images", ...],
    "gdrive": ["gdrive_auth", "gdrive_list", "gdrive_search", ...],
    "scheduler": ["schedule_task"],
}

TOOL_TRIGGERS = {
    "telegram": ["telegram", "канал", "чат", "подписка", "@"],
    "docker": ["docker", "контейнер", "container", "image"],
    "gdrive": ["drive", "диск", "google", "гугл"],
    "scheduler": ["напомни", "через", "каждый", "schedule", "задача"],
}

async def get_tools_for_request(message: str, session_tools: set) -> list:
    """Get tools based on message content + previously discovered"""
    tools = set(CORE_TOOLS)
    tools.update(session_tools)  # Tools discovered via search_tools
    
    # Auto-detect needed tool groups
    message_lower = message.lower()
    for group, triggers in TOOL_TRIGGERS.items():
        if any(t in message_lower for t in triggers):
            tools.update(TOOL_GROUPS[group])
    
    return list(tools)
```

**Изменения в search_tools:**

```python
async def tool_search_tools(args: dict, ctx: ToolContext) -> ToolResult:
    """Search and ACTIVATE tools"""
    query = args.get("query", "")
    
    # Search all available tools
    all_tools = await fetch_all_tools()
    matches = [t for t in all_tools if query.lower() in t["name"].lower() 
               or query.lower() in t["description"].lower()]
    
    # Add matched tools to session's active tools
    for tool in matches:
        ctx.session.active_tools.add(tool["name"])
    
    # Return formatted list
    result = f"Found {len(matches)} tools:\n"
    for t in matches[:10]:
        result += f"• {t['name']}: {t['description'][:50]}...\n"
    
    return ToolResult(True, output=result)
```

**System prompt update:**

```
<TOOLS>
У тебя есть базовые инструменты: run_command, read_file, write_file, search_web, memory, manage_tasks.

🔍 ВАЖНО: Для специальных задач используй search_tools!
- "docker" → search_tools(query="docker") → найдёт docker_ps, docker_logs...
- "telegram" → search_tools(query="telegram") → найдёт telegram_channel, telegram_send...
- "drive" → search_tools(query="drive") → найдёт gdrive_auth, gdrive_list...

После search_tools новые инструменты станут доступны для использования!
</TOOLS>
```

### 4. Node.js в sandbox
**Проблема:** Node.js не установлен
**Решение:** Добавить в sandbox Dockerfile:
```dockerfile
RUN apk add --no-cache nodejs npm
```

### 5. Таймауты на долгих операциях
**Проблема:** git clone больших репо таймаутит
**Решение:** 
- Увеличить timeout до 180s для run_command
- Использовать shallow clone: `git clone --depth 1`

### 6. Telegram time filtering
**Проблема:** telegram_channel не фильтрует по времени
**Решение:** Добавить параметр `since_hours`:
```python
async def tool_telegram_channel(args: dict, ctx: ToolContext) -> ToolResult:
    channel = args.get("channel")
    limit = args.get("limit", 5)
    since_hours = args.get("since_hours")  # NEW
```

---

## 🟢 Низкий приоритет (nice to have)

### 7. Tool usage analytics
Собирать статистику какие tools используются чаще всего для оптимизации.

### 8. Tool suggestions
После ошибки предлагать альтернативные tools.

### 9. Skill auto-discovery
Автоматически показывать релевантные skills в system prompt.

### 10. MCP tools caching
Кэшировать MCP tool definitions дольше (сейчас 60s).

---

## Метрики успеха

| Метрика | Текущее | Цель |
|---------|---------|------|
| Pass rate | 74% | 90%+ |
| Avg response time | 4-6s | 3-4s |
| Tools per request | ~30 | ~15 (lazy) |
| Docker tests | 0/4 | 4/4 |
| Telegram tests | 8/12 | 12/12 |

---

## Порядок реализации

1. **Неделя 1:** Фикс MCP Docker tools (system prompt)
2. **Неделя 2:** Lazy loading базовая версия
3. **Неделя 3:** Node.js в sandbox + таймауты
4. **Неделя 4:** Telegram improvements + тестирование
