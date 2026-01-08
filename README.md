# 🗃️ SQL Agent - 筆記型電腦零件庫存查詢助手

一個基於 **LangChain** 和 **LangGraph** 的 SQL 智能代理，透過自然語言對話來查詢 SQLite 資料庫。本專案配備完整的 Web 聊天介面 (`agent-chat-ui`)，讓使用者能夠輕鬆與資料庫互動。

---

## 📋 目錄

- [專案架構](#專案架構)
- [設定檔說明](#設定檔說明)
  - [langgraph.json](#1-langgraphjson---langgraph-server-設定)
  - [.env (根目錄)](#2-env-根目錄---langgraph-server-環境變數)
  - [agent-chat-ui .env](#3-agent-chat-uiappswebenv---chat-ui-設定)
- [環境需求](#環境需求)
- [快速開始](#快速開始)
  - [1. 安裝 Python 環境 (uv)](#1-安裝-python-環境-uv)
  - [2. 初始化資料庫](#2-初始化資料庫)
  - [3. 啟動 LangGraph Server](#3-啟動-langgraph-server)
  - [4. 安裝並啟動 Agent Chat UI](#4-安裝並啟動-agent-chat-ui)
- [Agent 設計說明](#agent-設計說明)
- [Prompt 設計說明](#prompt-設計說明)
- [工具 (Tool) 設計說明](#工具-tool-設計說明)
- [測試資料說明](#測試資料說明)
- [常見問題](#常見問題)

---

## 專案架構

```
sql-agent/
├── graph.py              # LangGraph Agent 定義 (主入口)
├── langgraph.json        # LangGraph Server 設定檔
├── init_db.py            # 資料庫初始化腳本
├── inventory.db          # SQLite 庫存資料庫 (由 init_db.py 建立)
├── chat_history.db       # SQLite 對話記錄資料庫 (自動建立)
├── pyproject.toml        # Python 專案設定 (uv 管理)
├── .env                  # 環境變數
│
├── db/                   # 資料庫模組
│   ├── __init__.py
│   └── schema.py         # 動態 Schema 讀取與格式化
│
├── tools/                # LangChain 工具模組
│   ├── __init__.py
│   └── sql_tool.py       # SQL 執行工具
│
├── data/                 # 測試用 CSV 資料
│   ├── laptops.csv
│   ├── components.csv
│   └── laptop_components.csv
│
└── agent-chat-ui/        # Web 聊天介面 (Next.js)
    └── apps/web/
        └── .env          # UI 連線設定
```

---

## 設定檔說明

本專案有三個重要的設定檔需要了解：

### 1. `langgraph.json` - LangGraph Server 設定

這是 LangGraph 開發伺服器的核心設定檔：

```json
{
  "$schema": "https://langchain-ai.github.io/langgraph/langgraph-schema.json",
  "graphs": {
    "agent": "./graph.py:graph"
  },
  "env": ".env",
  "python_version": "3.13",
  "dependencies": ["."]
}
```

| 欄位 | 說明 |
|------|------|
| `$schema` | JSON Schema 規格網址，讓 IDE 提供自動補全與語法檢查 (固定值，勿修改) |
| `graphs` | **Graph 映射表**。Key 是 Assistant ID (如 `agent`)，Value 是 `檔案路徑:變數名` |
| `env` | 環境變數檔案路徑 |
| `python_version` | Python 版本要求 |
| `dependencies` | Python 套件依賴路徑 (`.` 表示當前目錄的 `pyproject.toml`) |

> 💡 **重點**：`graphs` 欄位的 **Key** (如 `agent`) 就是 Chat UI 中 `NEXT_PUBLIC_ASSISTANT_ID` 要填的值。

---

### 2. `.env` (根目錄) - LangGraph Server 環境變數

位置：`sql-agent/.env`

```bash
# LangSmith API Key (可選，用於追蹤)
# LANGSMITH_API_KEY=lsv2_...

# OpenAI API 設定 (連接本地 llama.cpp)
OPENAI_API_BASE=http://localhost:8080/v1
OPENAI_API_KEY=EMPTY
```

| 變數 | 必填 | 說明 |
|------|------|------|
| `LANGSMITH_API_KEY` | 否 | LangSmith 追蹤用，本地開發可省略 |
| `OPENAI_API_BASE` | 否 | 如果你在 `graph.py` 中已hardcode，這裡可省略 |
| `OPENAI_API_KEY` | 否 | 本地 llama.cpp 填 `EMPTY` 即可 |

---

### 3. `agent-chat-ui/apps/web/.env` - Chat UI 設定

位置：`sql-agent/agent-chat-ui/apps/web/.env`

```bash
# LangGraph Server 的連線地址 (預設本地開發為 2024 埠)
NEXT_PUBLIC_API_URL=http://localhost:2024

# 對應 langgraph.json 中 graphs 欄位定義的 Key
NEXT_PUBLIC_ASSISTANT_ID=agent

# 隱藏左側 Thread History 側邊欄 (設為 true 隱藏，移除或設為 false 顯示)
NEXT_PUBLIC_HIDE_THREAD_HISTORY=true
```

| 變數 | 必填 | 說明 |
|------|------|------|
| `NEXT_PUBLIC_API_URL` | ✅ | LangGraph Server 的 API 位址 |
| `NEXT_PUBLIC_ASSISTANT_ID` | ✅ | 必須與 `langgraph.json` 中 `graphs` 的 Key 一致 |
| `NEXT_PUBLIC_HIDE_THREAD_HISTORY` | 否 | 設為 `true` 隱藏左側對話歷史列表 |

> ⚠️ **注意**：`NEXT_PUBLIC_` 開頭的變數會暴露給前端，請勿放置敏感資訊。

---

### 4. 對話記錄持久化 (SQLite)

本專案使用 **SQLite** 來持久化對話記錄，確保伺服器重啟後對話不會遺失。

**相關檔案：**
- `graph.py` - 使用 `SqliteSaver` 作為 Checkpointer
- `chat_history.db` - 對話記錄資料庫（自動建立）

**運作原理：**
```python
from langgraph.checkpoint.sqlite import SqliteSaver

# 初始化 SQLite Checkpointer
checkpointer = SqliteSaver.from_conn_string("./chat_history.db")

# 建立 Agent 時傳入 checkpointer
graph = create_agent(
    model=llm,
    tools=[execute_sql],
    system_prompt=build_system_prompt(),
    checkpointer=checkpointer,  # 使用 SQLite 持久化
)
```

**如何清除對話記錄：**
```powershell
# 刪除對話記錄資料庫
rm chat_history.db

# 重啟 LangGraph Server
uv run langgraph dev --no-browser
```

---

### 設定檔關聯圖

```
langgraph.json                     agent-chat-ui/apps/web/.env
┌─────────────────────┐            ┌─────────────────────────────┐
│ graphs:             │            │ NEXT_PUBLIC_ASSISTANT_ID=   │
│   "agent": ...      │◄───────────│   agent                     │
└─────────────────────┘            └─────────────────────────────┘
         ▲                                      │
         │                                      │
         │ 讀取                                  │ 連線
         │                                      ▼
┌─────────────────────┐            ┌─────────────────────────────┐
│ LangGraph Server    │◄───────────│ NEXT_PUBLIC_API_URL=        │
│ http://localhost:   │            │   http://localhost:2024     │
│ 2024                │            └─────────────────────────────┘
└─────────────────────┘
         │
         │ 儲存對話
         ▼
┌─────────────────────┐
│ chat_history.db     │
│ (SQLite)            │
└─────────────────────┘
```

---

## 環境需求

| 工具 | 版本 | 用途 |
|------|------|------|
| Python | 3.13+ | 執行 Agent |
| [uv](https://docs.astral.sh/uv/) | 最新版 | Python 套件管理 |
| Node.js | 18+ | 執行 Chat UI |
| npm | 9+ | 前端套件管理 |
| llama.cpp Server | - | 本地 LLM 推論 (預設 8080 埠) |

---

## 快速開始

### 1. 安裝 Python 環境 (uv)

首先確保已安裝 [uv](https://docs.astral.sh/uv/getting-started/installation/)：

```powershell
# Windows (PowerShell)
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"

# macOS / Linux
curl -LsSf https://astral.sh/uv/install.sh | sh
```

進入專案目錄並安裝 Python 依賴：

```powershell
cd sql-agent

# uv 會自動建立虛擬環境並安裝所有依賴
uv sync
```

### 2. 初始化資料庫

執行初始化腳本，將 CSV 資料匯入 SQLite：

```powershell
uv run init_db.py
```

成功後會看到：

```
Initializing database at ...\inventory.db...
Loading laptops.csv into table 'laptops'...
Loading components.csv into table 'components'...
Loading laptop_components.csv into table 'laptop_components'...
Database initialization complete.
```

### 3. 啟動 LangGraph Server

> ⚠️ **前提條件**：請確保你的本地 LLM 伺服器 (如 llama.cpp) 已在 `http://localhost:8080` 運行。

啟動 LangGraph 開發伺服器：

```powershell
uv run langgraph dev --no-browser
```

成功後會看到：

```
╦  ┌─┐┌┐┌┌─┐╔═╗┬─┐┌─┐┌─┐┬ ┬
║  ├─┤││││ ┬║ ╦├┬┘├─┤├─┘├─┤
╩═╝┴ ┴┘└┘└─┘╚═╝┴└─┴ ┴┴  ┴ ┴

- 🚀 API: http://127.0.0.1:2024
- 📚 API Docs: http://127.0.0.1:2024/docs
```

### 4. 安裝並啟動 Agent Chat UI

開啟新的終端機視窗，進入 Chat UI 目錄：

```powershell
cd agent-chat-ui/apps/web

# 安裝前端依賴
npm install

# 啟動開發伺服器
npm run dev
```

成功後會看到：

```
▲ Next.js 15.x.x
- Local: http://localhost:3000
```

現在打開瀏覽器訪問 **http://localhost:3000** 即可開始對話！

---

## Agent 設計說明

### 核心概念

本專案使用 LangChain 最新的 `create_agent` 函數來建立 Agent。這是基於 **LangGraph** 的現代化方法，提供更靈活的控制流程。

### 程式碼解析 (`graph.py`)

```python
from langchain.agents import create_agent
from langchain_openai import ChatOpenAI

def create_sql_agent():
    # 1. 初始化 LLM (連接本地 llama.cpp)
    llm = ChatOpenAI(
        base_url="http://localhost:8080/v1",
        api_key="EMPTY",
        model="qwen",
    )

    # 2. 建立 Agent，綁定工具與系統提示
    graph = create_agent(
        model=llm,
        tools=[execute_sql],           # 可用工具列表
        system_prompt=build_system_prompt(),  # 動態注入 Schema
    )

    return graph

# 3. 匯出 graph 供 LangGraph Server 使用
graph = create_sql_agent()
```

### Agent 運作流程

```
使用者輸入
    ↓
LLM 分析意圖
    ↓
決定是否呼叫工具 → 是 → 呼叫 execute_sql → 取得結果
    ↓                                           ↓
    否                                          ↓
    ↓                                           ↓
生成最終回應 ←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←
```

---

## Prompt 設計說明

系統提示 (System Prompt) 是 Agent 行為的核心。我們採用**動態注入**的方式，確保 Agent 總是擁有最新的資料庫結構資訊。

### Prompt 結構

```
┌─────────────────────────────────────────┐
│  角色定義                                │
│  "你是一個專業的 SQL 助手..."            │
├─────────────────────────────────────────┤
│  動態注入的資料庫 Schema                 │  ← 從 SQLite 即時讀取
│  📋 Table: laptops                      │
│     - id: INTEGER [PK]                  │
│     - brand: TEXT                       │
│     ...                                 │
├─────────────────────────────────────────┤
│  職責說明                                │
│  1. 理解用戶需求                         │
│  2. 生成正確的 SQL                       │
│  3. 執行查詢                             │
│  4. 解釋結果                             │
├─────────────────────────────────────────┤
│  注意事項                                │
│  - 使用正確的表名和欄位名                 │
│  - JOIN 語法使用時機                     │
└─────────────────────────────────────────┘
```

### Schema 動態讀取 (`db/schema.py`)

```python
def get_database_schema() -> dict:
    """從 SQLite 即時讀取資料表結構"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 取得所有表格名稱
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = cursor.fetchall()
    
    # 對每個表格取得欄位資訊
    for table in tables:
        cursor.execute(f"PRAGMA table_info({table})")
        # ... 解析欄位資訊
```

**優點**：
- 資料庫結構變更時，不需手動更新 Prompt
- Agent 永遠基於最新的 Schema 生成 SQL

---

## 多使用者與上下文管理 (Advanced)

本專案支援多使用者環境下的身份識別與上下文管理，確保開發者可以追蹤每個請求的來源與狀態。

### 1. 認證與身份識別 (`auth.py`)

透過 LangGraph 的認證掛鉤，我們可以在請求進入 Agent 之前攔截並分配身份。

```python
from langgraph_sdk import Auth

auth = Auth()

@auth.authenticate
async def get_user(headers: dict):
    # 從 Header 取得或產生隨機 User ID
    user_id = headers.get("x-user-id", f"user-{uuid.uuid4().hex[:8]}")
    return {"identity": user_id}
```

### 2. 使用 `ToolRuntime` 獲取執行資訊

在工具 (Tool) 中，我們可以透過注入 `ToolRuntime` 參數來獲取當前的執行上下文，包括 **Thread ID**、**Run ID** 以及 **User ID**。

**範例：在工具中讀取 ID**
```python
@tool
def query_data(raw_sql: str, runtime: ToolRuntime):
    # 獲取 Thread ID (對話 ID)
    thread_id = runtime.config["configurable"].get("thread_id")
    # 獲取 User ID (由 auth.py 提供)
    user_id = runtime.config["configurable"]["langgraph_auth_user"]["identity"]
    # 獲取 Run ID (本次執行的唯一 ID)
    run_id = runtime.config["run_id"]
    
    print(f"User {user_id} 在 Thread {thread_id} 執行了查詢")
```

### 3. 重要特性：模型不可見性 (Invisibility)

> 💡 **關鍵說明**：在工具函數名中定義的 `runtime: ToolRuntime` 或 `config: RunnableConfig` 參數，**對模型 (LLM) 是完全不可見的**。

- **運作機制**：LangChain 在將工具定義轉換為 JSON Schema 提供給 LLM 時，會自動過濾掉這些型別為 `ToolRuntime` 或 `RunnableConfig` 的參數。
- **優點**：LLM 永遠不會嘗試去「填充」這些資訊。Agent 會以為該工具只需要 `raw_sql` 參數，而系統會在執行階段自動將正確的對象注入進去。這保證了系統資訊的安全與簡潔。

---

## 工具 (Tool) 設計說明

本專案採用 **探索式 (Discovery Pattern)** 工具設計，讓 Agent 在執行時動態發現資料庫結構，而非在啟動時寫死。

### 工具定義 (`tools/sql_tool.py`)

1.  **`list_tables`**：列出資料庫中的所有資料表及其 Schema。
2.  **`query_data`**：執行 SQL 查詢並獲取結果。

### 工具設計原則

| 原則 | 說明 |
| :--- | :--- |
| **動態發現** | 透過 `list_tables` 獲取結構，解決資料表過多或權限變動的問題。 |
| **JSON 回傳格式** | **關鍵設計**：工具回傳原始的 `list` 或 `dict` (JSON 格式)，而非格式化字串。 |
| **UI 自動渲染** | 由於回傳的是 JSON，`agent-chat-ui` 會自動將其轉換為互動式 HTML 表格。 |
| **錯誤顯示** | 使用 `traceback.print_exc()` 確保後端終端機能看到詳細錯誤日誌。 |

### 輸出範例 (JSON 邏輯)

當 `query_data` 被呼叫時，它回傳如下格式：
```json
[
  {"brand": "Apple", "model_name": "MacBook Pro 14"},
  {"brand": "Dell", "model_name": "XPS 13"}
]
```
`agent-chat-ui` 接收到此 JSON 後，會在網頁上渲染出漂亮的資料表格，支援自動對齊與溢出捲動。

---

## 測試資料說明

本專案包含三個 CSV 檔案，模擬筆記型電腦零件庫存系統：

### 1. `data/laptops.csv` - 筆記型電腦

| 欄位 | 說明 | 範例 |
|------|------|------|
| id | 主鍵 | 1 |
| brand | 品牌 | Apple |
| model_name | 型號名稱 | MacBook Pro 14 |
| serial_number | 序號 | SN-APL-MBP14-001 |
| manufacture_date | 出廠日期 | 2023-11-01 |

### 2. `data/components.csv` - 零件

| 欄位 | 說明 | 範例 |
|------|------|------|
| id | 主鍵 | 1 |
| name | 零件名稱 | Apple M3 Pro |
| type | 類型 | CPU / RAM / SSD / GPU |
| manufacturer | 製造商 | Apple |
| specs | 規格 | 11-core CPU / 14-core GPU |

### 3. `data/laptop_components.csv` - 安裝關聯

| 欄位 | 說明 |
|------|------|
| laptop_id | 對應 laptops.id |
| component_id | 對應 components.id |
| installation_date | 安裝日期 |

### 資料關聯圖

```
┌──────────────┐       ┌───────────────────┐       ┌──────────────┐
│   laptops    │       │ laptop_components │       │  components  │
├──────────────┤       ├───────────────────┤       ├──────────────┤
│ id (PK)      │◄──────│ laptop_id (FK)    │       │ id (PK)      │
│ brand        │       │ component_id (FK) │──────►│ name         │
│ model_name   │       │ installation_date │       │ type         │
│ serial_number│       └───────────────────┘       │ manufacturer │
│ manufacture_ │                                   │ specs        │
│ date         │                                   └──────────────┘
└──────────────┘
```

### 範例查詢

```sql
-- 查詢所有 MacBook 及其安裝的 CPU
SELECT l.model_name, c.name AS cpu_name, c.specs
FROM laptops l
JOIN laptop_components lc ON l.id = lc.laptop_id
JOIN components c ON lc.component_id = c.id
WHERE l.brand = 'Apple' AND c.type = 'CPU';
```

---

## 常見問題

### Q: 為什麼連不上 Agent？

確認以下服務都在運行：

| 服務 | 預設埠 | 檢查方式 |
|------|--------|----------|
| llama.cpp | 8080 | `curl http://localhost:8080/v1/models` |
| LangGraph | 2024 | `curl http://localhost:2024/docs` |
| Chat UI | 3000 | 瀏覽器開啟 `http://localhost:3000` |

### Q: `NEXT_PUBLIC_ASSISTANT_ID` 要填什麼？

這個值必須對應 `langgraph.json` 中 `graphs` 欄位的 **Key**。本專案預設為 `agent`：

```json
{
  "graphs": {
    "agent": "./graph.py:graph"  // ← 這裡的 "agent"
  }
}
```

### Q: 如何新增其他資料表？

1. 在 `data/` 目錄新增 CSV 檔案
2. 修改 `init_db.py`，在 `csv_files` 字典中加入新表格
3. 重新執行 `uv run init_db.py`
4. LangGraph Server 會自動偵測到 Schema 變更

### Q: 如何更換 LLM 模型？

修改 `graph.py` 中的 `ChatOpenAI` 設定：

```python
llm = ChatOpenAI(
    base_url="http://localhost:8080/v1",  # 更改 API 位址
    model="your-model-name",               # 更改模型名稱
)
```
