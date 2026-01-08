"""
LangGraph Graph Definition for the SQL Agent

This module exposes the agent as a LangGraph-compatible graph
that can be served via `langgraph dev` command.
"""

import os
from langchain.agents import create_agent
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.sqlite import SqliteSaver

# SQLite 檔案路徑 (用於持久化對話記錄)
CHECKPOINT_DB_PATH = os.path.join(os.path.dirname(__file__), "chat_history.db")


def build_system_prompt() -> str:
    """
    建立系統提示詞，引導模型使用探索模式。
    """
    return (
        "你是一個專門查詢 SQLite 資料庫的 AI 助手。\n\n"
        "### 你的工作流程：\n"
        "1. **探索階段**：首先使用 `list_tables` 工具來了解資料庫中有哪些資料表以及它們的結構。\n"
        "2. **查詢階段**：根據用戶的問題和探索到的結構，編寫 SQL 語句並使用 `query_data` 工具獲取答案。\n"
        "3. **回答階段**：以親切、專業的語氣回答用戶，如果查詢不到資料，請誠實告知。\n\n"
        "### 規則：\n"
        "- **嚴禁**在未確認資料表結構前猜測欄位名稱。\n"
        "- 只使用 `SELECT` 語句進行查詢。\n"
        "- 所有的對話和回答都必須使用 **繁體中文**。\n"
        "- 如果用戶的問題無法透過資料庫回答，請禮貌地說明原因。"
    )


# 初始化 SQLite Checkpointer (持久化對話記錄)
checkpointer = SqliteSaver.from_conn_string(CHECKPOINT_DB_PATH)


def create_sql_agent():
    """
    建立 SQL Agent Graph
    """
    from tools.sql_tool import list_tables, query_data

    llm = ChatOpenAI(
        base_url="http://localhost:8080/v1",
        api_key="EMPTY",
        model="qwen",
    )

    tools = [list_tables, query_data]

    graph = create_agent(
        model=llm,
        tools=tools,
        system_prompt=build_system_prompt(),
        checkpointer=checkpointer,
    )
    return graph


# Export the graph for langgraph dev
graph = create_sql_agent()
